"""Add projects and project tasks.

Revision ID: 0004_projects
Revises: 0003_agent_team
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_projects"
down_revision = "0003_agent_team"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("goal", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("workspace", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_projects_name", "projects", ["name"])
        op.create_index("ix_projects_category", "projects", ["category"])
        op.create_index("ix_projects_status", "projects", ["status"])
    if "project_tasks" not in tables:
        op.create_table(
            "project_tasks",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("task_type", sa.String(length=50), nullable=False),
            sa.Column("assigned_agent", sa.String(length=50), nullable=True),
            sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        for column in ("project_id", "status", "priority", "task_type", "assigned_agent", "run_id"):
            op.create_index(f"ix_project_tasks_{column}", "project_tasks", [column])


def downgrade() -> None:
    op.drop_table("project_tasks")
    op.drop_table("projects")
