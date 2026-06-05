"""job posting provider readiness

Revision ID: 20260606_0002
Revises: 20260606_0001
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260606_0002"
down_revision = "20260606_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add provider-ready listing fields, indexes, and uniqueness rules."""
    with op.batch_alter_table("job_postings") as batch_op:
        batch_op.add_column(sa.Column("country", sa.String(length=100), server_default="Germany", nullable=True))
        batch_op.add_column(sa.Column("city", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("federal_state", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("salary_period", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("salary_is_estimated", sa.Boolean(), server_default=sa.false(), nullable=True))
        batch_op.add_column(sa.Column("salary_confidence", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("employment_type", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("required_skills", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("source_posting_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("application_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("company_career_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("remote_status", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("role_type", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("occupation_group", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("experience_level", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("source_legal_basis", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("ingestion_batch_id", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("is_expired", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.create_unique_constraint("unique_job_source_posting", ["source", "source_posting_id"])

    op.create_index("idx_job_city", "job_postings", ["city"])
    op.create_index("idx_job_federal_state", "job_postings", ["federal_state"])
    op.create_index("idx_job_source_posting_id", "job_postings", ["source_posting_id"])
    op.create_index("idx_job_remote_status", "job_postings", ["remote_status"])
    op.create_index("idx_job_role_type", "job_postings", ["role_type"])
    op.create_index("idx_job_occupation_group", "job_postings", ["occupation_group"])
    op.create_index("idx_job_experience_level", "job_postings", ["experience_level"])
    op.create_index("idx_job_ingestion_batch_id", "job_postings", ["ingestion_batch_id"])
    op.create_index("idx_job_posted_at", "job_postings", ["posted_at"])
    op.create_index("idx_job_expires_at", "job_postings", ["expires_at"])
    op.create_index("idx_job_last_seen_at", "job_postings", ["last_seen_at"])
    op.create_index("idx_job_is_expired", "job_postings", ["is_expired"])


def downgrade() -> None:
    """Remove provider-ready listing fields."""
    op.drop_index("idx_job_is_expired", table_name="job_postings")
    op.drop_index("idx_job_last_seen_at", table_name="job_postings")
    op.drop_index("idx_job_expires_at", table_name="job_postings")
    op.drop_index("idx_job_posted_at", table_name="job_postings")
    op.drop_index("idx_job_ingestion_batch_id", table_name="job_postings")
    op.drop_index("idx_job_experience_level", table_name="job_postings")
    op.drop_index("idx_job_occupation_group", table_name="job_postings")
    op.drop_index("idx_job_role_type", table_name="job_postings")
    op.drop_index("idx_job_remote_status", table_name="job_postings")
    op.drop_index("idx_job_source_posting_id", table_name="job_postings")
    op.drop_index("idx_job_federal_state", table_name="job_postings")
    op.drop_index("idx_job_city", table_name="job_postings")

    with op.batch_alter_table("job_postings") as batch_op:
        batch_op.drop_constraint("unique_job_source_posting", type_="unique")
        batch_op.drop_column("is_expired")
        batch_op.drop_column("last_seen_at")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("posted_at")
        batch_op.drop_column("ingestion_batch_id")
        batch_op.drop_column("source_legal_basis")
        batch_op.drop_column("experience_level")
        batch_op.drop_column("occupation_group")
        batch_op.drop_column("role_type")
        batch_op.drop_column("remote_status")
        batch_op.drop_column("company_career_url")
        batch_op.drop_column("application_url")
        batch_op.drop_column("url")
        batch_op.drop_column("source_posting_id")
        batch_op.drop_column("required_skills")
        batch_op.drop_column("employment_type")
        batch_op.drop_column("salary_confidence")
        batch_op.drop_column("salary_is_estimated")
        batch_op.drop_column("salary_period")
        batch_op.drop_column("federal_state")
        batch_op.drop_column("city")
        batch_op.drop_column("country")
