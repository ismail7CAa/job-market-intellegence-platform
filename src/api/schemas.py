"""Pydantic response schemas for the public API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base API schema with strict response fields."""

    model_config = ConfigDict(extra="forbid")


class FacetCount(ApiModel):
    """A filter value and its result count."""

    value: str
    count: int


class SalaryFields(ApiModel):
    """Salary fields included in search result cards."""

    salary_min: float | None = None
    salary_max: float | None = None
    salary_midpoint: float | None = None
    salary_label: str
    salary_type: Literal["listed", "missing", "estimated"]
    salary_estimation_basis: str | None = None


class JobResult(SalaryFields):
    """Compact job result used by search and similar-job responses."""

    id: str
    title: str
    company: str
    location: str
    job_type: str | None = None
    remote_status: str | None = None
    role_type: str | None = None
    description: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    posted_date: datetime | str | None = None
    source: str | None = None
    source_legal_basis: str | None = None
    source_posting_id: str | None = None
    apply_url: str
    apply_endpoint: str
    application_url: str | None = None
    company_career_url: str | None = None
    country: str | None = None
    city: str | None = None
    federal_state: str | None = None
    occupation_group: str | None = None
    experience_level: str | None = None
    employment_type: str | None = None
    salary_period: str | None = None
    salary_is_estimated: bool = False
    salary_confidence: float | None = None
    expires_at: datetime | str | None = None
    last_seen_at: datetime | str | None = None
    is_expired: bool = False
    relevance_score: float | None = None
    match_reasons: list[str] = Field(default_factory=list)


class SearchSummary(ApiModel):
    """Aggregate intelligence for a search result set."""

    average_salary: float | None = None
    salary_sample_size: int
    listed_salary_sample_size: int = 0
    estimated_salary_sample_size: int = 0
    top_companies: list[FacetCount]
    top_locations: list[FacetCount]
    role_types: list[FacetCount]
    apply_links_available: int


class SearchGovernance(ApiModel):
    """Data governance note included with search responses."""

    region: str
    currency: str
    legal_position: str
    blocked_sources: list[str]


class JobSearchResponse(ApiModel):
    """Response contract for /jobs/search."""

    query: str
    location: str | None = None
    work_mode: str
    sort: str
    count: int
    total: int
    page: int
    per_page: int
    total_pages: int
    filters: "SearchFilters"
    jobs: list[JobResult]
    summary: SearchSummary
    data_governance: SearchGovernance


class SearchFilters(ApiModel):
    """Applied filters for /jobs/search."""

    company: str | None = None
    role_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    employment_type: str | None = None


class SalaryDetail(ApiModel):
    """Detailed salary object for a job detail page."""

    currency: str
    min: float | None = None
    max: float | None = None
    midpoint: float | None = None
    label: str
    type: Literal["listed", "missing", "estimated"]
    is_estimated: bool = False
    confidence: float | None = None
    estimation_basis: str | None = None


class CompanyProfile(ApiModel):
    """Company context exposed on a job detail page."""

    name: str | None = None
    current_open_jobs_endpoint: str


class ApplyHandoff(ApiModel):
    """Application handoff contract."""

    job_id: str
    title: str
    company: str
    location: str
    apply_url: str
    application_url: str
    company_career_url: str | None = None
    apply_method: Literal["external_redirect"]
    button_label: str
    source: str | None = None
    source_allowed: bool
    source_legal_basis: str | None = None
    handoff_note: str


class MarketContext(ApiModel):
    """Market context for a selected job."""

    role_type: str | None = None
    same_role_count: int
    same_location_count: int
    role_average_salary: float | None = None
    similar_jobs_endpoint: str


class JobDetailResponse(JobResult):
    """Full job detail response contract."""

    full_description: str | None = None
    salary: SalaryDetail
    company_profile: CompanyProfile
    application: ApplyHandoff
    market_context: MarketContext


class SimilarJobsResponse(ApiModel):
    """Response contract for similar jobs."""

    job_id: str
    count: int
    jobs: list[JobResult]


class SalaryFacetRange(ApiModel):
    """Salary range available in the current index."""

    min: float | None = None
    max: float | None = None
    currency: str


class SearchFacetsResponse(ApiModel):
    """Response contract for search filter facets."""

    status: Literal["ready"]
    total_jobs: int
    locations: list[FacetCount]
    role_types: list[FacetCount]
    companies: list[FacetCount]
    work_modes: list[FacetCount]
    job_types: list[FacetCount]
    salary_range: SalaryFacetRange


class SourceGovernance(ApiModel):
    """Governance status for one data source."""

    source: str
    allowed: bool
    reason: str
    required_action: str | None = None
    legal_basis: str | None = None


class CandidateLiveSource(ApiModel):
    """Candidate live-source option and its intended use."""

    name: str
    status: str
    use: str


class DataGovernanceResponse(ApiModel):
    """Response contract for data governance status."""

    status: Literal["ready"]
    market_region: str
    approved_for_current_stage: bool
    sources: list[SourceGovernance]
    production_rule: str
    candidate_live_sources: list[CandidateLiveSource]


class EngineWorkflowStep(ApiModel):
    """One step in the backend engine workflow."""

    step: str
    task: str
    current_backend: str


class EngineWorkflowResponse(ApiModel):
    """Response contract for the engine workflow endpoint."""

    status: Literal["ready"]
    workflow: list[EngineWorkflowStep]
    next_backend_increment: str


class EscoConceptResponse(ApiModel):
    """Normalized ESCO occupation or skill concept."""

    concept_type: Literal["occupation", "skill"]
    preferred_label: str
    concept_uri: str | None = None
    broader_group: str | None = None
    aliases: list[str]


class EscoNormalizeResponse(ApiModel):
    """Response contract for ESCO query normalization."""

    query: str
    source: str
    source_use: Literal["market_context_enrichment"]
    occupations: list[EscoConceptResponse]
    skills: list[EscoConceptResponse]
    expanded_terms: list[str]
