"""Add specialized runs and project management controls."""

from alembic import op
import sqlalchemy as sa


revision = "0006_autonomy_project_controls"
down_revision = "0005_integrations_missions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch:
        batch.add_column(sa.Column("run_kind", sa.String(length=50), nullable=False, server_default="coding"))
        batch.create_index("ix_agent_runs_run_kind", ["run_kind"])

    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("owner_agent", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("budget_cents", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("revenue_target_cents", sa.Integer(), nullable=False, server_default="0"))
        batch.create_index("ix_projects_owner_agent", ["owner_agent"])

    with op.batch_alter_table("project_tasks") as batch:
        batch.add_column(sa.Column("result", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("project_tasks") as batch:
        batch.drop_column("result")
    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_owner_agent")
        batch.drop_column("revenue_target_cents")
        batch.drop_column("budget_cents")
        batch.drop_column("deadline")
        batch.drop_column("owner_agent")
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_index("ix_agent_runs_run_kind")
        batch.drop_column("run_kind")
