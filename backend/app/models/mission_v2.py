from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Mission(Base):
    __tablename__ = "missions_v2"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="planning", index=True)
    risk_level: Mapped[int] = mapped_column(Integer, default=0)
    autonomy_level: Mapped[int] = mapped_column(Integer, default=1)
    budget_cents: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success_criteria: Mapped[str] = mapped_column(Text, default="[]")
    context: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class WorkItem(Base):
    __tablename__ = "mission_work_items"
    __table_args__ = (
        UniqueConstraint("mission_id", "key", name="uq_mission_work_item_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions_v2.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    agent_id: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    risk_level: Mapped[int] = mapped_column(Integer, default=0)
    dependencies: Mapped[str] = mapped_column(Text, default="[]")
    required_tools: Mapped[str] = mapped_column(Text, default="[]")
    resource_keys: Mapped[str] = mapped_column(Text, default="[]")
    expected_artifacts: Mapped[str] = mapped_column(Text, default="[]")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="[]")
    skip_reason: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AgentAssignment(Base):
    __tablename__ = "mission_agent_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions_v2.id", ondelete="CASCADE"), index=True
    )
    work_item_id: Mapped[str] = mapped_column(
        ForeignKey("mission_work_items.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    input_data: Mapped[str] = mapped_column(Text, default="{}")
    output_data: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    worker_id: Mapped[str] = mapped_column(String(100), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditedToolCall(Base):
    __tablename__ = "mission_tool_calls"
    __table_args__ = (
        UniqueConstraint(
            "mission_id",
            "tool_name",
            "idempotency_key",
            name="uq_mission_tool_call_idempotency",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions_v2.id", ondelete="CASCADE"), index=True
    )
    work_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_work_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_agent_assignments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(50), index=True)
    tool_name: Mapped[str] = mapped_column(String(100), index=True)
    risk_level: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    request_redacted: Mapped[str] = mapped_column(Text, default="{}")
    result_redacted: Mapped[str] = mapped_column(Text, default="{}")
    error_class: Mapped[str] = mapped_column(String(100), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QualityGate(Base):
    __tablename__ = "mission_quality_gates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions_v2.id", ondelete="CASCADE"), index=True
    )
    work_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_work_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    gate_type: Mapped[str] = mapped_column(String(50), default="acceptance")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    details: Mapped[str] = mapped_column(Text, default="{}")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Approval(Base):
    __tablename__ = "mission_approvals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions_v2.id", ondelete="CASCADE"), index=True
    )
    work_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_work_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_tool_calls.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(80), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    target: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[int] = mapped_column(Integer, default=2)
    payload_preview: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    decision_note: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CostEntry(Base):
    __tablename__ = "mission_cost_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions_v2.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_agent_assignments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_tool_calls.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(80), default="local", index=True)
    model: Mapped[str] = mapped_column(String(100), default="")
    kind: Mapped[str] = mapped_column(String(50), default="inference")
    estimated_cents: Mapped[int] = mapped_column(Integer, default=0)
    actual_cents: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ResourceLease(Base):
    __tablename__ = "mission_resource_leases"

    resource_key: Mapped[str] = mapped_column(String(300), primary_key=True)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions_v2.id", ondelete="CASCADE"), index=True
    )
    work_item_id: Mapped[str] = mapped_column(
        ForeignKey("mission_work_items.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_agent_assignments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    owner_id: Mapped[str] = mapped_column(String(100), index=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
