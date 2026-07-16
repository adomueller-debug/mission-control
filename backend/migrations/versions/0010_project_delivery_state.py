"""Add project delivery and Drive hierarchy state."""

from alembic import op
import sqlalchemy as sa


revision = "0010_project_delivery_state"
down_revision = "0009_project_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(
            sa.Column("delivery_status", sa.String(length=50), nullable=False, server_default="pending")
        )
        batch.add_column(sa.Column("delivery_error", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("drive_url", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("drive_project_folder_id", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("drive_crm_folder_id", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("drive_websites_folder_id", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("drive_results_folder_id", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("delivery_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_projects_delivery_status", ["delivery_status"])


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_delivery_status")
        batch.drop_column("delivery_synced_at")
        batch.drop_column("drive_results_folder_id")
        batch.drop_column("drive_websites_folder_id")
        batch.drop_column("drive_crm_folder_id")
        batch.drop_column("drive_project_folder_id")
        batch.drop_column("drive_url")
        batch.drop_column("delivery_error")
        batch.drop_column("delivery_status")
