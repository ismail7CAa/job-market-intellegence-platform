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
    """Load legal seed or licensed CSV jobs through the provider interface."""

    source_id = "legal_demo_csv"
    legal_basis = "Local legal seed data for portfolio use."

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
    def _optional_datetime(value):
        if value is None or pd.isna(value):
            return None
        if hasattr(value, "to_pydatetime"):
            return value.to_pydatetime()
        if isinstance(value, datetime):
            return value
        return pd.to_datetime(value).to_pydatetime()

    @staticmethod
    def _parse_bool(value, default: bool = False) -> bool:
        if value is None or pd.isna(value):
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)

    @staticmethod
    def _infer_city(location: str) -> str | None:
        if not location:
            return None
        return location.split(",")[0].strip() or None

    @staticmethod
    def _infer_country(location: str) -> str:
        if location and "," in location:
            country = location.split(",")[-1].strip()
            if country:
                return country
        return "Germany"

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
        posted_date = self._optional_datetime(record.get("posted_date"))
        location = str(record["location"])
        url = self._nullable_value(record.get("url"))
        application_url = self._nullable_value(record.get("application_url")) or url

        return JobPosting(
            id=str(record["id"]),
            title=str(record["title"]),
            company=str(record["company"]),
            location=location,
            salary_min=self._nullable_value(record.get("salary_min")),
            salary_max=self._nullable_value(record.get("salary_max")),
            salary_period=self._nullable_value(record.get("salary_period")) or "yearly",
            salary_is_estimated=self._parse_bool(record.get("salary_is_estimated"), default=False),
            salary_confidence=self._nullable_value(record.get("salary_confidence")),
            job_type=str(record.get("job_type") or "Full-time"),
            employment_type=self._nullable_value(record.get("employment_type")) or "permanent",
            description=str(record.get("description") or ""),
            required_skills=self._parse_skills(record.get("required_skills")),
            posted_date=posted_date,
            posted_at=self._optional_datetime(record.get("posted_at")) or posted_date,
            expires_at=self._optional_datetime(record.get("expires_at")),
            last_seen_at=self._optional_datetime(record.get("last_seen_at")) or posted_date,
            source=str(record.get("source") or self.source_id),
            source_posting_id=self._nullable_value(record.get("source_posting_id")) or str(record["id"]),
            url=url,
            application_url=application_url,
            company_career_url=self._nullable_value(record.get("company_career_url")),
            country=self._nullable_value(record.get("country")) or self._infer_country(location),
            city=self._nullable_value(record.get("city")) or self._infer_city(location),
            federal_state=self._nullable_value(record.get("federal_state")),
            remote_status=self._nullable_value(record.get("remote_status")),
            role_type=self._nullable_value(record.get("role_type")),
            occupation_group=self._nullable_value(record.get("occupation_group")) or self._nullable_value(record.get("role_type")),
            experience_level=self._nullable_value(record.get("experience_level")),
            source_legal_basis=self._nullable_value(
                record.get("source_legal_basis")
            ) or self.legal_basis,
            ingestion_batch_id=self._nullable_value(record.get("ingestion_batch_id")),
        )

    def fetch(self, request: JobSearchRequest) -> List[JobPosting]:
        """Load and filter jobs from the configured CSV file."""
        parse_dates = [
            column for column in ["posted_date", "posted_at", "expires_at", "last_seen_at"]
            if column in pd.read_csv(self.dataset_path, nrows=0).columns
        ]
        frame = pd.read_csv(self.dataset_path, parse_dates=parse_dates)
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
