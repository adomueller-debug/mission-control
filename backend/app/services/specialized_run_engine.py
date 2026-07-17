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
from backend.app.services.website_sales_pipeline import OverpassLeadResearcher


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
                ("risiko", "risk", "gefährdung", "schweregrad"),
                ("freigabe", "approval", "genehmigung", "bestätigung", "zustimmung"),
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
        if task_type == "research" and self._is_local_lead_research(task):
            return self._execute_local_lead_research(task), "openstreetmap.overpass"

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
            result = SpecializedTaskOutput.model_validate(response.json())
            result = self._canonicalize_artifact_types(task_type, result)
            return self._apply_deterministic_policy(task_type, result), "n8n.execute_task"

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
- Bei Security: nenne ausdrücklich Risiko, Risikostufe, Abhilfe und Freigabebedarf. Eine Sicherheitsprüfung erteilt selbst niemals eine Freigabe für Außenwirkungen.
- Externe Nachrichten bleiben Entwürfe und dürfen nicht automatisch versendet werden.
Antworte ausschließlich im vorgegebenen JSON-Schema.
JSON-Schema (artifact_type muss exakt einem Enum-Wert entsprechen):
{json.dumps(self._output_schema(task_type), ensure_ascii=False)}
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
                    "format": self._output_schema(task_type),
                    "options": {
                        "num_ctx": OLLAMA_CONTEXT,
                        "num_predict": max(OLLAMA_MAX_TOKENS, 4096),
                        "temperature": 0.1 if attempt else 0.15,
                    },
                },
                timeout=OLLAMA_TIMEOUT,
            )
            if response.status_code == 400:
                # Older Ollama versions accept JSON mode but reject parts of a
                # full JSON Schema. The prompt still contains the contract and
                # the result is validated locally below.
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
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                detail = response.text.strip()[:1_000]
                raise RuntimeError(
                    f"Ollama-Anfrage fehlgeschlagen ({response.status_code}): {detail}"
                ) from exc
            raw = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                response.json()["response"].strip(),
            )
            try:
                result = self._canonicalize_artifact_types(
                    task_type, SpecializedTaskOutput.model_validate_json(raw)
                )
                result = self._apply_deterministic_policy(task_type, result)
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

    @staticmethod
    def _output_schema(task_type: str) -> dict[str, Any]:
        schema = SpecializedTaskOutput.model_json_schema()
        contract = contract_for(task_type)
        artifact = schema.get("$defs", {}).get("SpecializedArtifact", {})
        properties = artifact.get("properties", {})
        artifact_type = properties.get("artifact_type", {})
        artifact_type["enum"] = list(contract.required_artifact_types)
        artifact_type.pop("default", None)
        artifact_type["description"] = "Verbindlicher Artefakttyp; exakt einen Enum-Wert verwenden."
        artifacts = schema.get("properties", {}).get("artifacts", {})
        artifacts["minItems"] = contract.minimum_artifacts
        return schema

    @staticmethod
    def _canonicalize_artifact_types(
        task_type: str, result: SpecializedTaskOutput
    ) -> SpecializedTaskOutput:
        contract = contract_for(task_type)
        required = set(contract.required_artifact_types)
        present = {item.artifact_type for item in result.artifacts}
        if required.issubset(present) or len(required) != 1:
            return result
        generic_aliases = {
            "document",
            "report",
            "brief",
            "research",
            "research_brief",
            task_type,
        }
        candidates = [
            item
            for item in result.artifacts
            if item.artifact_type.casefold() in generic_aliases
            and len(re.sub(r"\s+", " ", item.content).strip()) >= 200
        ]
        if len(candidates) == 1:
            previous = candidates[0].artifact_type
            candidates[0].artifact_type = next(iter(required))
            result.findings.append(
                f"Artefakttyp '{previous}' wurde anhand des Rollenvertrags zu "
                f"'{candidates[0].artifact_type}' normalisiert."
            )
        return result

    @staticmethod
    def _apply_deterministic_policy(
        task_type: str,
        result: SpecializedTaskOutput,
    ) -> SpecializedTaskOutput:
        """Attach non-negotiable local policy instead of asking the LLM to invent it."""
        if task_type != "security" or result.status != "completed":
            return result
        review = next(
            (
                item
                for item in result.artifacts
                if item.artifact_type == "security_review"
            ),
            None,
        )
        if review is None:
            return result

        policy = (
            "\n\nDeterministische Mission-Control-Risikopolicy:\n"
            "Risiko und Risikostufe: Lokale Analyse und Entwürfe sind Stufe 0; "
            "protokollierte Drive-, CRM- und Git-Branch-Aktionen Stufe 1; "
            "E-Mail-Versand, Kalendereinladungen, Veröffentlichungen und Deployments "
            "Stufe 2; Käufe, Zahlungen, Verträge, externe Löschungen und "
            "Berechtigungsänderungen Stufe 3.\n"
            "Freigabe: Stufe 2 benötigt eine gebündelte Approval-Entscheidung und "
            "Stufe 3 immer eine einzelne Bestätigung mit Empfänger, Inhalt, Betrag "
            "und Auswirkung. Dieser Security Review erteilt selbst keine Freigabe "
            "und führt keine Außenwirkung aus. Secrets bleiben außerhalb von Prompts, "
            "Events und Artefakten; personenbezogene Daten werden minimiert und "
            "Berechtigungen nach dem Least-Privilege-Prinzip vergeben."
        )
        review.content = review.content[: 20_000 - len(policy)] + policy
        marker = "Mission-Control-Risikopolicy wurde deterministisch angewendet."
        if marker not in result.findings:
            result.findings.append(marker)
        return result

    @staticmethod
    def _is_local_lead_research(task: str) -> bool:
        lower = task.casefold()
        return bool(
            re.search(r"\b(lead|unternehmen|betrieb|zielmarkt)\w*\b", lower)
            and re.search(r"\b(website|webseite|kundengewinnung|crm)\w*\b", lower)
        )

    @staticmethod
    def _execute_local_lead_research(task: str) -> SpecializedTaskOutput:
        city_match = re.search(
            r"(?:region|stadt|ort|in)\s*[:=-]?\s*([A-ZÄÖÜ][A-Za-zÄÖÜäöüß-]{2,})",
            task,
        )
        city = city_match.group(1) if city_match else "Heidelberg"
        limit_match = re.search(r"(?:maximal|bis zu|für den anfang)\s+(\d{1,2})", task, re.IGNORECASE)
        limit = min(20, max(1, int(limit_match.group(1)) if limit_match else 20))
        leads = OverpassLeadResearcher().find(city, limit)
        if not leads:
            return SpecializedTaskOutput(
                status="needs_setup",
                summary=f"Für {city} wurden in der öffentlichen Datenquelle keine passenden Einträge gefunden.",
                next_actions=["Ort oder Suchkriterien anpassen und Recherche erneut starten."],
            )
        rows = [lead.model_dump() for lead in leads]
        content = json.dumps(
            {
                "city": city,
                "method": "OpenStreetMap/Overpass; Website- und Kontaktdaten aus öffentlichen Brancheneinträgen",
                "lead_count": len(rows),
                "leads": rows,
                "limitations": [
                    "Fehlender Website-Link ist ein Bedarfssignal, aber kein Beweis, dass keine Website existiert.",
                    "Bestehende Websites benötigen vor Kontaktaufnahme eine manuelle UX-Prüfung.",
                    "Es wurden keine E-Mails versendet.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        return SpecializedTaskOutput(
            summary=f"ATLAS hat {len(rows)} öffentliche Unternehmenseinträge in {city} priorisiert.",
            findings=[
                f"{lead.name}: Opportunity {lead.opportunity_score}/100 – "
                + "; ".join(lead.reasons)
                for lead in leads[:10]
            ],
            artifacts=[
                SpecializedArtifact(
                    title=f"Lead-Recherche {city}",
                    content=content,
                    artifact_type="research_report",
                )
            ],
            next_actions=[
                "Leads mit öffentlicher geschäftlicher E-Mail manuell verifizieren.",
                "FLOW kann verifizierte Leads anschließend in CRM und Entwürfe überführen.",
            ],
            sources=[lead.source_url for lead in leads],
        )


specialized_run_engine = SpecializedRunEngine()
