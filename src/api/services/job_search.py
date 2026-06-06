"""Job search, detail, facets, governance, and apply-handoff services."""

from __future__ import annotations

from collections import Counter
import math
from typing import Callable, TYPE_CHECKING
from urllib.parse import quote_plus

from src.data_pipeline.source_policy import evaluate_source
from src.market_context import EscoNormalizer

if TYPE_CHECKING:
    from src.database.repository import JobPostingRepository


class JobSearchService:
    """Coordinate job search behavior over a normalized job index."""

    ALLOWED_SORTS = {
        "relevance",
        "salary_desc",
        "salary_asc",
        "posted_desc",
        "posted_asc",
        "company",
        "title",
    }

    def __init__(
        self,
        jobs_loader: Callable[[], list[dict]] | None = None,
        repository_provider: Callable[[], "JobPostingRepository | None"] | None = None,
        esco_normalizer: EscoNormalizer | None = None,
        currency: str = "EUR",
        region: str = "Germany",
    ):
        self.jobs_loader = jobs_loader or (lambda: [])
        self.repository_provider = repository_provider
        self.esco_normalizer = esco_normalizer or EscoNormalizer()
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
    def _suggestion_label(value: str, category: str) -> str:
        """Return a compact label for a typeahead suggestion."""
        labels = {
            "title": "Job title",
            "company": "Company",
            "location": "Location",
            "skill": "Skill",
            "occupation": "Occupation",
            "role_type": "Role group",
        }
        return f"{value} · {labels.get(category, category)}"

    @staticmethod
    def _suggestion_score(value: str, count: int, query: str, category: str) -> tuple[int, int, str]:
        """Sort exact prefix suggestions above broad contains matches."""
        normalized_value = value.lower()
        normalized_query = query.lower()
        category_priority = {
            "title": 0,
            "occupation": 1,
            "skill": 2,
            "role_type": 3,
            "company": 4,
            "location": 5,
        }.get(category, 9)
        if normalized_value == normalized_query:
            match_rank = 0
        elif normalized_value.startswith(normalized_query):
            match_rank = 1
        else:
            match_rank = 2
        return (match_rank, category_priority, -count, normalized_value)

    @staticmethod
    def salary_midpoint(job: dict) -> float | None:
        """Return a salary midpoint when both bounds are present."""
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        if salary_min is None or salary_max is None:
            return None
        return (float(salary_min) + float(salary_max)) / 2

    @staticmethod
    def _salary_bounds(job: dict) -> tuple[float, float] | None:
        """Return salary bounds when both values are present."""
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        if salary_min is None or salary_max is None:
            return None
        return float(salary_min), float(salary_max)

    @staticmethod
    def _is_listed_salary(job: dict) -> bool:
        """Return whether a job has a real listed salary."""
        return (
            job.get("salary_min") is not None
            and job.get("salary_max") is not None
            and not bool(job.get("salary_is_estimated", False))
        )

    @staticmethod
    def _experience_multiplier(experience_level: str | None) -> float:
        level = str(experience_level or "").lower()
        if level in {"entry", "junior", "trainee"}:
            return 0.9
        if level in {"senior", "lead", "manager"}:
            return 1.12
        return 1.0

    @staticmethod
    def _location_multiplier(location: str | None) -> float:
        value = str(location or "").lower()
        if any(city in value for city in ["munich", "frankfurt", "stuttgart", "hamburg"]):
            return 1.05
        if any(city in value for city in ["leipzig", "dresden", "bremen", "hannover"]):
            return 0.95
        return 1.0

    def estimate_salary(self, job: dict, reference_jobs: list[dict] | None = None) -> dict | None:
        """Estimate missing salary from role, location, and experience peers."""
        if self._is_listed_salary(job):
            return None

        peers = [
            item for item in (reference_jobs or self._jobs())
            if item.get("id") != job.get("id") and self._is_listed_salary(item)
        ]
        if not peers:
            return None

        role = str(job.get("role_type") or "").lower()
        occupation_group = str(job.get("occupation_group") or "").lower()
        location = str(job.get("location") or "").lower()
        experience = str(job.get("experience_level") or "").lower()

        candidate_sets = [
            (
                "role type + location + experience level",
                0.86,
                [
                    item for item in peers
                    if str(item.get("role_type") or "").lower() == role
                    and str(item.get("location") or "").lower() == location
                    and str(item.get("experience_level") or "").lower() == experience
                ],
            ),
            (
                "role type + location",
                0.78,
                [
                    item for item in peers
                    if str(item.get("role_type") or "").lower() == role
                    and str(item.get("location") or "").lower() == location
                ],
            ),
            (
                "role type + experience level",
                0.7,
                [
                    item for item in peers
                    if str(item.get("role_type") or "").lower() == role
                    and str(item.get("experience_level") or "").lower() == experience
                ],
            ),
            (
                "role type",
                0.62,
                [
                    item for item in peers
                    if str(item.get("role_type") or "").lower() == role
                ],
            ),
            (
                "occupation group",
                0.54,
                [
                    item for item in peers
                    if str(item.get("occupation_group") or "").lower() == occupation_group
                ],
            ),
        ]

        basis = None
        confidence = 0.0
        matches: list[dict] = []
        for candidate_basis, candidate_confidence, candidate_matches in candidate_sets:
            if candidate_matches:
                basis = candidate_basis
                confidence = candidate_confidence
                matches = candidate_matches
                break
        if not matches:
            return None

        mins = [float(item["salary_min"]) for item in matches]
        maxes = [float(item["salary_max"]) for item in matches]
        estimated_min = sum(mins) / len(mins)
        estimated_max = sum(maxes) / len(maxes)

        if basis in {"role type", "occupation group"}:
            multiplier = (
                self._experience_multiplier(job.get("experience_level"))
                * self._location_multiplier(job.get("location"))
            )
            estimated_min *= multiplier
            estimated_max *= multiplier

        confidence = min(confidence + min(len(matches), 5) * 0.02, 0.9)
        return {
            "salary_min": round(estimated_min, -2),
            "salary_max": round(estimated_max, -2),
            "salary_midpoint": round((estimated_min + estimated_max) / 2, 2),
            "salary_is_estimated": True,
            "salary_confidence": round(confidence, 2),
            "salary_estimation_basis": basis,
        }

    def effective_salary(self, job: dict, reference_jobs: list[dict] | None = None) -> dict:
        """Return listed or estimated salary fields without hiding the source type."""
        formatted = self.format_salary(job, reference_jobs=reference_jobs)
        return formatted

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
            self.esco_normalizer.search_terms_for_job(job),
        ]
        return " ".join(self._normalize_search_text(field) for field in fields).lower()

    def _expanded_query_terms(self, query: str) -> list[str]:
        """Return query terms expanded with ESCO occupation and skill aliases."""
        terms = [
            term.strip().lower()
            for term in query.split()
            if term.strip()
        ]
        terms.extend(self.esco_normalizer.expand_query_terms(query))
        return sorted({term for term in terms if term})

    def build_search_suggestions(self, query: str, limit: int = 8) -> dict:
        """Return typeahead suggestions from indexed jobs and ESCO-normalized terms."""
        normalized_query = query.strip().lower()
        if not normalized_query:
            return {"status": "ready", "query": query, "suggestions": []}

        counters: dict[str, Counter] = {
            "title": Counter(),
            "company": Counter(),
            "location": Counter(),
            "skill": Counter(),
            "occupation": Counter(),
            "role_type": Counter(),
        }

        for job in self._jobs():
            for category, value in (
                ("title", job.get("title")),
                ("company", job.get("company")),
                ("location", job.get("city") or job.get("location")),
                ("occupation", job.get("occupation_group")),
                ("role_type", job.get("role_type")),
            ):
                if value and normalized_query in str(value).lower():
                    counters[category][str(value)] += 1
            for skill in job.get("required_skills", []) or []:
                if normalized_query in str(skill).lower():
                    counters["skill"][str(skill)] += 1

        normalized = self.esco_normalizer.normalize_query(query)
        for concept in normalized.get("occupations", []):
            value = concept.get("preferred_label")
            if value:
                counters["title"][str(value)] += 3
            for alias in concept.get("aliases", []):
                if normalized_query in str(alias).lower():
                    counters["occupation"][str(alias)] += 1
        for concept in normalized.get("skills", []):
            value = concept.get("preferred_label")
            if value:
                counters["skill"][str(value)] += 2

        rows = []
        seen = set()
        for category, counter in counters.items():
            for value, count in counter.items():
                key = value.lower()
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "value": value,
                    "label": self._suggestion_label(value, category),
                    "category": category,
                    "count": count,
                    "_sort": self._suggestion_score(value, count, normalized_query, category),
                })

        rows.sort(key=lambda row: row["_sort"])
        suggestions = [
            {key: value for key, value in row.items() if key != "_sort"}
            for row in rows[:limit]
        ]
        return {
            "status": "ready",
            "query": query,
            "suggestions": suggestions,
        }

    @staticmethod
    def _contains(value: object, term: str) -> bool:
        """Return whether a normalized term is contained in a value."""
        if value is None:
            return False
        if isinstance(value, list):
            return any(term in str(item).lower() for item in value)
        return term in str(value).lower()

    def _salary_matches(
        self,
        job: dict,
        salary_min: float | None = None,
        salary_max: float | None = None,
        reference_jobs: list[dict] | None = None,
    ) -> bool:
        """Return whether a job salary overlaps the requested salary range."""
        midpoint = self.effective_salary(job, reference_jobs=reference_jobs).get("salary_midpoint")
        if midpoint is None:
            return salary_min is None and salary_max is None
        if salary_min is not None and midpoint < salary_min:
            return False
        if salary_max is not None and midpoint > salary_max:
            return False
        return True

    def _filter_job(
        self,
        job: dict,
        location: str | None = None,
        work_mode: str | None = None,
        company: str | None = None,
        role_type: str | None = None,
        salary_min: float | None = None,
        salary_max: float | None = None,
        employment_type: str | None = None,
        reference_jobs: list[dict] | None = None,
    ) -> bool:
        """Apply structured search filters to one job."""
        if location and location.lower().strip() not in str(job.get("location", "")).lower():
            return False
        if work_mode and work_mode.lower().strip() != "any":
            if work_mode.lower().strip() != str(job.get("remote_status", "")).lower():
                return False
        if company and company.lower().strip() not in str(job.get("company", "")).lower():
            return False
        if role_type and role_type.lower().strip() not in str(job.get("role_type", "")).lower():
            return False
        if employment_type and employment_type.lower().strip() not in str(job.get("employment_type", "")).lower():
            return False
        return self._salary_matches(
            job,
            salary_min=salary_min,
            salary_max=salary_max,
            reference_jobs=reference_jobs,
        )

    def _score_job(self, job: dict, query_terms: list[str]) -> tuple[float, list[str]]:
        """Score one job and explain why it matched."""
        if not query_terms:
            return 1.0, ["No keyword query; included by active listing filters."]

        score = 0.0
        reasons: list[str] = []
        title = str(job.get("title", "")).lower()
        company = str(job.get("company", "")).lower()
        role_type = str(job.get("role_type", "")).lower()
        occupation_group = str(job.get("occupation_group", "")).lower()
        description = str(job.get("description", "")).lower()
        skill_text = " ".join(str(skill) for skill in job.get("required_skills", [])).lower()
        esco_terms = " ".join(self.esco_normalizer.search_terms_for_job(job)).lower()

        for term in query_terms:
            term_score = 0.0
            if term in title:
                term_score += 8
            if term in role_type or term in occupation_group:
                term_score += 5
            if term in skill_text:
                term_score += 4
            if term in esco_terms:
                term_score += 3
            if term in company:
                term_score += 2
            if term in description:
                term_score += 1

            if term_score:
                score += term_score
                if term in title and "title match" not in reasons:
                    reasons.append("title match")
                elif (term in role_type or term in occupation_group) and "occupation match" not in reasons:
                    reasons.append("occupation match")
                elif term in skill_text and "skill match" not in reasons:
                    reasons.append("skill match")
                elif term in esco_terms and "ESCO synonym match" not in reasons:
                    reasons.append("ESCO synonym match")
                elif term in company and "company match" not in reasons:
                    reasons.append("company match")
                elif term in description and "description match" not in reasons:
                    reasons.append("description match")

        return score, reasons

    @staticmethod
    def _boost_exact_query_match(job: dict, query: str, score: float, reasons: list[str]) -> tuple[float, list[str]]:
        """Boost exact title matches above broad ESCO occupation aliases."""
        normalized_query = query.strip().lower()
        if normalized_query and normalized_query in str(job.get("title", "")).lower():
            score += 20
            reasons = [reason for reason in reasons if reason != "title match"]
            reasons.insert(0, "title match")
        return score, reasons

    @staticmethod
    def _sort_value(job: dict, sort: str) -> object:
        if sort in {"salary_desc", "salary_asc"}:
            return job.get("salary_midpoint") if job.get("salary_midpoint") is not None else -1
        if sort in {"posted_desc", "posted_asc"}:
            return str(job.get("posted_date") or "")
        if sort == "company":
            return str(job.get("company") or "")
        if sort == "title":
            return str(job.get("title") or "")
        return job.get("relevance_score") or 0

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

    def format_salary(self, job: dict, reference_jobs: list[dict] | None = None) -> dict:
        """Format listed or estimated salary fields for search results."""
        midpoint = self.salary_midpoint(job)
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        if midpoint is None:
            estimate = self.estimate_salary(job, reference_jobs=reference_jobs)
            if estimate:
                return {
                    "salary_min": estimate["salary_min"],
                    "salary_max": estimate["salary_max"],
                    "salary_midpoint": estimate["salary_midpoint"],
                    "salary_label": (
                        f"Estimated {int(float(estimate['salary_min'])):,}-"
                        f"{int(float(estimate['salary_max'])):,} {self.currency}"
                    ),
                    "salary_type": "estimated",
                    "salary_is_estimated": True,
                    "salary_confidence": estimate["salary_confidence"],
                    "salary_estimation_basis": estimate["salary_estimation_basis"],
                }
            return {
                "salary_min": None,
                "salary_max": None,
                "salary_midpoint": None,
                "salary_label": "Salary not listed",
                "salary_type": "missing",
                "salary_is_estimated": False,
                "salary_confidence": None,
                "salary_estimation_basis": None,
            }
        salary_type = "estimated" if job.get("salary_is_estimated") else "listed"
        salary_label_prefix = "Estimated " if salary_type == "estimated" else ""
        return {
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_midpoint": midpoint,
            "salary_label": f"{salary_label_prefix}{int(float(salary_min)):,}-{int(float(salary_max)):,} {self.currency}",
            "salary_type": salary_type,
            "salary_is_estimated": bool(job.get("salary_is_estimated", False)),
            "salary_confidence": job.get("salary_confidence") if job.get("salary_is_estimated") else 1.0,
            "salary_estimation_basis": job.get("salary_estimation_basis"),
        }

    def rank_jobs(
        self,
        jobs: list[dict],
        query: str,
        location: str | None = None,
        work_mode: str | None = None,
        company: str | None = None,
        role_type: str | None = None,
        salary_min: float | None = None,
        salary_max: float | None = None,
        employment_type: str | None = None,
        sort: str = "relevance",
        limit: int = 25,
        offset: int = 0,
        reference_jobs: list[dict] | None = None,
    ) -> list[dict]:
        """Rank local jobs against a keyword query and optional filters."""
        query_terms = self._expanded_query_terms(query)
        ranked: list[dict] = []
        salary_reference_jobs = reference_jobs or jobs

        for job in jobs:
            if not self._filter_job(
                job,
                location=location,
                work_mode=work_mode,
                company=company,
                role_type=role_type,
                salary_min=salary_min,
                salary_max=salary_max,
                employment_type=employment_type,
                reference_jobs=salary_reference_jobs,
            ):
                continue

            score, reasons = self._score_job(job, query_terms)
            score, reasons = self._boost_exact_query_match(job, query, score, reasons)
            if query_terms and score == 0:
                continue

            ranked_job = {
                **job,
                "relevance_score": round(score, 2),
                "match_reasons": reasons,
                **self.format_salary(job, reference_jobs=salary_reference_jobs),
            }
            ranked.append(ranked_job)

        reverse = sort in {"relevance", "salary_desc", "posted_desc"}
        ranked.sort(
            key=lambda job: (
                self._sort_value(job, sort),
                str(job.get("posted_date") or ""),
                str(job.get("title") or ""),
            ),
            reverse=reverse,
        )
        return ranked[offset: offset + limit]

    def build_job_result(self, job: dict, reference_jobs: list[dict] | None = None) -> dict:
        """Project a loaded job into the public search-result contract."""
        salary = self.format_salary(job, reference_jobs=reference_jobs)
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
            "salary_is_estimated": salary.get("salary_is_estimated", job.get("salary_is_estimated", False)),
            "salary_confidence": salary.get("salary_confidence", job.get("salary_confidence")),
            "salary_estimation_basis": salary.get("salary_estimation_basis"),
            "expires_at": job.get("expires_at"),
            "last_seen_at": job.get("last_seen_at"),
            "is_expired": job.get("is_expired", False),
            "relevance_score": job.get("relevance_score"),
            "match_reasons": job.get("match_reasons", []),
            **salary,
        }

    def build_job_detail(self, job: dict) -> dict:
        """Build the full job detail payload for a result detail page."""
        reference_jobs = self._jobs()
        result = self.build_job_result(job, reference_jobs=reference_jobs)
        salary = self.format_salary(job, reference_jobs=reference_jobs)
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
                "is_estimated": salary["salary_is_estimated"],
                "confidence": salary["salary_confidence"],
                "estimation_basis": salary["salary_estimation_basis"],
            },
            "company_profile": {
                "name": job.get("company"),
                "current_open_jobs_endpoint": f"/jobs/search?q={quote_plus(str(job.get('company', '')))}",
            },
            "application": self.build_apply_handoff(job),
            "market_context": self.build_job_market_context(job),
        }

    def _similarity_score(self, target: dict, candidate: dict) -> int:
        """Score how related two jobs are using stable structured fields."""
        if target.get("id") == candidate.get("id"):
            return 0
        score = 0
        if target.get("role_type") and target.get("role_type") == candidate.get("role_type"):
            score += 5
        if target.get("occupation_group") and target.get("occupation_group") == candidate.get("occupation_group"):
            score += 4
        if target.get("location") and target.get("location") == candidate.get("location"):
            score += 3
        if target.get("remote_status") and target.get("remote_status") == candidate.get("remote_status"):
            score += 2
        target_skills = {str(skill).lower() for skill in target.get("required_skills", [])}
        candidate_skills = {str(skill).lower() for skill in candidate.get("required_skills", [])}
        score += len(target_skills & candidate_skills)
        target_esco = {term.lower() for term in self.esco_normalizer.search_terms_for_job(target)}
        candidate_esco = {term.lower() for term in self.esco_normalizer.search_terms_for_job(candidate)}
        score += len(target_esco & candidate_esco)
        return score

    def build_similar_jobs(self, job: dict, limit: int = 5) -> dict:
        """Return jobs similar to the selected posting."""
        repository = self._repository()
        if repository and job.get("id"):
            similar_jobs = repository.query_similar_job_dicts(str(job["id"]), limit=limit)
            return {
                "job_id": job.get("id"),
                "count": len(similar_jobs),
                "jobs": [self.build_job_result(candidate, reference_jobs=self._jobs()) for candidate in similar_jobs],
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
            "jobs": [self.build_job_result(candidate, reference_jobs=self._jobs()) for _, candidate in ranked[:limit]],
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
        limit: int | None = None,
        page: int = 1,
        per_page: int | None = None,
        sort: str = "relevance",
        company: str | None = None,
        role_type: str | None = None,
        salary_min: float | None = None,
        salary_max: float | None = None,
        employment_type: str | None = None,
    ) -> dict:
        """Search loaded German job data and summarize the result set."""
        per_page = per_page or limit or 25
        page = max(page, 1)
        sort = sort if sort in self.ALLOWED_SORTS else "relevance"
        offset = (page - 1) * per_page
        salary_reference_jobs = self._jobs()
        repository = self._repository()
        if repository:
            jobs = repository.query_job_dicts(
                query="",
                location=location,
                work_mode=work_mode,
                company=company,
                role_type=role_type,
                employment_type=employment_type,
                limit=max(per_page, 1_000),
            )
        else:
            jobs = self._jobs()
        ranked_matches = self.rank_jobs(
            jobs,
            query=query,
            location=location,
            work_mode=work_mode,
            company=company,
            role_type=role_type,
            salary_min=salary_min,
            salary_max=salary_max,
            employment_type=employment_type,
            sort=sort,
            limit=len(jobs) or per_page,
            offset=0,
            reference_jobs=salary_reference_jobs,
        )
        matches = ranked_matches[offset: offset + per_page]
        result_jobs = [self.build_job_result(job, reference_jobs=salary_reference_jobs) for job in matches]
        all_result_jobs = [self.build_job_result(job, reference_jobs=salary_reference_jobs) for job in ranked_matches]
        salaries = [
            job["salary_midpoint"]
            for job in all_result_jobs
            if job["salary_midpoint"] is not None
        ]
        companies = Counter(job["company"] for job in all_result_jobs if job.get("company"))
        locations = Counter(job["location"] for job in all_result_jobs if job.get("location"))
        role_types = Counter(job["role_type"] for job in all_result_jobs if job.get("role_type"))
        total = len(ranked_matches)
        listed_salary_count = sum(1 for job in all_result_jobs if job.get("salary_type") == "listed")
        estimated_salary_count = sum(1 for job in all_result_jobs if job.get("salary_type") == "estimated")

        return {
            "query": query,
            "location": location,
            "work_mode": work_mode or "any",
            "sort": sort,
            "count": len(result_jobs),
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page) if total else 0,
            "filters": {
                "company": company,
                "role_type": role_type,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "employment_type": employment_type,
            },
            "jobs": result_jobs,
            "summary": {
                "average_salary": round(sum(salaries) / len(salaries), 2) if salaries else None,
                "salary_sample_size": len(salaries),
                "listed_salary_sample_size": listed_salary_count,
                "estimated_salary_sample_size": estimated_salary_count,
                "top_companies": self._counter_rows(companies, limit=5),
                "top_locations": self._counter_rows(locations, limit=5),
                "role_types": self._counter_rows(role_types, limit=5),
                "apply_links_available": sum(1 for job in all_result_jobs if job.get("apply_url")),
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
                    "current_backend": "/data/governance and protected /data/fetch through IngestionService",
                },
                {
                    "step": "Normalize jobs",
                    "task": "Convert source records into one JobPosting contract with role type, work mode, salary, source, and apply URL.",
                    "current_backend": "JobPostingProvider adapters, JobPosting model, and Pandera dataframe boundary validation",
                },
                {
                    "step": "Rank matching jobs",
                    "task": "Normalize occupation and skill aliases with ESCO, then match query terms against title, description, company, location, role category, job type, work mode, and skills.",
                    "current_backend": "EscoNormalizer plus JobSearchService.rank_jobs",
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
                "Add one approved live provider implementation after source terms are confirmed, "
                "then schedule IngestionService as a refresh job."
            ),
        }
