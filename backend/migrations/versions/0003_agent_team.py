"""Add persistent agent memory and delegations.

Revision ID: 0003_agent_team
Revises: 0002_source_workspace
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_agent_team"
down_revision = "0002_source_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "agent_memory_entries" not in tables:
        op.create_table(
            "agent_memory_entries",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_agent_memory_entries_agent_id", "agent_memory_entries", ["agent_id"])
        op.create_index("ix_agent_memory_entries_run_id", "agent_memory_entries", ["run_id"])
    if "agent_delegations" not in tables:
        op.create_table(
            "agent_delegations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("from_agent", sa.String(), nullable=False),
            sa.Column("to_agent", sa.String(), nullable=False),
            sa.Column("task", sa.Text(), nullable=False),
            sa.Column("context", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_agent_delegations_run_id", "agent_delegations", ["run_id"])
        op.create_index("ix_agent_delegations_from_agent", "agent_delegations", ["from_agent"])
        op.create_index("ix_agent_delegations_to_agent", "agent_delegations", ["to_agent"])
        op.create_index("ix_agent_delegations_status", "agent_delegations", ["status"])


def downgrade() -> None:
    op.drop_table("agent_delegations")
    op.drop_table("agent_memory_entries")
