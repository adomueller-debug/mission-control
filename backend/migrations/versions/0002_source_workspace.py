"""Track source workspace separately from isolated worktree.

Revision ID: 0002_source_workspace
Revises: 0001_agent_run_platform
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_source_workspace"
down_revision = "0001_agent_run_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("agent_runs")
    }
    if "source_workspace" not in columns:
        with op.batch_alter_table("agent_runs") as batch:
            batch.add_column(sa.Column("source_workspace", sa.Text(), nullable=True))
        op.execute("UPDATE agent_runs SET source_workspace = workspace")


def downgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_column("source_workspace")
