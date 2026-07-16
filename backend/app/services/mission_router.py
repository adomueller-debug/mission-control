from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import requests
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from backend.app.database.database import SessionLocal
from backend.app.models.mission import MissionPlan, MissionPlanTask
from backend.app.models.project import Project
from backend.app.services.agent_catalog import AGENTS, get_agent
from backend.app.services.agent_team import agent_team
from backend.app.services.coder import (
    MODEL,
    OLLAMA_CONTEXT,
    OLLAMA_MAX_TOKENS,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
)
from backend.app.services.integration_catalog import INTEGRATION_BY_ID, INTEGRATIONS
from backend.app.services.integration_service import integration_service
from backend.app.services.project_service import TASK_TYPES, project_service


class MissionTaskDraft(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(min_length=2, max_length=10_000)
    agent_id: str
    task_type: str
    priority: int = Field(ge=1, le=5)
    dependencies: list[int] = Field(default_factory=list)
    integration_ids: list[str] = Field(default_factory=list)
    acceptance_criteria: str = Field(min_length=2, max_length=5_000)


class MissionDraft(BaseModel):
    summary: str
    strategy: str
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    tasks: list[MissionTaskDraft] = Field(min_length=1, max_length=20)


def _loads(value: str) -> Any:
    return json.loads(value) if value else []


def _task_to_dict(task: MissionPlanTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "sequence": task.sequence,
        "title": task.title,
        "description": task.description,
        "agent_id": task.agent_id,
        "task_type": task.task_type,
        "priority": task.priority,
        "dependencies": _loads(task.dependencies),
        "integration_ids": _loads(task.integration_ids),
        "acceptance_criteria": task.acceptance_criteria,
        "delegation_path": agent_team.delegation_path("boss", task.agent_id),
    }


def _plan_to_dict(plan: MissionPlan, tasks: list[MissionPlanTask]) -> dict[str, Any]:
    return {
        "id": plan.id,
        "project_id": plan.project_id,
        "goal": plan.goal,
        "summary": plan.summary,
        "strategy": plan.strategy,
        "assumptions": _loads(plan.assumptions),
        "risks": _loads(plan.risks),
        "success_metrics": _loads(plan.success_metrics),
        "status": plan.status,
        "planner_mode": plan.planner_mode,
        "tasks": [_task_to_dict(task) for task in tasks],
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
    }


class MissionRouter:
    def create_plan(self, project_id: str, goal: str | None = None) -> dict[str, Any]:
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise KeyError(project_id)
            mission_goal = (goal or project.goal or project.name).strip()
            project_context = {
                "name": project.name,
                "description": project.description,
                "category": project.category,
                "goal": project.goal,
            }

        planner_mode = "ollama"
        try:
            draft = self._ollama_plan(mission_goal, project_context)
            self._validate_draft(draft)
        except (requests.RequestException, ValueError, ValidationError, KeyError):
            draft = self._fallback_plan(mission_goal, project_context)
            planner_mode = "fallback"

        plan = MissionPlan(
            project_id=project_id,
            goal=mission_goal,
            summary=draft.summary,
            strategy=draft.strategy,
            assumptions=json.dumps(draft.assumptions, ensure_ascii=False),
            risks=json.dumps(draft.risks, ensure_ascii=False),
            success_metrics=json.dumps(draft.success_metrics, ensure_ascii=False),
            planner_mode=planner_mode,
        )
        with SessionLocal() as db:
            db.add(plan)
            db.flush()
            tasks: list[MissionPlanTask] = []
            for sequence, draft_task in enumerate(draft.tasks, start=1):
                row = MissionPlanTask(
                    plan_id=plan.id,
                    sequence=sequence,
                    title=draft_task.title,
                    description=draft_task.description,
                    agent_id=draft_task.agent_id,
                    task_type=draft_task.task_type,
                    priority=draft_task.priority,
                    dependencies=json.dumps(draft_task.dependencies),
                    integration_ids=json.dumps(draft_task.integration_ids),
                    acceptance_criteria=draft_task.acceptance_criteria,
                )
                db.add(row)
                tasks.append(row)
            db.commit()
            db.refresh(plan)
            for persisted_task in tasks:
                db.refresh(persisted_task)
            return _plan_to_dict(plan, tasks)

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with SessionLocal() as db:
            plan = db.get(MissionPlan, plan_id)
            if plan is None:
                return None
            tasks = db.scalars(
                select(MissionPlanTask)
                .where(MissionPlanTask.plan_id == plan_id)
                .order_by(MissionPlanTask.sequence)
            ).all()
            return _plan_to_dict(plan, list(tasks))

    def project_plans(self, project_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            plans = db.scalars(
                select(MissionPlan)
                .where(MissionPlan.project_id == project_id)
                .order_by(MissionPlan.created_at.desc())
            ).all()
        result = []
        for plan in plans:
            item = self.get_plan(plan.id)
            if item is not None:
                result.append(item)
        return result

    def approve(self, plan_id: str) -> dict[str, Any]:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise KeyError(plan_id)
        if plan["status"] != "draft":
            raise ValueError("Nur Missionsentwürfe können genehmigt werden.")

        created_tasks = []
        created_by_sequence: dict[int, str] = {}
        integration_ids: set[str] = set()
        for task in plan["tasks"]:
            description = (
                f"{task['description']}\n\nAbnahmekriterien:\n"
                f"{task['acceptance_criteria']}"
            )
            created = project_service.create_task(
                plan["project_id"],
                title=task["title"],
                description=description,
                status="planned",
                priority=task["priority"],
                task_type=task["task_type"],
                assigned_agent=task["agent_id"],
            )
            if created:
                created_tasks.append(created)
                created_by_sequence[task["sequence"]] = created["id"]
            integration_ids.update(task["integration_ids"])

        for task in plan["tasks"]:
            created_id = created_by_sequence.get(task["sequence"])
            if created_id is None:
                continue
            dependencies = [
                created_by_sequence[sequence]
                for sequence in task["dependencies"]
                if sequence in created_by_sequence
            ]
            project_service.update_task(
                created_id,
                {"dependencies": json.dumps(dependencies)},
            )

        for integration_id in integration_ids:
            integration_service.add_requirement(
                plan["project_id"],
                integration_id,
                purpose="Vom genehmigten BOSS-Missionsplan benötigt",
            )

        with SessionLocal() as db:
            row = db.get(MissionPlan, plan_id)
            if row is None:
                raise KeyError(plan_id)
            row.status = "approved"
            row.updated_at = datetime.now(UTC)
            db.commit()
        project_service.enable_autopilot(plan["project_id"])
        return {
            "plan": self.get_plan(plan_id),
            "created_tasks": [
                project_service.get_task(task["id"]) for task in created_tasks
            ],
            "integration_requirements": integration_service.requirements(
                plan["project_id"]
            ),
        }

    def _ollama_plan(self, goal: str, project: dict[str, Any]) -> MissionDraft:
        team = [
            {
                "id": agent["id"],
                "role": agent["title"],
                "capabilities": agent["capabilities"],
            }
            for agent in AGENTS
            if not agent.get("specialist")
        ]
        integrations = [
            {"id": item["id"], "purpose": item["description"]}
            for item in INTEGRATIONS
        ]
        prompt = f"""
Du bist BOSS, CEO und Chief Orchestrator eines lokalen Multi-Agent-Systems.
Zerlege das Ziel in einen realistischen, ausführbaren Missionsplan.

Projekt: {json.dumps(project, ensure_ascii=False)}
Ziel: {goal}
Team: {json.dumps(team, ensure_ascii=False)}
Verfügbare Integrationen: {json.dumps(integrations, ensure_ascii=False)}

Regeln:
- Weise jede Aufgabe genau einem passenden Agenten zu.
- Plane höchstens 12 klar abgegrenzte Aufgaben.
- Abhängigkeiten sind 1-basierte Sequenznummern früherer Aufgaben.
- Verwende nur aufgeführte Agenten, Aufgabentypen und Integrationen.
- Externe Kommunikation, Zahlungen und Veröffentlichungen als kontrollierte Aufgabe planen.
- Keine Umsatzgarantie behaupten; messbare führende Kennzahlen verwenden.
- Antworte ausschließlich im JSON-Schema.
JSON-Schema:
{json.dumps(MissionDraft.model_json_schema(), ensure_ascii=False)}
"""
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "format": "json",
                "options": {
                    "num_ctx": OLLAMA_CONTEXT,
                    "num_predict": max(OLLAMA_MAX_TOKENS, 4096),
                    "temperature": 0.2,
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        raw = re.sub(
            r"^```(?:json)?\s*|\s*```$", "", response.json()["response"].strip()
        )
        return MissionDraft.model_validate_json(raw)

    @staticmethod
    def _validate_draft(draft: MissionDraft) -> None:
        for sequence, task in enumerate(draft.tasks, start=1):
            if get_agent(task.agent_id) is None:
                raise ValueError(f"Unbekannter Agent: {task.agent_id}")
            if task.task_type not in TASK_TYPES:
                raise ValueError(f"Ungültiger Aufgabentyp: {task.task_type}")
            if any(item not in INTEGRATION_BY_ID for item in task.integration_ids):
                raise ValueError("Missionsplan enthält unbekannte Integration.")
            if any(item >= sequence or item < 1 for item in task.dependencies):
                raise ValueError("Missionsplan enthält ungültige Abhängigkeit.")
            agent_team.delegation_path("boss", task.agent_id)

    @staticmethod
    def _fallback_plan(goal: str, project: dict[str, Any]) -> MissionDraft:
        text = f"{goal} {project.get('category', '')}".lower()
        commercial = any(
            word in text
            for word in ("verkauf", "umsatz", "kunde", "website", "€", "euro", "business")
        )
        if commercial:
            return MissionDraft(
                summary="BOSS zerlegt das Geschäftsziel in validierbare Markt-, Produkt-, Vertriebs- und Lieferaufgaben.",
                strategy="Zuerst Nachfrage und Angebot validieren, danach ein wiederholbares Liefer- und Kontaktverfahren aufbauen und anhand führender Kennzahlen steuern.",
                assumptions=[
                    "Es steht zunächst kein bezahltes Werbebudget zur Verfügung.",
                    "Externe Kommunikation muss rechtlich geprüft und nachvollziehbar sein.",
                ],
                risks=[
                    "Umsatz und Reaktionsquote hängen von externen Entscheidungen ab.",
                    "Ungezielte Kontaktaufnahme kann rechtliche oder reputative Risiken erzeugen.",
                ],
                success_metrics=[
                    "Qualifizierte Zielunternehmen",
                    "Positive Antworten und Termine",
                    "Versendete Angebote",
                    "Bezahlte Aufträge und Deckungsbeitrag",
                ],
                tasks=[
                    MissionTaskDraft(title="Zielmarkt und Bedarf validieren", description="Branchenoffen lokale Unternehmen nach Kundengewinnungspotenzial, Website-Defizit, Kontaktierbarkeit und Auftragswert priorisieren und im Google-Sheets-CRM dokumentieren.", agent_id="atlas", task_type="research", priority=1, integration_ids=["google_workspace"], acceptance_criteria="Bis zu 20 priorisierte Leads mit Bedarfssignalen, Quellen und nachvollziehbarem Score."),
                    MissionTaskDraft(title="Angebot und Customer Journey entwerfen", description="Ein Starterpaket zwischen 200 und 500 EUR sowie einen minimalistischen, cineastischen Website-Ansatz anhand des AURA-Design-Briefs definieren.", agent_id="aura", task_type="design", priority=1, dependencies=[1], integration_ids=["google_workspace"], acceptance_criteria="Leistungsumfang, Zielkunde, Nutzenversprechen, Designrichtung und klare nächste Aktion sind dokumentiert."),
                    MissionTaskDraft(title="Lieferbaren Website-Prototyp bauen", description="Eine wiederverwendbare, schnelle Website-Basis mit messbarer Conversion-Aktion implementieren.", agent_id="forge", task_type="coding", priority=2, dependencies=[2], integration_ids=["github"], acceptance_criteria="Prototyp ist getestet, versioniert und lokal reproduzierbar."),
                    MissionTaskDraft(title="Kontakt- und Follow-up-Prozess entwerfen", description="Einen kontrollierten Prozess für qualifizierte E-Mail-Entwürfe, Antworten und Follow-ups definieren; kein automatischer Versand.", agent_id="flow", task_type="automation", priority=2, dependencies=[1, 2], integration_ids=["smtp", "n8n", "google_workspace"], acceptance_criteria="Prozess enthält CRM-Schreibpfad, Trigger, Freigabe, Abbruchregeln, Status und Fehlerpfade."),
                    MissionTaskDraft(title="Recht und Secrets prüfen", description="Datenschutz, zulässige Kontaktwege, Zugriffsumfang und Secret-Handhabung prüfen.", agent_id="sentinel", task_type="security", priority=1, dependencies=[4], acceptance_criteria="Freigegebene Kanäle, Verbote und Audit-Anforderungen sind dokumentiert."),
                    MissionTaskDraft(title="Vertriebs-KPIs und Zahlungsfluss definieren", description="Funnel-Kennzahlen, Tagesziele, Angebotsstatus und Zahlungseingänge messbar machen.", agent_id="orbit", task_type="data", priority=2, dependencies=[2, 5], integration_ids=["paypal"], acceptance_criteria="Funnel und Umsatzmetriken besitzen klare Definitionen und Datenquellen."),
                ],
            )
        return MissionDraft(
            summary="BOSS erstellt einen sicheren Analyse-, Umsetzungs- und Review-Pfad.",
            strategy="Ziel klären, Wissen aufbauen, Lösung entwerfen, umsetzen und messbar validieren.",
            assumptions=["Das Ziel kann mit den vorhandenen lokalen Ressourcen bearbeitet werden."],
            risks=["Unklare Abnahmekriterien können zu unnötiger Arbeit führen."],
            success_metrics=["Abgenommene Ergebnisse", "Keine offenen Blocker"],
            tasks=[
                MissionTaskDraft(title="Ziel und Randbedingungen analysieren", description="Ziel, Stakeholder, Abhängigkeiten und offene Fragen strukturieren.", agent_id="atlas", task_type="research", priority=1, acceptance_criteria="Entscheidungsgrundlage und offene Risiken sind dokumentiert."),
                MissionTaskDraft(title="Lösung und Nutzerweg entwerfen", description="Eine umsetzbare Lösung mit klaren Ergebnissen und Abnahmekriterien entwerfen.", agent_id="aura", task_type="design", priority=2, dependencies=[1], acceptance_criteria="Lösung, Ablauf und Abnahmekriterien sind eindeutig."),
                MissionTaskDraft(title="Technische Umsetzung planen", description="Technischen Umfang und ausführbare Arbeitspakete definieren.", agent_id="forge", task_type="coding", priority=2, dependencies=[2], integration_ids=["github"], acceptance_criteria="Technischer Plan ist testbar und sicher ausführbar."),
            ],
        )


mission_router = MissionRouter()
