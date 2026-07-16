"""Add integration requirements and mission plans.

Revision ID: 0005_integrations_missions
Revises: 0004_projects
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_integrations_missions"
down_revision = "0004_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "integration_requirements" not in tables:
        op.create_table(
            "integration_requirements",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("integration_id", sa.String(length=80), nullable=False),
            sa.Column("purpose", sa.Text(), nullable=False),
            sa.Column("required", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_integration_requirements_project_id", "integration_requirements", ["project_id"])
        op.create_index("ix_integration_requirements_integration_id", "integration_requirements", ["integration_id"])
    if "mission_plans" not in tables:
        op.create_table(
            "mission_plans",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("goal", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("strategy", sa.Text(), nullable=False),
            sa.Column("assumptions", sa.Text(), nullable=False),
            sa.Column("risks", sa.Text(), nullable=False),
            sa.Column("success_metrics", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("planner_mode", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_mission_plans_project_id", "mission_plans", ["project_id"])
        op.create_index("ix_mission_plans_status", "mission_plans", ["status"])
    if "mission_plan_tasks" not in tables:
        op.create_table(
            "mission_plan_tasks",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("plan_id", sa.String(), sa.ForeignKey("mission_plans.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("agent_id", sa.String(length=50), nullable=False),
            sa.Column("task_type", sa.String(length=50), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("dependencies", sa.Text(), nullable=False),
            sa.Column("integration_ids", sa.Text(), nullable=False),
            sa.Column("acceptance_criteria", sa.Text(), nullable=False),
        )
        op.create_index("ix_mission_plan_tasks_plan_id", "mission_plan_tasks", ["plan_id"])
        op.create_index("ix_mission_plan_tasks_agent_id", "mission_plan_tasks", ["agent_id"])


def downgrade() -> None:
    op.drop_table("mission_plan_tasks")
    op.drop_table("mission_plans")
    op.drop_table("integration_requirements")
