"""ingestion batch audit

Revision ID: 20260606_0003
Revises: 20260606_0002
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260606_0003"
down_revision = "20260606_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ingestion batch audit table."""
    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("saved_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("expired_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_ingestion_batch_status", "ingestion_batches", ["status"])
    op.create_index("idx_ingestion_batch_started_at", "ingestion_batches", ["started_at"])


def downgrade() -> None:
    """Drop ingestion batch audit table."""
    op.drop_index("idx_ingestion_batch_started_at", table_name="ingestion_batches")
    op.drop_index("idx_ingestion_batch_status", table_name="ingestion_batches")
    op.drop_table("ingestion_batches")
