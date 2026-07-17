from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
import json
from pathlib import Path
import threading
import time
from time import monotonic
from typing import Any

from sqlalchemy import select, update

from backend.app.database.database import SessionLocal
from backend.app.models.mission_v2 import (
    AgentAssignment,
    AuditedToolCall,
    Mission,
    QualityGate,
    WorkItem,
)
from backend.app.models.project import Project
from backend.app.services.engineering_quality import create_technical_blueprint
from backend.app.services.mission_v2_service import mission_v2_service
from backend.app.services.planner import create_execution_plan
from backend.app.services.run_engine import run_engine
from backend.app.services.run_service import run_service
from backend.app.services.specialized_run_engine import specialized_run_engine


LOCAL_GENERATION = threading.Semaphore(1)


class MissionSchedulerV2:
    """Persistent DAG scheduler; database state is the source of truth."""

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def start(self, mission_id: str) -> None:
        with self._lock:
            if mission_id in self._active:
                return
            self._active.add(mission_id)
        threading.Thread(target=self._run, args=(mission_id,), daemon=True, name=f"v2-{mission_id[:8]}").start()

    def recover(self) -> None:
        with SessionLocal() as db:
            mission_v2_service.recover_expired_leases(db)
            # A new process cannot own assignments left active by its predecessor.
            interrupted_missions = set(
                db.scalars(
                    select(WorkItem.mission_id).where(WorkItem.status == "active")
                )
            )
            db.execute(
                update(WorkItem)
                .where(WorkItem.status == "active")
                .values(status="retrying")
            )
            db.execute(
                update(AgentAssignment)
                .where(AgentAssignment.status == "active")
                .values(status="queued", worker_id="")
            )
            db.commit()
            ids = set(
                db.scalars(
                    select(Mission.id).where(
                        Mission.status.in_(["ready", "running", "validating"])
                    )
                )
            )
            ids.update(interrupted_missions)
        for mission_id in ids:
            self.start(mission_id)

    def _run(self, mission_id: str) -> None:
        try:
            while True:
                with SessionLocal() as db:
                    mission = db.get(Mission, mission_id)
                    if mission is None or mission.cancel_requested or mission.status in {"completed", "failed", "cancelled"}:
                        return
                    mission_v2_service.refresh_ready_items(db, mission_id)
                    ready = list(
                        db.scalars(
                            select(WorkItem).where(
                                WorkItem.mission_id == mission_id,
                                WorkItem.status == "ready",
                            ).order_by(WorkItem.priority, WorkItem.created_at).limit(3)
                        )
                    )
                    ready_ids = [item.id for item in ready]
                    active = db.scalar(
                        select(WorkItem.id).where(
                            WorkItem.mission_id == mission_id,
                            WorkItem.status == "active",
                        ).limit(1)
                    )
                    if not ready:
                        unfinished = list(
                            db.scalars(
                                select(WorkItem).where(
                                    WorkItem.mission_id == mission_id,
                                    WorkItem.status.not_in(["completed", "skipped"]),
                                )
                            )
                        )
                        if not unfinished:
                            mission.status = "completed"
                            db.commit()
                            return
                        if any(item.status == "blocked" for item in unfinished):
                            mission.status = "blocked"
                            db.commit()
                            return
                        if not active:
                            # DAG validation guarantees a future ready node; another worker may
                            # be committing its completion between this query and the next loop.
                            db.commit()
                    else:
                        mission.status = "running"
                        db.commit()
                if ready_ids:
                    with ThreadPoolExecutor(max_workers=min(3, len(ready_ids))) as pool:
                        futures = [pool.submit(self._execute_item, item_id) for item_id in ready_ids]
                        for future in as_completed(futures):
                            future.result()
                else:
                    time.sleep(0.25)
        finally:
            with self._lock:
                self._active.discard(mission_id)

    def _execute_item(self, item_id: str) -> None:
        started = monotonic()
        with SessionLocal() as db:
            item = db.get(WorkItem, item_id)
            if item is None or item.status != "ready":
                return
            assignment = db.scalar(select(AgentAssignment).where(AgentAssignment.work_item_id == item_id))
            mission = db.get(Mission, item.mission_id)
            if assignment is None or mission is None:
                return
            item.status = assignment.status = "active"
            item.attempts += 1
            assignment.started_at = datetime.now(UTC)
            assignment.heartbeat_at = datetime.now(UTC)
            db.commit()
            goal = mission.goal
            project = db.get(Project, mission.project_id) if mission.project_id else None
            workspace = project.workspace if project else str(Path.cwd())
            agent_id = item.agent_id
            tool_kind = (json.loads(item.required_tools) or ["general"])[0]
            tool_call = AuditedToolCall(
                mission_id=mission.id,
                work_item_id=item.id,
                assignment_id=assignment.id,
                agent_id=agent_id,
                tool_name=tool_kind,
                risk_level=item.risk_level,
                idempotency_key=f"{item.id}:{item.attempts}",
                status="active",
                request_redacted=json.dumps({"goal": goal}, ensure_ascii=False),
                timeout_seconds=1200,
            )
            db.add(tool_call)
            db.commit()
            tool_call_id = tool_call.id
        try:
            output = self._perform(agent_id, tool_kind, goal, workspace, item_id)
            with SessionLocal() as db:
                item = db.get(WorkItem, item_id)
                assignment = db.scalar(select(AgentAssignment).where(AgentAssignment.work_item_id == item_id))
                if item is None or assignment is None:
                    return
                self._require_expected_artifacts(item, output)
                item.status = "completed"
                assignment.status = "completed"
                assignment.output_data = json.dumps(output, ensure_ascii=False, default=str)
                assignment.completed_at = datetime.now(UTC)
                call = db.get(AuditedToolCall, tool_call_id)
                if call:
                    call.status = "completed"
                    call.result_redacted = json.dumps(output, ensure_ascii=False, default=str)
                    call.duration_ms = round((monotonic() - started) * 1000)
                    call.completed_at = datetime.now(UTC)
                for criterion in json.loads(item.acceptance_criteria):
                    db.add(QualityGate(mission_id=item.mission_id, work_item_id=item.id, name=criterion, status="passed", details=json.dumps({"evidence": output}, ensure_ascii=False, default=str), checked_at=datetime.now(UTC)))
                mission_v2_service.refresh_ready_items(db, item.mission_id)
                db.commit()
        except Exception as exc:
            with SessionLocal() as db:
                item = db.get(WorkItem, item_id)
                assignment = db.scalar(select(AgentAssignment).where(AgentAssignment.work_item_id == item_id))
                if item is None or assignment is None:
                    return
                item.status = "retrying" if item.attempts < item.max_attempts else "blocked"
                assignment.status = item.status
                assignment.error = str(exc)
                call = db.get(AuditedToolCall, tool_call_id)
                if call:
                    call.status = "failed"
                    call.error_class = type(exc).__name__
                    call.error = str(exc)
                    call.duration_ms = round((monotonic() - started) * 1000)
                    call.completed_at = datetime.now(UTC)
                db.commit()

    def _perform(self, agent_id: str, tool_kind: str, goal: str, workspace: str, item_id: str) -> dict[str, Any]:
        if agent_id == "forge_planner":
            plan = create_execution_plan(goal, workspace)
            return {"artifact": create_technical_blueprint(plan, workspace).model_dump(), "tool": "repository.blueprint"}
        if agent_id == "forge_builder":
            with LOCAL_GENERATION:
                run = run_service.create(task=goal, workspace=workspace, publish=False, start=False, workstream=f"mission-v2:{item_id}")
                run_engine.execute(run["id"])
            completed = run_service.get(run["id"])
            if not completed or completed["status"] != "completed":
                raise RuntimeError((completed or {}).get("error") or "Builder-Run fehlgeschlagen")
            return {"run_id": run["id"], "result": completed.get("result", {}), "tool": "coding.pipeline"}
        if agent_id in {"forge_reviewer", "forge_publisher"}:
            with SessionLocal() as db:
                current_item = db.get(WorkItem, item_id)
                if current_item is None:
                    raise RuntimeError("Work Item wurde während der Prüfung entfernt")
                assignment = db.scalar(
                    select(AgentAssignment)
                    .join(WorkItem, AgentAssignment.work_item_id == WorkItem.id)
                    .where(
                        WorkItem.mission_id == current_item.mission_id,
                        AgentAssignment.output_data.like('%"run_id"%'),
                    )
                    .order_by(AgentAssignment.created_at.desc())
                )
            if assignment is None:
                raise RuntimeError("Kein Builder-Ergebnis als Prüfnachweis vorhanden")
            evidence = json.loads(assignment.output_data)
            result = evidence.get("result", {})
            key = "validation" if agent_id == "forge_reviewer" else "release_candidate"
            artifact = result.get(key)
            if not artifact:
                raise RuntimeError(f"Builder-Run enthält kein {key}-Artefakt")
            return {"artifact": artifact, "source_run_id": evidence["run_id"], "tool": f"engineering.{key}"}
        task_type = tool_kind if tool_kind in {"research", "design", "business", "data", "automation", "email", "calendar", "security", "devops"} else "general"
        with LOCAL_GENERATION:
            result, tool = specialized_run_engine._execute_task(task_type, goal, agent_id)
        validation = specialized_run_engine._validate_result(task_type, result)
        if result.status != "completed" or not validation["success"]:
            raise RuntimeError(result.summary)
        return {"result": result.model_dump(), "validation": validation, "tool": tool}

    @staticmethod
    def _require_expected_artifacts(item: WorkItem, output: dict[str, Any]) -> None:
        expected = set(json.loads(item.expected_artifacts))
        if not expected:
            return
        actual: set[str] = set()
        artifact = output.get("artifact")
        if isinstance(artifact, dict) and artifact.get("artifact_type"):
            actual.add(str(artifact["artifact_type"]))
        result = output.get("result")
        if isinstance(result, dict):
            for candidate in result.get("artifacts", []):
                if isinstance(candidate, dict) and candidate.get("artifact_type"):
                    actual.add(str(candidate["artifact_type"]))
        if item.agent_id == "forge_builder" and output.get("run_id"):
            actual.update({"code", "change_log"})
        missing = expected.difference(actual)
        if missing:
            raise RuntimeError("Pflichtartefakte fehlen: " + ", ".join(sorted(missing)))


mission_scheduler_v2 = MissionSchedulerV2()
