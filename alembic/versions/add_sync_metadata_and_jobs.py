"""Add vendor sync metadata + sync_jobs table

Revision ID: add_sync_metadata_and_jobs
Revises: add_timezone_to_user
Create Date: 2026-01-13

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_sync_metadata_and_jobs"
down_revision = "add_timezone_to_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendor_integrations", sa.Column("vendor_user_id", sa.String(), nullable=True))
    op.add_column("vendor_integrations", sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "vendor_integrations",
        sa.Column("sync_status", sa.String(), nullable=False, server_default="idle"),
    )
    op.add_column("vendor_integrations", sa.Column("sync_job_id", sa.String(), nullable=True))

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("vendor", sa.String(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_sync_jobs_user_id", "sync_jobs", ["user_id"], unique=False)
    op.create_index("ix_sync_jobs_vendor", "sync_jobs", ["vendor"], unique=False)
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sync_jobs_status", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_vendor", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_user_id", table_name="sync_jobs")
    op.drop_table("sync_jobs")

    op.drop_column("vendor_integrations", "sync_job_id")
    op.drop_column("vendor_integrations", "sync_status")
    op.drop_column("vendor_integrations", "last_successful_sync_at")
    op.drop_column("vendor_integrations", "vendor_user_id")
