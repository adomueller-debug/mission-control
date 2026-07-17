from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    goal: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="general", index=True)
    status: Mapped[str] = mapped_column(String(50), default="idea", index=True)
    workspace: Mapped[str] = mapped_column(Text)
    owner_agent: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    budget_cents: Mapped[int] = mapped_column(Integer, default=0)
    revenue_target_cents: Mapped[int] = mapped_column(Integer, default=0)
    autopilot_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    delivery_error: Mapped[str] = mapped_column(Text, default="")
    drive_url: Mapped[str] = mapped_column(Text, default="")
    drive_project_folder_id: Mapped[str] = mapped_column(Text, default="")
    drive_crm_folder_id: Mapped[str] = mapped_column(Text, default="")
    drive_websites_folder_id: Mapped[str] = mapped_column(Text, default="")
    drive_results_folder_id: Mapped[str] = mapped_column(Text, default="")
    delivery_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ProjectTask(Base):
    __tablename__ = "project_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="backlog", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3, index=True)
    task_type: Mapped[str] = mapped_column(String(50), default="general", index=True)
    assigned_agent: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result: Mapped[str] = mapped_column(Text, default="")
    dependencies: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ProjectArtifact(Base):
    __tablename__ = "project_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "artifact_key", name="uq_project_artifact_run_key"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("project_tasks.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    artifact_key: Mapped[str] = mapped_column(String(500))
    name: Mapped[str] = mapped_column(String(300))
    artifact_type: Mapped[str] = mapped_column(String(50), index=True)
    storage_path: Mapped[str] = mapped_column(Text)
    entry_path: Mapped[str] = mapped_column(Text, default="")
    media_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sync_status: Mapped[str] = mapped_column(String(50), default="local", index=True)
    external_url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
