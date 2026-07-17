from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
import json
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from backend.app.models.mission_v2 import (
    AgentAssignment,
    Approval,
    AuditedToolCall,
    CostEntry,
    Mission,
    QualityGate,
    ResourceLease,
    WorkItem,
)
from backend.app.models.project import Project
from backend.app.services.agent_catalog import AGENTS


MISSION_STATUSES = {
    "draft",
    "planning",
    "ready",
    "running",
    "waiting_approval",
    "blocked",
    "validating",
    "completed",
    "failed",
    "cancelled",
}
WORK_ITEM_STATUSES = {
    "queued",
    "ready",
    "active",
    "review",
    "retrying",
    "completed",
    "skipped",
    "blocked",
}
TERMINAL_MISSION_STATUSES = {"completed", "failed", "cancelled"}
TERMINAL_WORK_ITEM_STATUSES = {"completed", "skipped"}


def utcnow() -> datetime:
    return datetime.now(UTC)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def validate_dag(items: list[dict[str, Any]]) -> list[str]:
    """Validate keys and dependencies and return a stable topological order."""
    keys = [str(item["key"]) for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError("Work-Item-Schlüssel müssen innerhalb einer Mission eindeutig sein")
    known = set(keys)
    incoming = {key: 0 for key in keys}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for item in items:
        key = str(item["key"])
        dependencies = list(item.get("dependencies", []))
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"Work Item '{key}' enthält doppelte Abhängigkeiten")
        for dependency in dependencies:
            if dependency not in known:
                raise ValueError(f"Unbekannte Abhängigkeit '{dependency}' in '{key}'")
            if dependency == key:
                raise ValueError(f"Work Item '{key}' darf nicht von sich selbst abhängen")
            incoming[key] += 1
            outgoing[dependency].append(key)
    ready = deque(key for key in keys if incoming[key] == 0)
    order: list[str] = []
    while ready:
        current = ready.popleft()
        order.append(current)
        for child in outgoing[current]:
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    if len(order) != len(keys):
        raise ValueError("Der Missionsplan enthält einen Abhängigkeitszyklus")
    return order


class MissionV2Service:
    def create_mission(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = payload.get("project_id")
        if project_id and db.get(Project, project_id) is None:
            raise KeyError("Projekt nicht gefunden")
        items = payload.pop("work_items", [])
        validate_dag(items)
        mission = Mission(
            project_id=project_id,
            goal=payload["goal"],
            status="ready" if items else "planning",
            risk_level=payload.get("risk_level", 0),
            autonomy_level=payload.get("autonomy_level", 1),
            budget_cents=payload.get("budget_cents", 0),
            deadline=payload.get("deadline"),
            success_criteria=_json(payload.get("success_criteria", [])),
            context=_json(payload.get("context", {})),
        )
        db.add(mission)
        db.flush()
        self._insert_work_items(db, mission.id, items)
        db.commit()
        return self.get_mission(db, mission.id) or {}

    def list_missions(self, db: Session, status: str | None = None) -> list[dict[str, Any]]:
        query = select(Mission).order_by(Mission.created_at.desc())
        if status:
            if status not in MISSION_STATUSES:
                raise ValueError("Ungültiger Missionsstatus")
            query = query.where(Mission.status == status)
        return [self._mission_summary(db, item) for item in db.scalars(query)]

    def get_mission(self, db: Session, mission_id: str) -> dict[str, Any] | None:
        mission = db.get(Mission, mission_id)
        if mission is None:
            return None
        work_items = list(
            db.scalars(
                select(WorkItem)
                .where(WorkItem.mission_id == mission_id)
                .order_by(WorkItem.priority, WorkItem.created_at)
            )
        )
        gates = list(db.scalars(select(QualityGate).where(QualityGate.mission_id == mission_id)))
        approvals = list(db.scalars(select(Approval).where(Approval.mission_id == mission_id)))
        result = self._mission_summary(db, mission)
        result.update(
            work_items=[self._work_item(item) for item in work_items],
            quality_gates=[self._gate(item) for item in gates],
            approvals=[self._approval(item) for item in approvals],
        )
        return result

    def replace_plan(
        self, db: Session, mission_id: str, items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        mission = db.get(Mission, mission_id)
        if mission is None:
            raise KeyError("Mission nicht gefunden")
        active = db.scalar(
            select(func.count()).select_from(WorkItem).where(
                WorkItem.mission_id == mission_id,
                WorkItem.status.in_(["active", "review"]),
            )
        )
        if active:
            raise ValueError("Ein aktiver Missionsplan kann nicht ersetzt werden")
        validate_dag(items)
        db.execute(delete(AgentAssignment).where(AgentAssignment.mission_id == mission_id))
        db.execute(delete(QualityGate).where(QualityGate.mission_id == mission_id))
        db.execute(delete(WorkItem).where(WorkItem.mission_id == mission_id))
        self._insert_work_items(db, mission_id, items)
        mission.status = "ready"
        mission.error = ""
        mission.cancel_requested = False
        db.commit()
        return self.get_mission(db, mission_id) or {}

    def cancel(self, db: Session, mission_id: str) -> dict[str, Any]:
        mission = self._require_mission(db, mission_id)
        if mission.status == "completed":
            raise ValueError("Eine abgeschlossene Mission kann nicht abgebrochen werden")
        mission.cancel_requested = True
        mission.status = "cancelled"
        db.execute(
            delete(ResourceLease).where(ResourceLease.mission_id == mission_id)
        )
        db.execute(
            update(WorkItem)
            .where(
                WorkItem.mission_id == mission_id,
                WorkItem.status.not_in(TERMINAL_WORK_ITEM_STATUSES),
            )
            .values(status="blocked")
        )
        db.commit()
        return self.get_mission(db, mission_id) or {}

    def resume(self, db: Session, mission_id: str) -> dict[str, Any]:
        mission = self._require_mission(db, mission_id)
        if mission.status not in {"cancelled", "blocked", "failed"}:
            raise ValueError("Nur abgebrochene, blockierte oder fehlgeschlagene Missionen können fortgesetzt werden")
        mission.cancel_requested = False
        mission.error = ""
        mission.status = "ready"
        db.execute(
            update(WorkItem)
            .where(WorkItem.mission_id == mission_id, WorkItem.status == "blocked")
            .values(status="queued", skip_reason="")
        )
        self.refresh_ready_items(db, mission_id)
        db.commit()
        return self.get_mission(db, mission_id) or {}

    def set_work_item_status(
        self,
        db: Session,
        work_item_id: str,
        status: str,
        *,
        skip_reason: str = "",
    ) -> dict[str, Any]:
        if status not in WORK_ITEM_STATUSES:
            raise ValueError("Ungültiger Work-Item-Status")
        item = db.get(WorkItem, work_item_id)
        if item is None:
            raise KeyError("Work Item nicht gefunden")
        if status == "skipped" and not skip_reason.strip():
            raise ValueError("Übersprungene Work Items benötigen einen sichtbaren Grund")
        item.status = status
        item.skip_reason = skip_reason.strip() if status == "skipped" else ""
        if status in {"completed", "skipped"}:
            self.refresh_ready_items(db, item.mission_id)
        db.commit()
        return self._work_item(item)

    def refresh_ready_items(self, db: Session, mission_id: str) -> list[str]:
        items = list(db.scalars(select(WorkItem).where(WorkItem.mission_id == mission_id)))
        completed = {item.key for item in items if item.status in TERMINAL_WORK_ITEM_STATUSES}
        newly_ready: list[str] = []
        for item in items:
            if item.status not in {"queued", "retrying"}:
                continue
            dependencies = set(_load(item.dependencies, []))
            if dependencies.issubset(completed):
                item.status = "ready"
                newly_ready.append(item.id)
        return newly_ready

    def create_approval(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        mission = self._require_mission(db, payload["mission_id"])
        if payload.get("risk_level", 2) < 2:
            raise ValueError("Freigaben sind für Außenwirkungen der Risikostufen 2 und 3 vorgesehen")
        approval = Approval(
            mission_id=mission.id,
            work_item_id=payload.get("work_item_id"),
            tool_call_id=payload.get("tool_call_id"),
            action_type=payload["action_type"],
            summary=payload.get("summary", ""),
            target=payload.get("target", ""),
            risk_level=payload.get("risk_level", 2),
            payload_preview=_json(payload.get("payload_preview", payload.get("preview", {}))),
        )
        db.add(approval)
        mission.status = "waiting_approval"
        db.commit()
        db.refresh(approval)
        return self._approval(approval)

    def list_approvals(
        self, db: Session, status: str | None = "pending"
    ) -> list[dict[str, Any]]:
        query = select(Approval).order_by(Approval.created_at.desc())
        if status:
            query = query.where(Approval.status == status)
        return [self._approval(item) for item in db.scalars(query)]

    def decide_approval(
        self, db: Session, approval_id: str, approved: bool, note: str = ""
    ) -> dict[str, Any]:
        approval = db.get(Approval, approval_id)
        if approval is None:
            raise KeyError("Freigabe nicht gefunden")
        if approval.status != "pending":
            raise ValueError("Diese Freigabe wurde bereits entschieden")
        approval.status = "approved" if approved else "rejected"
        approval.decision_note = note
        approval.decided_at = utcnow()
        mission = self._require_mission(db, approval.mission_id)
        pending = db.scalar(
            select(func.count()).select_from(Approval).where(
                Approval.mission_id == approval.mission_id,
                Approval.status == "pending",
                Approval.id != approval.id,
            )
        )
        if not pending:
            mission.status = "ready" if approved else "blocked"
        db.commit()
        return self._approval(approval)

    def add_quality_gate(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_mission(db, payload["mission_id"])
        gate = QualityGate(
            mission_id=payload["mission_id"],
            work_item_id=payload.get("work_item_id"),
            name=payload["name"],
            gate_type=payload.get("gate_type", "acceptance"),
            required=payload.get("required", True),
        )
        db.add(gate)
        db.commit()
        db.refresh(gate)
        return self._gate(gate)

    def record_tool_call(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        existing = db.scalar(
            select(AuditedToolCall).where(
                AuditedToolCall.mission_id == payload["mission_id"],
                AuditedToolCall.tool_name == payload["tool_name"],
                AuditedToolCall.idempotency_key == payload["idempotency_key"],
            )
        )
        if existing:
            return self._tool_call(existing)
        call = AuditedToolCall(
            mission_id=payload["mission_id"],
            work_item_id=payload.get("work_item_id"),
            assignment_id=payload.get("assignment_id"),
            agent_id=payload["agent_id"],
            tool_name=payload["tool_name"],
            risk_level=payload.get("risk_level", 0),
            idempotency_key=payload["idempotency_key"],
            request_redacted=_json(payload.get("request_redacted", {})),
            timeout_seconds=payload.get("timeout_seconds", 60),
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return self._tool_call(call)

    def add_cost(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        entry = CostEntry(**payload)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return self._cost(entry)

    def budget_summary(self, db: Session, mission_id: str | None = None) -> dict[str, Any]:
        query = select(
            func.coalesce(func.sum(CostEntry.estimated_cents), 0),
            func.coalesce(func.sum(CostEntry.actual_cents), 0),
        )
        if mission_id:
            self._require_mission(db, mission_id)
            query = query.where(CostEntry.mission_id == mission_id)
        estimated, actual = db.execute(query).one()
        monthly_limit = 2_000
        return {
            "mission_id": mission_id,
            "currency": "EUR",
            "monthly_limit_cents": monthly_limit,
            "estimated_cents": int(estimated),
            "actual_cents": int(actual),
            "remaining_cents": max(0, monthly_limit - int(actual)),
        }

    def agent_statuses(self, db: Session) -> list[dict[str, Any]]:
        active = list(
            db.scalars(
                select(AgentAssignment).where(
                    AgentAssignment.status.in_(["active", "review", "retrying"])
                )
            )
        )
        by_agent: dict[str, list[AgentAssignment]] = defaultdict(list)
        for assignment in active:
            by_agent[assignment.agent_id].append(assignment)
        return [
            {
                **agent,
                "status": "active" if by_agent[agent["id"]] else "offline",
                "active_assignments": [
                    self._assignment(item) for item in by_agent[agent["id"]]
                ],
            }
            for agent in AGENTS
        ]

    def acquire_lease(
        self,
        db: Session,
        *,
        resource_key: str,
        mission_id: str,
        work_item_id: str,
        owner_id: str,
        assignment_id: str | None = None,
        ttl_seconds: int = 60,
    ) -> bool:
        now = utcnow()
        lease = db.get(ResourceLease, resource_key)
        if lease and self._is_future(lease.expires_at, now) and lease.owner_id != owner_id:
            return False
        if lease is None:
            lease = ResourceLease(
                resource_key=resource_key,
                mission_id=mission_id,
                work_item_id=work_item_id,
                assignment_id=assignment_id,
                owner_id=owner_id,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            db.add(lease)
        else:
            lease.mission_id = mission_id
            lease.work_item_id = work_item_id
            lease.assignment_id = assignment_id
            lease.owner_id = owner_id
            lease.heartbeat_at = now
            lease.expires_at = now + timedelta(seconds=ttl_seconds)
        db.commit()
        return True

    def heartbeat_lease(
        self, db: Session, resource_key: str, owner_id: str, ttl_seconds: int = 60
    ) -> bool:
        lease = db.get(ResourceLease, resource_key)
        if lease is None or lease.owner_id != owner_id:
            return False
        now = utcnow()
        lease.heartbeat_at = now
        lease.expires_at = now + timedelta(seconds=ttl_seconds)
        if lease.assignment_id:
            assignment = db.get(AgentAssignment, lease.assignment_id)
            if assignment:
                assignment.heartbeat_at = now
        db.commit()
        return True

    def release_lease(self, db: Session, resource_key: str, owner_id: str) -> bool:
        lease = db.get(ResourceLease, resource_key)
        if lease is None or lease.owner_id != owner_id:
            return False
        db.delete(lease)
        db.commit()
        return True

    def recover_expired_leases(self, db: Session) -> list[str]:
        now = utcnow()
        leases = list(db.scalars(select(ResourceLease).where(ResourceLease.expires_at <= now)))
        recovered: list[str] = []
        for lease in leases:
            item = db.get(WorkItem, lease.work_item_id)
            if item and item.status == "active":
                item.attempts += 1
                item.status = "retrying" if item.attempts < item.max_attempts else "blocked"
                recovered.append(item.id)
            if lease.assignment_id:
                assignment = db.get(AgentAssignment, lease.assignment_id)
                if assignment and assignment.status == "active":
                    assignment.status = "queued" if item and item.status == "retrying" else "blocked"
                    assignment.worker_id = ""
            db.delete(lease)
        db.commit()
        return recovered

    @staticmethod
    def _is_future(value: datetime, now: datetime) -> bool:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value > now

    def _insert_work_items(self, db: Session, mission_id: str, items: list[dict[str, Any]]) -> None:
        for data in items:
            dependencies = list(data.get("dependencies", []))
            item = WorkItem(
                mission_id=mission_id,
                key=data["key"],
                title=data["title"],
                description=data.get("description", ""),
                agent_id=data["agent_id"],
                status="ready" if not dependencies else "queued",
                priority=data.get("priority", 3),
                risk_level=data.get("risk_level", 0),
                dependencies=_json(dependencies),
                required_tools=_json(data.get("required_tools", [])),
                resource_keys=_json(data.get("resource_keys", [])),
                expected_artifacts=_json(data.get("expected_artifacts", [])),
                acceptance_criteria=_json(data.get("acceptance_criteria", [])),
                max_attempts=data.get("max_attempts", 3),
            )
            db.add(item)
            db.flush()
            db.add(
                AgentAssignment(
                    mission_id=mission_id,
                    work_item_id=item.id,
                    agent_id=item.agent_id,
                    input_data=_json({"work_item_key": item.key}),
                )
            )

    def _mission_summary(self, db: Session, mission: Mission) -> dict[str, Any]:
        items = list(db.scalars(select(WorkItem).where(WorkItem.mission_id == mission.id)))
        gates = list(
            db.scalars(
                select(QualityGate).where(
                    QualityGate.mission_id == mission.id, QualityGate.required.is_(True)
                )
            )
        )
        completed = sum(item.status in TERMINAL_WORK_ITEM_STATUSES for item in items)
        passed = sum(gate.status == "passed" for gate in gates)
        total = len(items) + len(gates)
        return {
            "id": mission.id,
            "project_id": mission.project_id,
            "goal": mission.goal,
            "status": mission.status,
            "risk_level": mission.risk_level,
            "autonomy_level": mission.autonomy_level,
            "budget_cents": mission.budget_cents,
            "deadline": mission.deadline,
            "success_criteria": _load(mission.success_criteria, []),
            "context": _load(mission.context, {}),
            "error": mission.error,
            "cancel_requested": mission.cancel_requested,
            "progress": {
                "percent": round(((completed + passed) / total) * 100) if total else 0,
                "completed_work_items": completed,
                "total_work_items": len(items),
                "passed_required_gates": passed,
                "total_required_gates": len(gates),
            },
            "created_at": mission.created_at,
            "updated_at": mission.updated_at,
        }

    @staticmethod
    def _work_item(item: WorkItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "mission_id": item.mission_id,
            "key": item.key,
            "title": item.title,
            "description": item.description,
            "agent_id": item.agent_id,
            "status": item.status,
            "priority": item.priority,
            "risk_level": item.risk_level,
            "dependencies": _load(item.dependencies, []),
            "required_tools": _load(item.required_tools, []),
            "resource_keys": _load(item.resource_keys, []),
            "expected_artifacts": _load(item.expected_artifacts, []),
            "acceptance_criteria": _load(item.acceptance_criteria, []),
            "skip_reason": item.skip_reason,
            "attempts": item.attempts,
            "max_attempts": item.max_attempts,
        }

    @staticmethod
    def _assignment(item: AgentAssignment) -> dict[str, Any]:
        return {
            "id": item.id,
            "mission_id": item.mission_id,
            "work_item_id": item.work_item_id,
            "agent_id": item.agent_id,
            "status": item.status,
            "input": _load(item.input_data, {}),
            "output": _load(item.output_data, {}),
            "error": item.error,
            "worker_id": item.worker_id,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "heartbeat_at": item.heartbeat_at,
        }

    @staticmethod
    def _gate(item: QualityGate) -> dict[str, Any]:
        return {
            "id": item.id,
            "mission_id": item.mission_id,
            "work_item_id": item.work_item_id,
            "name": item.name,
            "gate_type": item.gate_type,
            "required": item.required,
            "status": item.status,
            "details": _load(item.details, {}),
            "checked_at": item.checked_at,
        }

    @staticmethod
    def _approval(item: Approval) -> dict[str, Any]:
        return {
            "id": item.id,
            "mission_id": item.mission_id,
            "work_item_id": item.work_item_id,
            "tool_call_id": item.tool_call_id,
            "action_type": item.action_type,
            "summary": item.summary,
            "target": item.target,
            "risk_level": item.risk_level,
            "payload_preview": _load(item.payload_preview, {}),
            "status": item.status,
            "decision_note": item.decision_note,
            "decided_at": item.decided_at,
            "created_at": item.created_at,
        }

    @staticmethod
    def _tool_call(item: AuditedToolCall) -> dict[str, Any]:
        return {
            "id": item.id,
            "mission_id": item.mission_id,
            "work_item_id": item.work_item_id,
            "assignment_id": item.assignment_id,
            "agent_id": item.agent_id,
            "tool_name": item.tool_name,
            "risk_level": item.risk_level,
            "idempotency_key": item.idempotency_key,
            "status": item.status,
            "request_redacted": _load(item.request_redacted, {}),
            "result_redacted": _load(item.result_redacted, {}),
        }

    @staticmethod
    def _cost(item: CostEntry) -> dict[str, Any]:
        return {
            "id": item.id,
            "mission_id": item.mission_id,
            "provider": item.provider,
            "model": item.model,
            "kind": item.kind,
            "estimated_cents": item.estimated_cents,
            "actual_cents": item.actual_cents,
            "currency": item.currency,
            "created_at": item.created_at,
        }

    @staticmethod
    def _require_mission(db: Session, mission_id: str) -> Mission:
        mission = db.get(Mission, mission_id)
        if mission is None:
            raise KeyError("Mission nicht gefunden")
        return mission


mission_v2_service = MissionV2Service()
