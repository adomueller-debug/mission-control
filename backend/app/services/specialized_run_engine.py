from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from pydantic import BaseModel, Field

from backend.app.services.agent_team import agent_team
from backend.app.services.agent_contracts import contract_for
from backend.app.services.coder import (
    MODEL,
    OLLAMA_CONTEXT,
    OLLAMA_MAX_TOKENS,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
)
from backend.app.services.run_service import run_service


TASK_AGENTS = {
    "research": "atlas",
    "design": "aura",
    "business": "boss",
    "data": "orbit",
    "automation": "flow",
    "email": "flow",
    "calendar": "flow",
    "security": "sentinel",
    "devops": "mercury",
    "general": "boss",
}


class SpecializedArtifact(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=20_000)
    artifact_type: str = Field(default="document", max_length=50)


class SpecializedTaskOutput(BaseModel):
    status: str = Field(default="completed", pattern="^(completed|needs_setup|unsupported)$")
    summary: str = Field(min_length=2, max_length=5_000)
    findings: list[str] = Field(default_factory=list, max_length=30)
    artifacts: list[SpecializedArtifact] = Field(default_factory=list, max_length=12)
    next_actions: list[str] = Field(default_factory=list, max_length=20)
    sources: list[str] = Field(default_factory=list, max_length=30)


class SpecializedRunEngine:
    def execute(self, run_id: str) -> None:
        run = run_service.get(run_id)
        if run is None:
            return
        task_type = run["run_kind"].removeprefix("task:")
        agent = TASK_AGENTS.get(task_type, "boss")
        try:
            run_service.transition(run_id, "planning", agent)
            run_service.add_event(
                run_id,
                "plan.created",
                {
                    "summary": f"{agent} führt eine strukturierte {task_type}-Aufgabe aus.",
                    "steps": [
                        {"id": 1, "title": "Kontext analysieren", "agent": agent},
                        {"id": 2, "title": "Ergebnis erzeugen", "agent": agent},
                        {"id": 3, "title": "Ergebnis validieren", "agent": agent},
                    ],
                },
            )
            agent_team.remember(
                agent,
                f"Spezialisierte Aufgabe übernommen: {run['task']}",
                kind="assignment",
                run_id=run_id,
            )
            run_service.transition(run_id, "executing", agent)
            result, tool_name = self._execute_task(task_type, run["task"], agent)
            current = run_service.get(run_id)
            run_service.update(
                run_id,
                tool_calls=(current["tool_calls"] if current else 0) + 1,
            )
            run_service.add_event(
                run_id,
                "tool.completed",
                {"tool": tool_name, "result": result.model_dump()},
            )
            run_service.transition(run_id, "validating", agent)
            validation = self._validate_result(task_type, result)
            if result.status != "completed":
                payload = {
                    "status": result.status,
                    "summary": result.summary,
                    "files": [],
                    "findings": result.findings,
                    "artifacts": [item.model_dump() for item in result.artifacts],
                    "next_actions": result.next_actions,
                    "sources": result.sources,
                    "validation": validation,
                    "executor": {"task_type": task_type, "agent": agent},
                }
                run_service.update(run_id, result=payload, error=result.summary)
                run_service.add_event(
                    run_id,
                    "agent.blocked",
                    {"agent": agent, "reason": result.status},
                )
                run_service.transition(run_id, "failed", agent)
                return
            if not validation["success"]:
                raise ValueError(
                    "Agentenvertrag nicht erfüllt: "
                    + "; ".join(
                        check["output"]
                        for check in validation["checks"]
                        if not check["success"]
                    )
                )
            payload = {
                "status": result.status,
                "summary": result.summary,
                "files": [],
                "findings": result.findings,
                "artifacts": [item.model_dump() for item in result.artifacts],
                "next_actions": result.next_actions,
                "sources": result.sources,
                "validation": validation,
                "executor": {"task_type": task_type, "agent": agent},
            }
            run_service.update(run_id, result=payload)
            run_service.save_checkpoint(
                run_id,
                {"phase": "completed", "result": payload},
            )
            agent_team.remember(
                agent,
                result.summary,
                kind="result",
                run_id=run_id,
            )
            run_service.add_event(run_id, "agent.completed", {"agent": agent})
            run_service.transition(run_id, "completed", agent)
        except Exception as exc:
            run_service.update(run_id, error=str(exc))
            run_service.add_event(run_id, "run.error", {"message": str(exc)})
            run_service.transition(run_id, "failed", agent)

    @staticmethod
    def _validate_result(
        task_type: str, result: SpecializedTaskOutput
    ) -> dict[str, Any]:
        contract = contract_for(task_type)
        artifact_types = {item.artifact_type for item in result.artifacts}
        missing_types = set(contract.required_artifact_types).difference(artifact_types)
        placeholder_markers = ("lorem ipsum", "todo", "tbd", "beispielquelle")
        combined = " ".join(
            [result.summary, *result.findings, *(item.content for item in result.artifacts)]
        ).casefold()
        placeholders = sorted(
            marker for marker in placeholder_markers if marker in combined
        )
        research_sources_valid = task_type != "research" or bool(result.sources)
        artifact_substance = all(
            len(re.sub(r"\s+", " ", item.content).strip()) >= 200
            for item in result.artifacts
        )
        semantic_valid, semantic_output = SpecializedRunEngine._semantic_contract(
            task_type, combined
        )
        checks = [
            {
                "name": "structured-output",
                "success": True,
                "output": "Pydantic-Schema erfüllt",
            },
            {
                "name": "minimum-artifacts",
                "success": len(result.artifacts) >= contract.minimum_artifacts,
                "output": (
                    f"{len(result.artifacts)}/{contract.minimum_artifacts} Artefakte"
                ),
            },
            {
                "name": "required-artifact-types",
                "success": not missing_types,
                "output": (
                    "Pflichtartefakte vorhanden"
                    if not missing_types
                    else "Fehlend: " + ", ".join(sorted(missing_types))
                ),
            },
            {
                "name": "placeholder-free",
                "success": not placeholders,
                "output": (
                    "Keine Platzhalter"
                    if not placeholders
                    else "Platzhalter: " + ", ".join(placeholders)
                ),
            },
            {
                "name": "artifact-substance",
                "success": artifact_substance,
                "output": "Artefakte sind substanziell" if artifact_substance else "Mindestens ein Artefakt ist zu knapp (< 200 Zeichen)",
            },
            {
                "name": "contract-semantics",
                "success": semantic_valid,
                "output": semantic_output,
            },
            {
                "name": "research-sources",
                "success": research_sources_valid,
                "output": (
                    "Quellen vorhanden oder nicht erforderlich"
                    if research_sources_valid
                    else "Research-Ergebnis enthält keine geprüfte Quelle"
                ),
            },
        ]
        return {
            "success": result.status == "completed"
            and all(bool(check["success"]) for check in checks),
            "checks": [
                *checks,
                {
                    "name": "role-contract",
                    "success": True,
                    "output": contract.purpose,
                },
            ],
        }

    @staticmethod
    def _semantic_contract(task_type: str, combined: str) -> tuple[bool, str]:
        requirements: dict[str, tuple[tuple[str, ...], ...]] = {
            "email": (("betreff", "subject"), ("sehr geehrt", "hallo", "guten tag")),
            "calendar": (("zeitzone", "timezone"), ("beginn", "start"), ("ende", "end")),
            "security": (
                ("secret", "geheimnis", "zugangsdaten"),
                ("personenbezogen", "datenschutz", "dsgvo"),
                ("berechtigung", "permission"),
                ("risiko", "risk"),
                ("freigabe", "approval"),
            ),
            "design": (
                ("typografie", "typography"),
                ("mobile", "responsive"),
                ("motion", "animation"),
                ("accessibility", "barriere"),
            ),
            "data": (("formel", "berechnung"), ("datenquelle", "source"), ("einheit", "unit")),
        }
        groups = requirements.get(task_type, ())
        missing = ["/".join(group) for group in groups if not any(term in combined for term in group)]
        if missing:
            return False, "Inhaltlich fehlend: " + ", ".join(missing)
        return True, "Rollenbezogene Pflichtinhalte vorhanden"

    def _execute_task(
        self, task_type: str, task: str, agent: str
    ) -> tuple[SpecializedTaskOutput, str]:
        webhook = os.getenv("N8N_TASK_EXECUTOR_WEBHOOK_URL", "").strip()
        if webhook and task_type in {"research", "business", "automation", "data"}:
            response = requests.post(
                webhook,
                json={
                    "task_type": task_type,
                    "agent": agent,
                    "task": task,
                    "draft_only": True,
                },
                timeout=60,
            )
            response.raise_for_status()
            return SpecializedTaskOutput.model_validate(response.json()), "n8n.execute_task"

        contract = contract_for(task_type)
        prompt = f"""
Du bist {agent}, ein spezialisierter Agent in Mission Control.
Aufgabentyp: {task_type}
Aufgabe und Projektkontext:
{task}

Erzeuge ein belastbares, direkt nutzbares Arbeitsergebnis.
- Dein verbindlicher Rollenauftrag: {contract.purpose}
- Pflicht-Artefakttypen: {', '.join(contract.required_artifact_types)}
- Mindestanzahl Artefakte: {contract.minimum_artifacts}
- Qualitätsregeln: {json.dumps(contract.quality_rules, ensure_ascii=False)}
- Trenne Fakten, Annahmen und nächste Schritte.
- Erfinde keine Quellen oder externen Prüfungen.
- Bei Research: Quellen nur aufführen, wenn sie im Kontext enthalten oder tatsächlich geprüft wurden.
- Bei Design: liefere ein konkretes UX-/Design-Artefakt.
- Bei Business: liefere Entscheidungsvorlage, Angebot oder Prozessartefakt.
- Bei Data: definiere Kennzahlen, Berechnung und Datenquelle.
- Bei Automation: liefere Workflow, Trigger, Schritte, Fehlerpfade und Freigaben.
- Externe Nachrichten bleiben Entwürfe und dürfen nicht automatisch versendet werden.
Antworte ausschließlich im vorgegebenen JSON-Schema.
JSON-Schema:
{json.dumps(SpecializedTaskOutput.model_json_schema(), ensure_ascii=False)}
"""
        last_error = ""
        for attempt in range(3):
            retry = (
                "\nDie vorherige Antwort verletzte den Agentenvertrag: "
                f"{last_error}. Erzeuge alle Pflichtartefakte ohne Platzhalter."
                if last_error
                else ""
            )
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt + retry,
                    "stream": False,
                    "think": False,
                    "format": "json",
                    "options": {
                        "num_ctx": OLLAMA_CONTEXT,
                        "num_predict": max(OLLAMA_MAX_TOKENS, 4096),
                        "temperature": 0.1 if attempt else 0.15,
                    },
                },
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            raw = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                response.json()["response"].strip(),
            )
            try:
                result = SpecializedTaskOutput.model_validate_json(raw)
                validation = self._validate_result(task_type, result)
                if validation["success"] or result.status != "completed":
                    return result, "ollama.specialized"
                last_error = "; ".join(
                    str(check["output"])
                    for check in validation["checks"]
                    if not check["success"]
                )
            except ValueError as exc:
                last_error = str(exc)
        raise ValueError(
            "Ollama konnte den Agentenvertrag nach drei Versuchen nicht erfüllen: "
            + last_error
        )


specialized_run_engine = SpecializedRunEngine()
