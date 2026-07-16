"""Add persistent workstreams for project and internal work."""

from alembic import op
import sqlalchemy as sa


revision = "0008_run_workstreams"
down_revision = "0007_project_autopilot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch:
        batch.add_column(
            sa.Column(
                "workstream",
                sa.String(length=50),
                nullable=False,
                server_default="standalone",
            )
        )
        batch.create_index("ix_agent_runs_workstream", ["workstream"])
    op.execute(
        "UPDATE agent_runs SET workstream = 'internal' "
        "WHERE run_kind = 'coding' AND lower(task) LIKE '%mission control%'"
    )
    op.execute(
        "UPDATE agent_runs SET workstream = 'project' "
        "WHERE id IN (SELECT run_id FROM project_tasks WHERE run_id IS NOT NULL)"
    )


def downgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_index("ix_agent_runs_workstream")
        batch.drop_column("workstream")
