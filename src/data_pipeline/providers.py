"""Provider adapters that normalize job sources into JobPosting records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Protocol

import pandas as pd

from .models import JobPosting
from .scraper import KaggleDataLoader, LinkedInScraper


@dataclass(frozen=True)
class JobSearchRequest:
    """Provider-neutral search request."""

    keywords: List[str]
    limit: int = 100
    location: str | None = None
    work_mode: str | None = None


class JobPostingProvider(Protocol):
    """Interface every job-data provider adapter must implement."""

    source_id: str
    legal_basis: str

    def fetch(self, request: JobSearchRequest) -> List[JobPosting]:
        """Fetch and normalize job postings for a search request."""


class LocalCsvJobProvider:
    """Load legal demo or licensed CSV jobs through the provider interface."""

    source_id = "legal_demo_csv"
    legal_basis = "Local legal demo data for portfolio use."

    def __init__(
        self,
        dataset_path: str | Path,
        source_id: str | None = None,
        legal_basis: str | None = None,
    ):
        self.dataset_path = Path(dataset_path)
        if source_id is not None:
            self.source_id = source_id
        if legal_basis is not None:
            self.legal_basis = legal_basis

    @staticmethod
    def _parse_skills(raw_skills) -> List[str]:
        if isinstance(raw_skills, list):
            return [str(skill).strip() for skill in raw_skills if str(skill).strip()]
        return [
            skill.strip()
            for skill in str(raw_skills or "").split(";")
            if skill.strip()
        ]

    @staticmethod
    def _nullable_value(value):
        return value if pd.notna(value) else None

    @staticmethod
    def _search_blob(job: JobPosting) -> str:
        return " ".join(
            [
                job.title,
                job.company,
                job.location,
                job.description,
                job.role_type or "",
                job.remote_status or "",
                " ".join(job.required_skills),
            ]
        ).lower()

    @staticmethod
    def _matches(job: JobPosting, request: JobSearchRequest) -> bool:
        if request.location and request.location.lower() not in job.location.lower():
            return False
        if request.work_mode and request.work_mode.lower() != "any":
            if request.work_mode.lower() != str(job.remote_status or "").lower():
                return False
        terms = [
            term.strip().lower()
            for keyword in request.keywords
            for term in keyword.split()
            if term.strip()
        ]
        if not terms:
            return True
        blob = LocalCsvJobProvider._search_blob(job)
        return any(term in blob for term in terms)

    def _record_to_job(self, record: Dict) -> JobPosting:
        posted_date = record.get("posted_date")
        if hasattr(posted_date, "to_pydatetime"):
            posted_date = posted_date.to_pydatetime()
        elif not isinstance(posted_date, datetime):
            posted_date = pd.to_datetime(posted_date).to_pydatetime()

        return JobPosting(
            id=str(record["id"]),
            title=str(record["title"]),
            company=str(record["company"]),
            location=str(record["location"]),
            salary_min=self._nullable_value(record.get("salary_min")),
            salary_max=self._nullable_value(record.get("salary_max")),
            job_type=str(record.get("job_type") or "Full-time"),
            description=str(record.get("description") or ""),
            required_skills=self._parse_skills(record.get("required_skills")),
            posted_date=posted_date,
            source=str(record.get("source") or self.source_id),
            url=self._nullable_value(record.get("url")),
            remote_status=self._nullable_value(record.get("remote_status")),
            role_type=self._nullable_value(record.get("role_type")),
            source_legal_basis=self._nullable_value(
                record.get("source_legal_basis")
            ) or self.legal_basis,
        )

    def fetch(self, request: JobSearchRequest) -> List[JobPosting]:
        """Load and filter jobs from the configured CSV file."""
        frame = pd.read_csv(self.dataset_path, parse_dates=["posted_date"])
        jobs = [self._record_to_job(record) for record in frame.to_dict(orient="records")]
        matches = [job for job in jobs if self._matches(job, request)]
        return matches[: request.limit]


class LinkedInJobProvider:
    """Adapter for the legacy LinkedIn loader.

    This remains available for tests and local experimentation. API-level
    governance blocks it unless the source is explicitly approved later.
    """

    source_id = "linkedin"
    legal_basis = "Unapproved live source. Use only as a local mock adapter."

    def __init__(self, scraper: LinkedInScraper | None = None):
        self.scraper = scraper or LinkedInScraper()

    def fetch(self, request: JobSearchRequest) -> List[JobPosting]:
        jobs = []
        keywords = request.keywords or [""]
        per_keyword_limit = max(1, request.limit)
        for keyword in keywords:
            jobs.extend(
                self.scraper.fetch(
                    keyword=keyword,
                    location=request.location or "",
                    limit=per_keyword_limit,
                )
            )
            if len(jobs) >= request.limit:
                break
        return jobs[: request.limit]


class KaggleJobProvider:
    """Adapter for the legacy Kaggle loader."""

    source_id = "kaggle"
    legal_basis = "Unapproved generic dataset source unless a specific license is configured."

    def __init__(self, loader: KaggleDataLoader | None = None):
        self.loader = loader or KaggleDataLoader()

    def fetch(self, request: JobSearchRequest) -> List[JobPosting]:
        return self.loader.fetch(limit=request.limit)
