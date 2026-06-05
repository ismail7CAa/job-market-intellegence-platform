"""initial core schema

Revision ID: 20260606_0001
Revises:
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260606_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the core analytics and job-posting tables."""
    op.create_table(
        "job_postings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("posted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_job_title", "job_postings", ["title"])
    op.create_index("idx_job_company", "job_postings", ["company"])
    op.create_index("idx_job_location", "job_postings", ["location"])
    op.create_index("idx_job_source", "job_postings", ["source"])
    op.create_index("idx_job_posted_date", "job_postings", ["posted_date"])

    op.create_table(
        "skills",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("name", name="uq_skills_name"),
    )
    op.create_index("idx_skill_name", "skills", ["name"])

    op.create_table(
        "job_skills",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id", "skill_id"),
    )

    op.create_table(
        "skill_trends",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("month", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrences", sa.Integer(), nullable=True),
        sa.Column("percentage", sa.Float(), nullable=True),
        sa.Column("salary_premium", sa.Float(), nullable=True),
        sa.Column("growth_percentage", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("skill_id", "month", name="unique_skill_month"),
    )
    op.create_index("idx_skill_trends_month", "skill_trends", ["month"])

    op.create_table(
        "salary_data",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("max_salary", sa.Integer(), nullable=True),
        sa.Column("median_salary", sa.Integer(), nullable=True),
        sa.Column("mean_salary", sa.Float(), nullable=True),
        sa.Column("std_dev", sa.Float(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_salary_role", "salary_data", ["role"])
    op.create_index("idx_salary_location", "salary_data", ["location"])


def downgrade() -> None:
    """Drop the core schema."""
    op.drop_index("idx_salary_location", table_name="salary_data")
    op.drop_index("idx_salary_role", table_name="salary_data")
    op.drop_table("salary_data")

    op.drop_index("idx_skill_trends_month", table_name="skill_trends")
    op.drop_table("skill_trends")

    op.drop_table("job_skills")

    op.drop_index("idx_skill_name", table_name="skills")
    op.drop_table("skills")

    op.drop_index("idx_job_posted_date", table_name="job_postings")
    op.drop_index("idx_job_source", table_name="job_postings")
    op.drop_index("idx_job_location", table_name="job_postings")
    op.drop_index("idx_job_company", table_name="job_postings")
    op.drop_index("idx_job_title", table_name="job_postings")
    op.drop_table("job_postings")
