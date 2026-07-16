"""Add persistent project autopilot state and task dependencies."""

from alembic import op
import sqlalchemy as sa


revision = "0007_project_autopilot"
down_revision = "0006_autonomy_project_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(
            sa.Column(
                "autopilot_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.create_index("ix_projects_autopilot_enabled", ["autopilot_enabled"])

    with op.batch_alter_table("project_tasks") as batch:
        batch.add_column(
            sa.Column("dependencies", sa.Text(), nullable=False, server_default="[]")
        )


def downgrade() -> None:
    with op.batch_alter_table("project_tasks") as batch:
        batch.drop_column("dependencies")
    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_autopilot_enabled")
        batch.drop_column("autopilot_enabled")
