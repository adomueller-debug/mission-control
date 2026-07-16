"""Align persisted V2 payload column names with the ORM contracts.

Revision ID: 0012_align_v2_payloads
Revises: 0011_mission_v2_core
"""

from alembic import op


revision = "0012_align_v2_payloads"
down_revision = "0011_mission_v2_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("mission_agent_assignments") as batch:
        batch.alter_column("request_redacted", new_column_name="input_data")
        batch.alter_column("result_redacted", new_column_name="output_data")
    with op.batch_alter_table("mission_tool_calls") as batch:
        batch.alter_column("input_data", new_column_name="request_redacted")
        batch.alter_column("output_data", new_column_name="result_redacted")


def downgrade() -> None:
    with op.batch_alter_table("mission_tool_calls") as batch:
        batch.alter_column("request_redacted", new_column_name="input_data")
        batch.alter_column("result_redacted", new_column_name="output_data")
    with op.batch_alter_table("mission_agent_assignments") as batch:
        batch.alter_column("input_data", new_column_name="request_redacted")
        batch.alter_column("output_data", new_column_name="result_redacted")
