from __future__ import annotations

import json
import os
import re

import requests
from pydantic import BaseModel, Field

from backend.app.services.agent_team import agent_team
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
    "security": "sentinel",
    "devops": "mercury",
    "general": "boss",
}


class SpecializedArtifact(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=20_000)
    artifact_type: str = Field(default="document", max_length=50)


class SpecializedTaskOutput(BaseModel):
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
            validation = {
                "success": bool(result.summary and result.artifacts),
                "checks": [
                    {
                        "name": "structured-output",
                        "success": True,
                        "output": "Pydantic-Schema erfüllt",
                    },
                    {
                        "name": "deliverable-present",
                        "success": bool(result.artifacts),
                        "output": f"{len(result.artifacts)} Artefakt(e)",
                    },
                ],
            }
            if not validation["success"]:
                raise ValueError("Spezialisierter Executor hat kein Artefakt geliefert.")
            payload = {
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

        prompt = f"""
Du bist {agent}, ein spezialisierter Agent in Mission Control.
Aufgabentyp: {task_type}
Aufgabe und Projektkontext:
{task}

Erzeuge ein belastbares, direkt nutzbares Arbeitsergebnis.
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
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "think": False,
                # Some Ollama backends cannot compile nested JSON Schemas with
                # $defs into a grammar. JSON mode plus Pydantic validation keeps
                # the contract strict without depending on that grammar parser.
                "format": "json",
                "options": {
                    "num_ctx": OLLAMA_CONTEXT,
                    "num_predict": max(OLLAMA_MAX_TOKENS, 3072),
                    "temperature": 0.15,
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
        return SpecializedTaskOutput.model_validate_json(raw), "ollama.specialized"


specialized_run_engine = SpecializedRunEngine()
