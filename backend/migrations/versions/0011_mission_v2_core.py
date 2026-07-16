"""Add the persistent Mission Control V2 execution core."""

from alembic import op
import sqlalchemy as sa


revision = "0011_mission_v2_core"
down_revision = "0010_project_delivery_state"
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.String(), primary_key=True)


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "missions_v2",
        _id(),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("risk_level", sa.Integer(), nullable=False),
        sa.Column("autonomy_level", sa.Integer(), nullable=False),
        sa.Column("budget_cents", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success_criteria", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_missions_v2_project_id", "missions_v2", ["project_id"])
    op.create_index("ix_missions_v2_status", "missions_v2", ["status"])

    op.create_table(
        "mission_work_items",
        _id(),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.Integer(), nullable=False),
        sa.Column("dependencies", sa.Text(), nullable=False),
        sa.Column("required_tools", sa.Text(), nullable=False),
        sa.Column("resource_keys", sa.Text(), nullable=False),
        sa.Column("expected_artifacts", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", sa.Text(), nullable=False),
        sa.Column("skip_reason", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("mission_id", "key", name="uq_mission_work_item_key"),
    )
    for column in ("mission_id", "agent_id", "status"):
        op.create_index(f"ix_mission_work_items_{column}", "mission_work_items", [column])

    op.create_table(
        "mission_agent_assignments",
        _id(),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_item_id", sa.String(), sa.ForeignKey("mission_work_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("request_redacted", sa.Text(), nullable=False),
        sa.Column("result_redacted", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("mission_id", "work_item_id", "agent_id", "status"):
        op.create_index(f"ix_mission_agent_assignments_{column}", "mission_agent_assignments", [column])

    op.create_table(
        "mission_tool_calls",
        _id(),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_item_id", sa.String(), sa.ForeignKey("mission_work_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assignment_id", sa.String(), sa.ForeignKey("mission_agent_assignments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", sa.String(length=50), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("output_data", sa.Text(), nullable=False),
        sa.Column("error_class", sa.String(length=100), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("mission_id", "tool_name", "idempotency_key", name="uq_mission_tool_call_idempotency"),
    )
    for column in ("mission_id", "work_item_id", "assignment_id", "agent_id", "tool_name", "status"):
        op.create_index(f"ix_mission_tool_calls_{column}", "mission_tool_calls", [column])

    op.create_table(
        "mission_quality_gates",
        _id(),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_item_id", sa.String(), sa.ForeignKey("mission_work_items.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("gate_type", sa.String(length=50), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("mission_id", "work_item_id", "status"):
        op.create_index(f"ix_mission_quality_gates_{column}", "mission_quality_gates", [column])

    op.create_table(
        "mission_approvals",
        _id(),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_item_id", sa.String(), sa.ForeignKey("mission_work_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tool_call_id", sa.String(), sa.ForeignKey("mission_tool_calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.Integer(), nullable=False),
        sa.Column("payload_preview", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("mission_id", "work_item_id", "tool_call_id", "action_type", "status"):
        op.create_index(f"ix_mission_approvals_{column}", "mission_approvals", [column])

    op.create_table(
        "mission_cost_entries",
        _id(),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.String(), sa.ForeignKey("mission_agent_assignments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tool_call_id", sa.String(), sa.ForeignKey("mission_tool_calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("estimated_cents", sa.Integer(), nullable=False),
        sa.Column("actual_cents", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("mission_id", "assignment_id", "tool_call_id", "provider", "created_at"):
        op.create_index(f"ix_mission_cost_entries_{column}", "mission_cost_entries", [column])

    op.create_table(
        "mission_resource_leases",
        sa.Column("resource_key", sa.String(length=300), primary_key=True),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_item_id", sa.String(), sa.ForeignKey("mission_work_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.String(), sa.ForeignKey("mission_agent_assignments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("owner_id", sa.String(length=100), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("mission_id", "work_item_id", "assignment_id", "owner_id", "expires_at"):
        op.create_index(f"ix_mission_resource_leases_{column}", "mission_resource_leases", [column])


def downgrade() -> None:
    for table in (
        "mission_resource_leases",
        "mission_cost_entries",
        "mission_approvals",
        "mission_quality_gates",
        "mission_tool_calls",
        "mission_agent_assignments",
        "mission_work_items",
        "missions_v2",
    ):
        op.drop_table(table)
