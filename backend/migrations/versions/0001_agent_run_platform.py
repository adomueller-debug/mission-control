"""Add persistent autonomous run platform.

Revision ID: 0001_agent_run_platform
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_agent_run_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "agent_runs" not in tables:
        op.create_table(
            "agent_runs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("task", sa.Text(), nullable=False),
            sa.Column("workspace", sa.Text(), nullable=False),
            sa.Column("source_workspace", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("current_step", sa.String(), nullable=True),
            sa.Column("plan", sa.Text(), nullable=False),
            sa.Column("result", sa.Text(), nullable=False),
            sa.Column("error", sa.Text(), nullable=False),
            sa.Column("branch", sa.String(), nullable=False),
            sa.Column("pr_url", sa.Text(), nullable=False),
            sa.Column("cancel_requested", sa.Boolean(), nullable=False),
            sa.Column("publish", sa.Boolean(), nullable=False),
            sa.Column("tool_calls", sa.Integer(), nullable=False),
            sa.Column("repair_attempts", sa.Integer(), nullable=False),
            sa.Column("max_tool_calls", sa.Integer(), nullable=False),
            sa.Column("max_repair_attempts", sa.Integer(), nullable=False),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    if "run_events" not in tables:
        op.create_table(
            "run_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "run_id",
                sa.String(),
                sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_run_events_run_id", "run_events", ["run_id"])
        op.create_index("ix_run_events_event_type", "run_events", ["event_type"])
    if "run_checkpoints" not in tables:
        op.create_table(
            "run_checkpoints",
            sa.Column(
                "run_id",
                sa.String(),
                sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("state", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("run_checkpoints")
    op.drop_index("ix_run_events_event_type", table_name="run_events")
    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_table("agent_runs")
