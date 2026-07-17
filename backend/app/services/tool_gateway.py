from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from time import monotonic
from typing import Any, Callable

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.mission_v2 import Approval, AuditedToolCall, Mission
from backend.app.services.action_contracts import ExternalActionRequest
from backend.app.services.risk_policy import RiskLevel, risk_for
from backend.app.services.run_service import redact


class ToolGatewayError(RuntimeError):
    """Base class for failures that are safe to expose to the mission engine."""


class ToolPermissionError(ToolGatewayError):
    pass


class ToolTimeoutError(ToolGatewayError):
    pass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    input_schema: type[BaseModel]
    handler: Callable[[BaseModel], dict[str, Any]]
    permitted_agents: frozenset[str]
    timeout_seconds: int = 60
    max_attempts: int = 2


class ToolGateway:
    """Typed, permissioned and persistent gateway for every V2 tool call."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool ist bereits registriert: {definition.name}")
        self._tools[definition.name] = definition

    def registered_for(self, agent_id: str) -> list[str]:
        return sorted(
            item.name for item in self._tools.values() if agent_id in item.permitted_agents
        )

    def execute(
        self,
        db: Session,
        action: ExternalActionRequest,
        *,
        assignment_id: str | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        definition = self._tools.get(action.action_type)
        if definition is None:
            raise ToolGatewayError(f"Nicht unterstütztes Tool: {action.action_type}")
        if action.agent_id not in definition.permitted_agents:
            raise ToolPermissionError(
                f"Agent {action.agent_id} darf {action.action_type} nicht ausführen"
            )

        existing = db.scalar(
            select(AuditedToolCall).where(
                AuditedToolCall.mission_id == action.mission_id,
                AuditedToolCall.tool_name == action.action_type,
                AuditedToolCall.idempotency_key == action.idempotency_key,
            )
        )
        if existing and existing.status in {"completed", "waiting_approval"}:
            return self._result(existing, reused=True)

        try:
            validated = definition.input_schema.model_validate(action.payload)
        except ValidationError as exc:
            raise ToolGatewayError(f"Ungültige Tool-Eingabe: {exc}") from exc

        risk_level = max(int(action.risk_level or 0), int(risk_for(action.action_type)))
        call = existing or AuditedToolCall(
            mission_id=action.mission_id,
            work_item_id=action.work_item_id,
            assignment_id=assignment_id,
            agent_id=action.agent_id,
            tool_name=action.action_type,
            risk_level=risk_level,
            idempotency_key=action.idempotency_key,
            timeout_seconds=definition.timeout_seconds,
        )
        call.request_redacted = json.dumps(redact(action.payload), ensure_ascii=False, default=str)
        db.add(call)
        db.flush()

        if risk_level >= int(RiskLevel.APPROVAL) and not approved:
            call.status = "waiting_approval"
            approval = db.scalar(
                select(Approval).where(Approval.tool_call_id == call.id)
            )
            if approval is None:
                approval = Approval(
                    mission_id=action.mission_id,
                    work_item_id=action.work_item_id,
                    tool_call_id=call.id,
                    action_type=action.action_type,
                    summary=action.summary,
                    target=action.target,
                    risk_level=risk_level,
                    payload_preview=json.dumps(redact(action.payload), ensure_ascii=False, default=str),
                )
                db.add(approval)
            mission = db.get(Mission, action.mission_id)
            if mission:
                mission.status = "waiting_approval"
            db.commit()
            return self._result(call, approval_id=approval.id)

        call.status = "active"
        db.commit()
        started = monotonic()
        error: Exception | None = None
        for attempt in range(definition.max_attempts):
            try:
                pool = ThreadPoolExecutor(max_workers=1)
                try:
                    future = pool.submit(definition.handler, validated)
                    result = future.result(timeout=definition.timeout_seconds)
                finally:
                    pool.shutdown(wait=False, cancel_futures=True)
                call.status = "completed"
                call.result_redacted = json.dumps(redact(result), ensure_ascii=False, default=str)
                call.duration_ms = round((monotonic() - started) * 1000)
                call.completed_at = datetime.now(UTC)
                db.commit()
                return self._result(call)
            except FutureTimeout:
                error = ToolTimeoutError(
                    f"Tool {definition.name} überschritt {definition.timeout_seconds} Sekunden"
                )
            except Exception as exc:  # Handler errors are normalized and audited.
                error = exc
            if attempt + 1 >= definition.max_attempts:
                break

        call.status = "failed"
        call.error_class = type(error).__name__ if error else "ToolGatewayError"
        call.error = str(error or "Tool-Ausführung fehlgeschlagen")
        call.duration_ms = round((monotonic() - started) * 1000)
        db.commit()
        if isinstance(error, ToolGatewayError):
            raise error
        raise ToolGatewayError(call.error) from error

    @staticmethod
    def _result(
        call: AuditedToolCall,
        *,
        reused: bool = False,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "tool_call_id": call.id,
            "status": call.status,
            "result": json.loads(call.result_redacted or "{}"),
            "approval_id": approval_id,
            "reused": reused,
        }


tool_gateway = ToolGateway()
