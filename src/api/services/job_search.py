"""Job search, detail, facets, governance, and apply-handoff services."""

from __future__ import annotations

from collections import Counter
from typing import Callable, TYPE_CHECKING
from urllib.parse import quote_plus

from src.data_pipeline.source_policy import evaluate_source

if TYPE_CHECKING:
    from src.database.repository import JobPostingRepository


class JobSearchService:
    """Coordinate job search behavior over a normalized job index."""

    def __init__(
        self,
        jobs_loader: Callable[[], list[dict]] | None = None,
        repository_provider: Callable[[], "JobPostingRepository | None"] | None = None,
        currency: str = "EUR",
        region: str = "Germany",
    ):
        self.jobs_loader = jobs_loader or (lambda: [])
        self.repository_provider = repository_provider
        self.currency = currency
        self.region = region

    def _repository(self) -> "JobPostingRepository | None":
        if not self.repository_provider:
            return None
        return self.repository_provider()

    def _jobs(self) -> list[dict]:
        repository = self._repository()
        if repository:
            return repository.list_job_dicts()
        return self.jobs_loader()

    @staticmethod
    def _counter_rows(counter: Counter, limit: int | None = None) -> list[dict]:
        """Return named counter rows for API contracts."""
        rows = counter.most_common(limit)
        return [{"value": key, "count": value} for key, value in rows]

    @staticmethod
    def salary_midpoint(job: dict) -> float | None:
        """Return a salary midpoint when both bounds are present."""
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        if salary_min is None or salary_max is None:
            return None
        return (float(salary_min) + float(salary_max)) / 2

    @staticmethod
    def _normalize_search_text(value: object) -> str:
        """Normalize values used by the local search index."""
        if value is None:
            return ""
        if isinstance(value, list):
            return " ".join(str(item) for item in value)
        return str(value)

    def _job_search_blob(self, job: dict) -> str:
        """Build the searchable text used by the v1 local search engine."""
        fields = [
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("description"),
            job.get("role_type"),
            job.get("job_type"),
            job.get("remote_status"),
            job.get("required_skills", []),
        ]
        return " ".join(self._normalize_search_text(field) for field in fields).lower()

    @staticmethod
    def infer_apply_url(job: dict) -> str:
        """Return a direct apply/source URL when one is available."""
        if job.get("application_url"):
            return str(job["application_url"])
        if job.get("url"):
            return str(job["url"])
        title = quote_plus(str(job.get("title", "")))
        location = quote_plus(str(job.get("location", "Germany")).replace(", Germany", ""))
        return f"https://www.arbeitsagentur.de/jobsuche/suche?was={title}&wo={location}"

    def find_job_by_id(self, job_id: str) -> dict | None:
        """Find a loaded job posting by id."""
        repository = self._repository()
        if repository:
            return repository.get_job_dict_by_id(job_id)
        for job in self._jobs():
            if str(job.get("id")) == str(job_id):
                return job
        return None

    def build_apply_handoff(self, job: dict) -> dict:
        """Build the apply handoff payload for a single job."""
        source_decision = evaluate_source(
            str(job.get("source", "")),
            legal_basis=job.get("source_legal_basis"),
        )
        apply_url = self.infer_apply_url(job)
        return {
            "job_id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "apply_url": apply_url,
            "application_url": job.get("application_url") or apply_url,
            "company_career_url": job.get("company_career_url"),
            "apply_method": "external_redirect",
            "button_label": "Apply",
            "source": job.get("source"),
            "source_allowed": source_decision.allowed,
            "source_legal_basis": job.get("source_legal_basis"),
            "handoff_note": (
                "The platform sends candidates to the legal source or employer apply page. "
                "It does not collect application documents in v1."
            ),
        }

    def format_salary(self, job: dict) -> dict:
        """Format listed or estimated salary fields for search results."""
        midpoint = self.salary_midpoint(job)
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        if midpoint is None:
            return {
                "salary_min": None,
                "salary_max": None,
                "salary_midpoint": None,
                "salary_label": "Salary not listed",
                "salary_type": "missing",
            }
        return {
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_midpoint": midpoint,
            "salary_label": f"{int(float(salary_min)):,}-{int(float(salary_max)):,} {self.currency}",
            "salary_type": "listed",
        }

    def rank_jobs(
        self,
        jobs: list[dict],
        query: str,
        location: str | None = None,
        work_mode: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        """Rank local jobs against a keyword query and optional filters."""
        query_terms = [
            term.strip().lower()
            for term in query.split()
            if term.strip()
        ]
        location_filter = location.lower().strip() if location else ""
        work_filter = work_mode.lower().strip() if work_mode else ""
        ranked = []

        for job in jobs:
            blob = self._job_search_blob(job)
            if location_filter and location_filter not in str(job.get("location", "")).lower():
                continue
            if work_filter and work_filter != "any":
                if work_filter != str(job.get("remote_status", "")).lower():
                    continue

            if query_terms:
                score = sum(3 if term in str(job.get("title", "")).lower() else 0 for term in query_terms)
                score += sum(1 for term in query_terms if term in blob)
                if score == 0:
                    continue
            else:
                score = 1

            ranked.append((score, job))

        ranked.sort(key=lambda item: (-item[0], str(item[1].get("posted_date", "")), item[1].get("title", "")))
        return [job for _, job in ranked[:limit]]

    def build_job_result(self, job: dict) -> dict:
        """Project a loaded job into the public search-result contract."""
        salary = self.format_salary(job)
        return {
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "job_type": job.get("job_type"),
            "remote_status": job.get("remote_status"),
            "role_type": job.get("role_type"),
            "description": job.get("description"),
            "required_skills": job.get("required_skills", []),
            "posted_date": job.get("posted_date"),
            "source": job.get("source"),
            "source_legal_basis": job.get("source_legal_basis"),
            "source_posting_id": job.get("source_posting_id"),
            "apply_url": self.infer_apply_url(job),
            "apply_endpoint": f"/jobs/{job.get('id')}/apply",
            "application_url": job.get("application_url"),
            "company_career_url": job.get("company_career_url"),
            "country": job.get("country"),
            "city": job.get("city"),
            "federal_state": job.get("federal_state"),
            "occupation_group": job.get("occupation_group"),
            "experience_level": job.get("experience_level"),
            "employment_type": job.get("employment_type"),
            "salary_period": job.get("salary_period"),
            "salary_is_estimated": job.get("salary_is_estimated", False),
            "salary_confidence": job.get("salary_confidence"),
            "expires_at": job.get("expires_at"),
            "last_seen_at": job.get("last_seen_at"),
            "is_expired": job.get("is_expired", False),
            **salary,
        }

    def build_job_detail(self, job: dict) -> dict:
        """Build the full job detail payload for a result detail page."""
        result = self.build_job_result(job)
        salary = self.format_salary(job)
        return {
            **result,
            "full_description": job.get("description"),
            "salary": {
                "currency": self.currency,
                "min": salary["salary_min"],
                "max": salary["salary_max"],
                "midpoint": salary["salary_midpoint"],
                "label": salary["salary_label"],
                "type": salary["salary_type"],
            },
            "company_profile": {
                "name": job.get("company"),
                "current_open_jobs_endpoint": f"/jobs/search?q={quote_plus(str(job.get('company', '')))}",
            },
            "application": self.build_apply_handoff(job),
            "market_context": self.build_job_market_context(job),
        }

    @staticmethod
    def _similarity_score(target: dict, candidate: dict) -> int:
        """Score how related two jobs are using stable structured fields."""
        if target.get("id") == candidate.get("id"):
            return 0
        score = 0
        if target.get("role_type") and target.get("role_type") == candidate.get("role_type"):
            score += 5
        if target.get("location") and target.get("location") == candidate.get("location"):
            score += 3
        if target.get("remote_status") and target.get("remote_status") == candidate.get("remote_status"):
            score += 2
        target_skills = {str(skill).lower() for skill in target.get("required_skills", [])}
        candidate_skills = {str(skill).lower() for skill in candidate.get("required_skills", [])}
        score += len(target_skills & candidate_skills)
        return score

    def build_similar_jobs(self, job: dict, limit: int = 5) -> dict:
        """Return jobs similar to the selected posting."""
        repository = self._repository()
        if repository and job.get("id"):
            similar_jobs = repository.query_similar_job_dicts(str(job["id"]), limit=limit)
            return {
                "job_id": job.get("id"),
                "count": len(similar_jobs),
                "jobs": [self.build_job_result(candidate) for candidate in similar_jobs],
            }

        ranked = [
            (self._similarity_score(job, candidate), candidate)
            for candidate in self._jobs()
            if candidate.get("id") != job.get("id")
        ]
        ranked = [item for item in ranked if item[0] > 0]
        ranked.sort(key=lambda item: (-item[0], item[1].get("title", "")))
        return {
            "job_id": job.get("id"),
            "count": min(len(ranked), limit),
            "jobs": [self.build_job_result(candidate) for _, candidate in ranked[:limit]],
        }

    def build_job_market_context(self, job: dict) -> dict:
        """Summarize market context around a selected job."""
        jobs = self._jobs()
        same_role = [
            item for item in jobs
            if item.get("role_type") and item.get("role_type") == job.get("role_type")
        ]
        same_location = [
            item for item in jobs
            if item.get("location") == job.get("location")
        ]
        salaries = [
            self.salary_midpoint(item)
            for item in same_role
            if self.salary_midpoint(item) is not None
        ]
        return {
            "role_type": job.get("role_type"),
            "same_role_count": len(same_role),
            "same_location_count": len(same_location),
            "role_average_salary": round(sum(salaries) / len(salaries), 2) if salaries else None,
            "similar_jobs_endpoint": f"/jobs/{job.get('id')}/similar",
        }

    def build_search_facets(self) -> dict:
        """Return filter facets for the current job index."""
        repository = self._repository()
        if repository:
            facets = repository.get_facets()
            return {
                "status": "ready",
                "total_jobs": facets["total_jobs"],
                "locations": self._counter_rows(facets["locations"]),
                "role_types": self._counter_rows(facets["role_types"]),
                "companies": self._counter_rows(facets["companies"]),
                "work_modes": self._counter_rows(facets["work_modes"]),
                "job_types": self._counter_rows(facets["job_types"]),
                "salary_range": {
                    "min": min(facets["salary_midpoints"]) if facets["salary_midpoints"] else None,
                    "max": max(facets["salary_midpoints"]) if facets["salary_midpoints"] else None,
                    "currency": self.currency,
                },
            }

        jobs = self._jobs()
        locations = Counter(job.get("location") for job in jobs if job.get("location"))
        role_types = Counter(job.get("role_type") for job in jobs if job.get("role_type"))
        companies = Counter(job.get("company") for job in jobs if job.get("company"))
        work_modes = Counter(job.get("remote_status") for job in jobs if job.get("remote_status"))
        job_types = Counter(job.get("job_type") for job in jobs if job.get("job_type"))
        salary_midpoints = [
            self.salary_midpoint(job)
            for job in jobs
            if self.salary_midpoint(job) is not None
        ]
        return {
            "status": "ready",
            "total_jobs": len(jobs),
            "locations": self._counter_rows(locations),
            "role_types": self._counter_rows(role_types),
            "companies": self._counter_rows(companies),
            "work_modes": self._counter_rows(work_modes),
            "job_types": self._counter_rows(job_types),
            "salary_range": {
                "min": min(salary_midpoints) if salary_midpoints else None,
                "max": max(salary_midpoints) if salary_midpoints else None,
                "currency": self.currency,
            },
        }

    def build_search_response(
        self,
        query: str = "",
        location: str | None = None,
        work_mode: str | None = None,
        limit: int = 25,
    ) -> dict:
        """Search loaded German job data and summarize the result set."""
        repository = self._repository()
        if repository:
            jobs = repository.query_job_dicts(
                query=query,
                location=location,
                work_mode=work_mode,
                limit=max(limit, 100),
            )
        else:
            jobs = self._jobs()
        matches = self.rank_jobs(jobs, query=query, location=location, work_mode=work_mode, limit=limit)
        result_jobs = [self.build_job_result(job) for job in matches]
        salaries = [
            job["salary_midpoint"]
            for job in result_jobs
            if job["salary_midpoint"] is not None
        ]
        companies = Counter(job["company"] for job in result_jobs if job.get("company"))
        locations = Counter(job["location"] for job in result_jobs if job.get("location"))
        role_types = Counter(job["role_type"] for job in result_jobs if job.get("role_type"))

        return {
            "query": query,
            "location": location,
            "work_mode": work_mode or "any",
            "count": len(result_jobs),
            "jobs": result_jobs,
            "summary": {
                "average_salary": round(sum(salaries) / len(salaries), 2) if salaries else None,
                "salary_sample_size": len(salaries),
                "top_companies": self._counter_rows(companies, limit=5),
                "top_locations": self._counter_rows(locations, limit=5),
                "role_types": self._counter_rows(role_types, limit=5),
                "apply_links_available": sum(1 for job in result_jobs if job.get("apply_url")),
            },
            "data_governance": {
                "region": self.region,
                "currency": self.currency,
                "legal_position": (
                    "This v1 uses local legal seed listings. Production ingestion must use an official API, "
                    "a licensed job-data provider, or company feeds with explicit permission."
                ),
                "blocked_sources": ["unapproved scraping", "terms-of-service bypassing", "personal data collection without purpose"],
            },
        }

    def build_data_governance_report(self) -> dict:
        """Describe which data sources are safe for the current platform stage."""
        source_basis = {}
        for job in self._jobs():
            source = str(job.get("source", "unknown"))
            source_basis.setdefault(source, job.get("source_legal_basis"))

        decisions = [
            evaluate_source(source, legal_basis=basis)
            for source, basis in sorted(source_basis.items())
        ]

        return {
            "status": "ready",
            "market_region": self.region,
            "approved_for_current_stage": all(decision.allowed for decision in decisions),
            "sources": [
                {
                    "source": decision.source,
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "required_action": decision.required_action,
                    "legal_basis": source_basis.get(decision.source),
                }
                for decision in decisions
            ],
            "production_rule": (
                "Live job-listing ingestion must use an official API, a licensed provider, "
                "or a company feed with explicit permission. Public website scraping and "
                "terms-of-service bypassing are blocked."
            ),
            "candidate_live_sources": [
                {
                    "name": "Licensed job data provider",
                    "status": "recommended for production",
                    "use": "Normalized job listings with apply links, salary fields when available, and provider terms.",
                },
                {
                    "name": "Company career feeds",
                    "status": "safe when permission is explicit",
                    "use": "Direct employer jobs and apply URLs.",
                },
                {
                    "name": "Bundesagentur fuer Arbeit statistics APIs",
                    "status": "useful for aggregate market context",
                    "use": "Regional labor-market context, not direct job listings for this engine.",
                },
            ],
        }

    @staticmethod
    def build_engine_workflow() -> dict:
        """Return the backend workflow the product is designed around."""
        return {
            "status": "ready",
            "workflow": [
                {
                    "step": "Search intent",
                    "task": "Accept any job title, profession, company, skill, or location in Germany.",
                    "current_backend": "/jobs/search parameters q, location, work_mode, limit",
                },
                {
                    "step": "Legal source gate",
                    "task": "Allow only legal seed listings, licensed providers, official APIs, or explicit company feeds.",
                    "current_backend": "/data/governance and protected /data/fetch",
                },
                {
                    "step": "Normalize jobs",
                    "task": "Convert source records into one JobPosting contract with role type, work mode, salary, source, and apply URL.",
                    "current_backend": "JobPosting model plus Pandera dataframe boundary validation",
                },
                {
                    "step": "Rank matching jobs",
                    "task": "Match query terms against title, description, company, location, role category, job type, work mode, and skills.",
                    "current_backend": "JobSearchService.rank_jobs",
                },
                {
                    "step": "Market intelligence",
                    "task": "Summarize salary, companies, locations, role categories, and apply-link availability for the result set.",
                    "current_backend": "JobSearchService.build_search_response",
                },
                {
                    "step": "Apply handoff",
                    "task": "Expose a direct apply/source link when the legal source provides one.",
                    "current_backend": "/jobs/{job_id}/apply redirects to the legal apply/source URL",
                },
            ],
            "next_backend_increment": (
                "Add a provider adapter interface and one approved live provider implementation "
                "after the source terms are confirmed."
            ),
        }
