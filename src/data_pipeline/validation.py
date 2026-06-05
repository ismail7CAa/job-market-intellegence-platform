"""Pandera schema contracts for data pipeline boundaries."""

from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd
try:
    import pandera.pandas as pa
except ImportError:  # pragma: no cover - supports older Pandera releases.
    import pandera as pa
from pandera import Check

from .models import JobPosting


REQUIRED_JOB_COLUMNS = [
    "id",
    "title",
    "company",
    "location",
    "currency",
    "job_type",
    "description",
    "required_skills",
    "posted_date",
    "source",
]


def _is_not_in_future(series: pd.Series) -> pd.Series:
    posted_dates = pd.to_datetime(series, errors="coerce")
    return posted_dates.notna() & (posted_dates <= pd.Timestamp.now())


def _salary_bounds_are_valid(frame: pd.DataFrame) -> pd.Series:
    missing_salary = frame["salary_min"].isna() | frame["salary_max"].isna()
    return missing_salary | (frame["salary_max"] >= frame["salary_min"])


JOB_POSTINGS_SCHEMA = pa.DataFrameSchema(
    {
        "id": pa.Column(str, nullable=False),
        "title": pa.Column(str, nullable=False),
        "company": pa.Column(str, nullable=False),
        "location": pa.Column(str, nullable=False),
        "salary_min": pa.Column(
            float,
            Check(lambda s: s.isna() | (s > 0), element_wise=False),
            nullable=True,
            coerce=True,
        ),
        "salary_max": pa.Column(
            float,
            Check(lambda s: s.isna() | (s > 0), element_wise=False),
            nullable=True,
            coerce=True,
        ),
        "currency": pa.Column(str, nullable=False),
        "job_type": pa.Column(str, nullable=False),
        "description": pa.Column(str, nullable=False),
        "required_skills": pa.Column(object, nullable=False),
        "posted_date": pa.Column(
            pa.DateTime,
            Check(_is_not_in_future, element_wise=False),
            nullable=False,
            coerce=True,
        ),
        "source": pa.Column(str, nullable=False),
        "url": pa.Column(str, nullable=True, required=False, coerce=True),
        "remote_status": pa.Column(str, nullable=True, required=False, coerce=True),
        "role_type": pa.Column(str, nullable=True, required=False, coerce=True),
        "source_legal_basis": pa.Column(str, nullable=True, required=False, coerce=True),
    },
    checks=Check(_salary_bounds_are_valid, element_wise=False),
    strict=False,
)


def jobs_to_dataframe(jobs: Iterable[JobPosting | Dict]) -> pd.DataFrame:
    """Convert job postings into the dataframe shape validated at boundaries."""
    records: List[Dict] = []
    for job in jobs:
        if isinstance(job, dict):
            records.append(job)
        elif hasattr(job, "model_dump"):
            records.append(job.model_dump(mode="python"))
        else:
            records.append(job.dict())

    frame = pd.DataFrame(records)
    for column in REQUIRED_JOB_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    for column in ["salary_min", "salary_max"]:
        if column not in frame.columns:
            frame[column] = None
    return frame


def validate_job_postings_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate a job postings dataframe and return the validated copy."""
    return JOB_POSTINGS_SCHEMA.validate(frame.copy(), lazy=True)


def validate_job_postings(jobs: Iterable[JobPosting | Dict]) -> pd.DataFrame:
    """Validate job posting records before they cross a pipeline boundary."""
    return validate_job_postings_frame(jobs_to_dataframe(jobs))
