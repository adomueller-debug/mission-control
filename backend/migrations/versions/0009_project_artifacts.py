"""Add persistent project deliverables and preview metadata."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0009_project_artifacts"
down_revision = "0008_run_workstreams"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The local app still calls metadata.create_all during startup. On an existing
    # installation that can materialize this table before Alembic advances.
    if inspect(op.get_bind()).has_table("project_artifacts"):
        return
    op.create_table(
        "project_artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("artifact_key", sa.String(length=500), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("entry_path", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "media_type",
            sa.String(length=100),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default="local"),
        sa.Column("external_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["project_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "artifact_key", name="uq_project_artifact_run_key"),
    )
    op.create_index("ix_project_artifacts_project_id", "project_artifacts", ["project_id"])
    op.create_index("ix_project_artifacts_task_id", "project_artifacts", ["task_id"])
    op.create_index("ix_project_artifacts_run_id", "project_artifacts", ["run_id"])
    op.create_index("ix_project_artifacts_artifact_type", "project_artifacts", ["artifact_type"])
    op.create_index("ix_project_artifacts_sync_status", "project_artifacts", ["sync_status"])


def downgrade() -> None:
    op.drop_table("project_artifacts")
