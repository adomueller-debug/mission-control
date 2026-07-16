from __future__ import annotations

import json
import re
import threading
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from backend.app.core.workspace_security import resolve_workspace
from backend.app.database.database import SessionLocal
from backend.app.models.run import AgentRun, RunCheckpoint, RunEvent
from backend.app.services.workspace_sandbox import discard_isolated_workspace


TERMINAL_STATES = {"completed", "failed", "cancelled"}
RUN_STATES = {
    "queued",
    "planning",
    "executing",
    "validating",
    "publishing",
    *TERMINAL_STATES,
}
SECRET_PATTERN = re.compile(
    r"(token|secret|password|authorization|api[_-]?key|cookie)", re.IGNORECASE
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SECRET_PATTERN.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def run_to_dict(run: AgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "task": run.task,
        "workspace": run.workspace,
        "source_workspace": run.source_workspace or run.workspace,
        "run_kind": run.run_kind,
        "workstream": run.workstream,
        "status": run.status,
        "current_step": run.current_step,
        "plan": json.loads(run.plan) if run.plan else None,
        "result": json.loads(run.result) if run.result else None,
        "error": run.error or None,
        "branch": run.branch or None,
        "pr_url": run.pr_url or None,
        "cancel_requested": run.cancel_requested,
        "publish": run.publish,
        "tool_calls": run.tool_calls,
        "repair_attempts": run.repair_attempts,
        "limits": {
            "max_tool_calls": run.max_tool_calls,
            "max_repair_attempts": run.max_repair_attempts,
            "timeout_seconds": run.timeout_seconds,
        },
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


def event_to_dict(event: RunEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "run_id": event.run_id,
        "type": event.event_type,
        "payload": json.loads(event.payload),
        "created_at": event.created_at.isoformat(),
    }


class RunService:
    def create(
        self,
        *,
        task: str,
        workspace: str,
        publish: bool = False,
        timeout_seconds: int = 1200,
        max_tool_calls: int = 50,
        max_repair_attempts: int = 5,
        run_kind: str = "coding",
        workstream: str = "standalone",
        start: bool = True,
    ) -> dict[str, Any]:
        root = resolve_workspace(workspace)
        run = AgentRun(
            task=task.strip(),
            workspace=str(root),
            source_workspace=str(root),
            run_kind=run_kind,
            workstream=workstream,
            publish=publish,
            timeout_seconds=timeout_seconds,
            max_tool_calls=max_tool_calls,
            max_repair_attempts=max_repair_attempts,
        )
        with SessionLocal() as db:
            active = db.scalar(
                select(AgentRun.id).where(
                    AgentRun.source_workspace == str(root),
                    AgentRun.status.not_in(TERMINAL_STATES),
                )
            )
            if active is not None:
                raise ValueError(f"Workspace wird bereits von Run {active} verwendet.")
            db.add(run)
            db.commit()
            db.refresh(run)
            result = run_to_dict(run)
        self.add_event(
            run.id,
            "run.created",
            {"task": task, "publish": publish, "run_kind": run_kind},
        )
        if start:
            self.start(run.id)
        return result

    def start(self, run_id: str) -> None:
        run = self.get(run_id)
        if run is None:
            raise KeyError(run_id)
        if run["run_kind"] == "coding":
            from backend.app.services.run_engine import run_engine

            target = run_engine.execute
        else:
            from backend.app.services.specialized_run_engine import specialized_run_engine

            target = specialized_run_engine.execute

        thread = threading.Thread(
            target=target,
            args=(run_id,),
            daemon=True,
            name=f"mission-control-{run_id[:8]}",
        )
        thread.start()

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            runs = db.scalars(
                select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
            ).all()
            return [run_to_dict(run) for run in runs]

    def get(self, run_id: str) -> dict[str, Any] | None:
        with SessionLocal() as db:
            run = db.get(AgentRun, run_id)
            return run_to_dict(run) if run else None

    def get_model(self, run_id: str) -> AgentRun | None:
        with SessionLocal() as db:
            run = db.get(AgentRun, run_id)
            if run is not None:
                db.expunge(run)
            return run

    def update(self, run_id: str, **fields: Any) -> dict[str, Any]:
        if "status" in fields and fields["status"] not in RUN_STATES:
            raise ValueError(f"Ungültiger Run-Status: {fields['status']}")
        with SessionLocal() as db:
            run = db.get(AgentRun, run_id)
            if run is None:
                raise KeyError(run_id)
            for key, value in fields.items():
                if key in {"plan", "result"} and not isinstance(value, str):
                    value = _json(redact(value))
                setattr(run, key, value)
            run.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(run)
            return run_to_dict(run)

    def transition(self, run_id: str, status: str, step: str | None = None) -> None:
        self.update(run_id, status=status, current_step=step)
        self.add_event(run_id, "run.status", {"status": status, "step": step})

    def cancel(self, run_id: str) -> dict[str, Any] | None:
        current = self.get(run_id)
        if current is None:
            return None
        if current["status"] in TERMINAL_STATES:
            return current
        result = self.update(run_id, cancel_requested=True)
        self.add_event(run_id, "run.cancel_requested", {})
        return result

    def resume(self, run_id: str) -> dict[str, Any] | None:
        current = self.get(run_id)
        if current is None:
            return None
        if current["status"] not in {"failed", "cancelled"}:
            raise ValueError("Nur fehlgeschlagene oder abgebrochene Runs können fortgesetzt werden.")
        discard_isolated_workspace(current["source_workspace"], run_id)
        with SessionLocal() as db:
            checkpoint = db.get(RunCheckpoint, run_id)
            if checkpoint is not None:
                db.delete(checkpoint)
                db.commit()
        result = self.update(
            run_id,
            status="queued",
            current_step=None,
            cancel_requested=False,
            error="",
            result="",
            tool_calls=0,
            repair_attempts=0,
        )
        self.add_event(run_id, "run.resume_requested", {})
        self.start(run_id)
        return result

    def is_cancelled(self, run_id: str) -> bool:
        current = self.get(run_id)
        return current is None or bool(current["cancel_requested"])

    def add_event(self, run_id: str, event_type: str, payload: Any) -> dict[str, Any]:
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            payload=_json(redact(payload)),
        )
        with SessionLocal() as db:
            db.add(event)
            db.commit()
            db.refresh(event)
            return event_to_dict(event)

    def events(self, run_id: str, after: int = 0) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            events = db.scalars(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.id > after)
                .order_by(RunEvent.id)
            ).all()
            return [event_to_dict(event) for event in events]

    def report(self, run_id: str) -> str | None:
        run = self.get(run_id)
        if run is None:
            return None
        events = self.events(run_id)
        lines = [
            f"# Mission Control Run {run_id}",
            "",
            f"- Status: {run['status']}",
            f"- Aufgabe: {run['task']}",
            f"- Workspace: `{run['workspace']}`",
            f"- Tool-Aufrufe: {run['tool_calls']}",
        ]
        if run["pr_url"]:
            lines.append(f"- Pull Request: {run['pr_url']}")
        lines.extend(["", "## Ereignisse", ""])
        for event in events:
            lines.append(
                f"- {event['created_at']} — **{event['type']}**: "
                f"`{_json(event['payload'])}`"
            )
        if run["error"]:
            lines.extend(["", "## Fehler", "", run["error"]])
        return "\n".join(lines) + "\n"

    def save_checkpoint(self, run_id: str, state: dict[str, Any]) -> None:
        with SessionLocal() as db:
            checkpoint = db.get(RunCheckpoint, run_id)
            if checkpoint is None:
                checkpoint = RunCheckpoint(run_id=run_id)
                db.add(checkpoint)
            checkpoint.state = _json(redact(state))
            checkpoint.updated_at = datetime.now(UTC)
            db.commit()

    def load_checkpoint(self, run_id: str) -> dict[str, Any]:
        with SessionLocal() as db:
            checkpoint = db.get(RunCheckpoint, run_id)
            return json.loads(checkpoint.state) if checkpoint else {}

    def resume_incomplete(self) -> None:
        with SessionLocal() as db:
            run_ids = list(
                db.scalars(
                    select(AgentRun.id).where(
                        AgentRun.status.in_(
                            {"queued", "planning", "executing", "validating", "publishing"}
                        )
                    )
                ).all()
            )
        for run_id in run_ids:
            self.add_event(run_id, "run.resumed", {})
            self.start(run_id)


run_service = RunService()
