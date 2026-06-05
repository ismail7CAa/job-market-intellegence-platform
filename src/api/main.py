"""FastAPI application for Job Market Intelligence Platform."""

import json
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger
from sqlalchemy import text

from config.settings import (
    API_HOST,
    API_PORT,
    DATABASE_URL,
    DEBUG,
    MLFLOW_REGISTERED_MODEL_NAME,
    get_settings,
)
from src.api.schemas import (
    ApplyHandoff,
    DataGovernanceResponse,
    EngineWorkflowResponse,
    EscoNormalizeResponse,
    JobDetailResponse,
    JobSearchResponse,
    SearchFacetsResponse,
    SimilarJobsResponse,
)
from src.api.services.job_search import JobSearchService
from src.analytics.salary_analysis import SalaryAnomalyDetector
from src.database import init_database
from src.database.repository import JobPostingRepository
from src.analytics.skill_demand import SkillDemandAnalyzer
from src.data_pipeline.pipeline import DataPipeline
from src.data_pipeline.models import JobPosting
from src.data_pipeline.providers import JobSearchRequest, LocalCsvJobProvider
from src.data_pipeline.source_policy import evaluate_source, evaluate_sources
from src.market_context import EscoNormalizer
from src.prediction.role_predictor import RolePredictor

# Initialize database
try:
    _db = init_database(DATABASE_URL)
    _db.create_tables()
except Exception as e:
    logger.warning(f"Database initialization skipped: {str(e)}")
    _db = None

app = FastAPI(
    title="German Job Market Intelligence Platform",
    description="Analyze German tech job trends, skill demand, salaries, and role forecasts",
    version="0.1.0"
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
analyzer = SkillDemandAnalyzer()
pipeline = DataPipeline()
role_predictor = RolePredictor()
salary_detector = SalaryAnomalyDetector()
esco_normalizer = EscoNormalizer()
TRAINING_DATA_PATH = settings.training_data_path
PRODUCTION_DATA_PATH = settings.production_data_path
_job_repository = JobPostingRepository(_db.get_session()) if _db else None
_repository_seeded = False


def _serialize_jobs(jobs):
    """Serialize JobPosting objects consistently across Pydantic versions."""
    return [
        job.model_dump(mode="json") if hasattr(job, "model_dump")
        else job.dict() if hasattr(job, "dict")
        else job
        for job in jobs
    ]


def _load_jobs_from_csv(dataset_path: Path) -> list[JobPosting]:
    """Load sample jobs from a local CSV file."""
    provider = LocalCsvJobProvider(dataset_path)
    return provider.fetch(JobSearchRequest(keywords=[], limit=10_000))


def _ensure_pipeline_jobs_loaded() -> None:
    """Load local sample jobs when the in-memory pipeline is empty."""
    global _repository_seeded
    if pipeline.jobs:
        if _job_repository and not _repository_seeded:
            _job_repository.save_jobs(pipeline.jobs)
            _repository_seeded = True
        return
    if PRODUCTION_DATA_PATH.exists():
        pipeline.jobs = _load_jobs_from_csv(PRODUCTION_DATA_PATH)
        pipeline.processing_log.append({
            "source": "local_csv",
            "job_count": len(pipeline.jobs),
            "timestamp": datetime.now().isoformat(),
        })
        if _job_repository:
            _job_repository.save_jobs(pipeline.jobs)
            _repository_seeded = True


def _get_job_repository() -> JobPostingRepository | None:
    """Return the repository used by the job search service."""
    _ensure_pipeline_jobs_loaded()
    return _job_repository


def _ensure_skill_analysis_loaded() -> dict:
    """Ensure jobs and skill analysis are available for read endpoints."""
    _ensure_pipeline_jobs_loaded()
    if not pipeline.jobs:
        raise HTTPException(status_code=400, detail="No job data available.")
    job_dicts = _serialize_jobs(pipeline.jobs)
    if not analyzer.skill_trends:
        analysis = analyzer.analyze_jobs(job_dicts)
    else:
        analysis = analyzer.skill_trends
    return analysis


def _ensure_role_predictor_trained() -> None:
    """Train the role predictor on local data when needed."""
    if role_predictor.model is not None:
        return
    if not TRAINING_DATA_PATH.exists():
        raise HTTPException(status_code=500, detail="Training dataset not found.")
    training_frame = pd.read_csv(TRAINING_DATA_PATH)
    role_predictor.train(training_frame.to_dict(orient="records"))


def _get_loaded_job_dicts() -> list[dict]:
    """Return serialized jobs after loading the local fallback dataset if needed."""
    _ensure_pipeline_jobs_loaded()
    if _job_repository:
        return _job_repository.list_job_dicts()
    return _serialize_jobs(pipeline.jobs)


job_search_service = JobSearchService(
    jobs_loader=_get_loaded_job_dicts,
    repository_provider=_get_job_repository,
    esco_normalizer=esco_normalizer,
    currency=settings.default_currency,
    region=settings.market_region,
)


def _get_role_prediction_payload(quarters_ahead: int) -> dict:
    """Build a consistent role prediction response payload."""
    _ensure_pipeline_jobs_loaded()
    _ensure_role_predictor_trained()
    if not pipeline.jobs:
        raise HTTPException(status_code=400, detail="No job data available for role prediction.")

    predictions = role_predictor.forecast_role_demand(
        _serialize_jobs(pipeline.jobs),
        quarters_ahead=quarters_ahead,
        top_n=settings.role_prediction_top_n,
    )
    evaluation_metrics = {}
    if PRODUCTION_DATA_PATH.exists():
        evaluation_metrics, _ = role_predictor.evaluate(pd.read_csv(PRODUCTION_DATA_PATH))

    return {
        "quarters_ahead": quarters_ahead,
        "predicted_roles": predictions,
        "model_name": MLFLOW_REGISTERED_MODEL_NAME,
        "evaluation_metrics": evaluation_metrics,
        "status": "ready",
    }


def _render_search_dashboard() -> HTMLResponse:
    """Render the v1 job-search product experience."""
    search_payload = job_search_service.build_search_response(query="", limit=12)
    stats = pipeline.get_statistics()
    initial_payload = json.dumps(search_payload, default=str)
    total_jobs = stats.get("total_jobs", 0)
    total_companies = stats.get("companies", 0)
    total_locations = stats.get("locations", 0)
    salary_stats = stats.get("salary_stats", {})
    median_salary = int(salary_stats.get("median", 0)) if salary_stats else 0

    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Germany Job Search Intelligence</title>
          <style>
            :root {{
              color-scheme: light;
              --bg: #f6f7f8;
              --ink: #172026;
              --muted: #62707a;
              --line: #d9e0e5;
              --panel: #ffffff;
              --panel-soft: #eef4f1;
              --green: #126b4f;
              --blue: #235f9c;
              --amber: #9b6413;
              --danger: #9b2c2c;
            }}
            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              background: var(--bg);
              color: var(--ink);
              font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }}
            a {{ color: inherit; }}
            main {{
              width: min(1240px, calc(100% - 28px));
              margin: 0 auto;
              padding: 18px 0 34px;
            }}
            .topbar {{
              min-height: 58px;
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 16px;
              border-bottom: 1px solid var(--line);
            }}
            .brand {{
              display: flex;
              align-items: center;
              gap: 10px;
              text-decoration: none;
              font-weight: 800;
            }}
            .mark {{
              width: 34px;
              height: 34px;
              display: grid;
              place-items: center;
              border: 1px solid var(--green);
              color: var(--green);
              background: #e8f3ee;
              font-size: 13px;
            }}
            .nav {{
              display: flex;
              align-items: center;
              gap: 12px;
              color: var(--muted);
              font-size: 14px;
            }}
            .nav a {{
              text-decoration: none;
              padding: 8px 0;
            }}
            .intro {{
              padding: 24px 0 18px;
              display: grid;
              grid-template-columns: minmax(0, 1fr) 360px;
              gap: 18px;
              align-items: end;
            }}
            h1 {{
              margin: 0;
              max-width: 850px;
              font-size: clamp(38px, 6vw, 76px);
              line-height: 0.96;
              letter-spacing: 0;
            }}
            .lede {{
              max-width: 760px;
              margin: 18px 0 0;
              color: var(--muted);
              font-size: 18px;
              line-height: 1.55;
            }}
            .source-note {{
              padding: 16px;
              border: 1px solid var(--line);
              background: var(--panel-soft);
              color: #2d4f43;
              line-height: 1.45;
              font-size: 14px;
            }}
            .search-shell {{
              border: 1px solid var(--line);
              background: var(--panel);
              padding: 14px;
            }}
            .search-form {{
              display: grid;
              grid-template-columns: minmax(220px, 1fr) minmax(160px, 220px) 160px 128px;
              gap: 10px;
            }}
            label {{
              display: grid;
              gap: 6px;
              color: var(--muted);
              font-size: 12px;
              font-weight: 700;
              text-transform: uppercase;
            }}
            input, select, button {{
              min-height: 44px;
              border: 1px solid var(--line);
              background: #fff;
              color: var(--ink);
              font: inherit;
            }}
            input, select {{ padding: 0 12px; }}
            button {{
              align-self: end;
              background: var(--green);
              border-color: var(--green);
              color: #fff;
              font-weight: 800;
              cursor: pointer;
            }}
            .quick-row {{
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
              margin-top: 12px;
            }}
            .quick-row button {{
              min-height: 34px;
              padding: 0 10px;
              border-color: var(--line);
              background: #f9fbfa;
              color: var(--ink);
              font-size: 13px;
              font-weight: 700;
            }}
            .layout {{
              display: grid;
              grid-template-columns: minmax(0, 1fr) 330px;
              gap: 14px;
              margin-top: 14px;
              align-items: start;
            }}
            .summary {{
              display: grid;
              grid-template-columns: repeat(4, minmax(0, 1fr));
              gap: 10px;
              margin-top: 14px;
            }}
            .metric, .side-panel, .job-card {{
              border: 1px solid var(--line);
              background: var(--panel);
            }}
            .metric {{
              padding: 14px;
              min-height: 92px;
            }}
            .metric span, .job-meta, .pill, .muted {{
              color: var(--muted);
              font-size: 13px;
            }}
            .metric strong {{
              display: block;
              margin-top: 10px;
              font-size: 26px;
              letter-spacing: 0;
            }}
            .results-head {{
              display: flex;
              justify-content: space-between;
              align-items: center;
              gap: 12px;
              margin: 8px 0 10px;
            }}
            h2 {{
              margin: 0;
              font-size: 20px;
              letter-spacing: 0;
            }}
            .job-list {{
              display: grid;
              gap: 10px;
            }}
            .job-card {{
              padding: 16px;
              display: grid;
              gap: 12px;
            }}
            .job-top {{
              display: flex;
              justify-content: space-between;
              gap: 16px;
              align-items: start;
            }}
            .job-title {{
              margin: 0 0 4px;
              font-size: 19px;
            }}
            .salary {{
              text-align: right;
              min-width: 150px;
              color: var(--green);
              font-weight: 800;
            }}
            .job-desc {{
              margin: 0;
              color: #3d4a52;
              line-height: 1.5;
            }}
            .tags {{
              display: flex;
              gap: 6px;
              flex-wrap: wrap;
            }}
            .pill {{
              display: inline-flex;
              align-items: center;
              min-height: 28px;
              padding: 0 8px;
              border: 1px solid var(--line);
              background: #f8faf9;
            }}
            .job-actions {{
              display: flex;
              justify-content: space-between;
              gap: 10px;
              align-items: center;
              border-top: 1px solid var(--line);
              padding-top: 12px;
            }}
            .apply {{
              display: inline-flex;
              align-items: center;
              justify-content: center;
              min-height: 38px;
              padding: 0 12px;
              text-decoration: none;
              background: var(--blue);
              color: #fff;
              font-weight: 800;
            }}
            .side-stack {{
              display: grid;
              gap: 10px;
            }}
            .side-panel {{
              padding: 14px;
            }}
            .side-panel h3 {{
              margin: 0 0 10px;
              font-size: 16px;
            }}
            .rank-row {{
              display: flex;
              justify-content: space-between;
              gap: 12px;
              padding: 9px 0;
              border-bottom: 1px solid var(--line);
            }}
            .rank-row:last-child {{ border-bottom: 0; }}
            .governance {{
              border-left: 4px solid var(--amber);
              background: #fff8e9;
            }}
            .empty {{
              padding: 28px;
              border: 1px solid var(--line);
              background: var(--panel);
              color: var(--muted);
            }}
            @media (max-width: 940px) {{
              .intro, .layout, .search-form {{
                grid-template-columns: 1fr;
              }}
              .summary {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
              }}
              button {{ align-self: stretch; }}
            }}
            @media (max-width: 620px) {{
              main {{ width: min(100% - 18px, 1240px); padding-top: 10px; }}
              .topbar {{ align-items: flex-start; flex-direction: column; padding-bottom: 12px; }}
              .nav {{ flex-wrap: wrap; }}
              .summary {{ grid-template-columns: 1fr; }}
              .job-top, .job-actions {{ flex-direction: column; }}
              .salary {{ text-align: left; }}
            }}
          </style>
        </head>
        <body>
          <main>
            <header class="topbar">
              <a class="brand" href="/">
                <span class="mark">DE</span>
                <span>Germany Job Search Intelligence</span>
              </a>
              <nav class="nav" aria-label="Primary">
                <a href="/jobs/search">Search API</a>
                <a href="/stats/jobs">Stats</a>
                <a href="/docs">API Docs</a>
                <a href="/health">Health</a>
              </nav>
            </header>

            <section class="intro">
              <div>
                <h1>Search jobs in Germany and understand the market around them.</h1>
                <p class="lede">
                  Find related roles across professions, compare listed salaries, see hiring companies,
                  and open a source or apply link when the data provides one.
                </p>
              </div>
              <aside class="source-note">
                Data policy: v1 runs on legal local demo data. The production engine must use official APIs,
                licensed job-data providers, or company feeds with explicit permission.
              </aside>
            </section>

            <section class="search-shell" aria-label="Job search">
              <form class="search-form" id="search-form">
                <label>
                  Job or keyword
                  <input id="query" name="q" value="" placeholder="Nurse, Marketing Manager, Data Analyst">
                </label>
                <label>
                  Location
                  <input id="location" name="location" placeholder="Berlin, Munich, Cologne">
                </label>
                <label>
                  Work mode
                  <select id="work-mode" name="work_mode">
                    <option value="any">Any</option>
                    <option value="remote">Remote</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="onsite">Onsite</option>
                  </select>
                </label>
                <button type="submit">Search</button>
              </form>
              <div class="quick-row" aria-label="Example searches">
                <button type="button" data-query="Nurse">Nurse</button>
                <button type="button" data-query="Marketing Manager">Marketing Manager</button>
                <button type="button" data-query="Warehouse">Warehouse</button>
                <button type="button" data-query="Accountant">Accountant</button>
                <button type="button" data-query="Data Analyst">Data Analyst</button>
              </div>
            </section>

            <section class="summary" aria-label="Platform coverage">
              <div class="metric"><span>Jobs indexed</span><strong>{total_jobs}</strong></div>
              <div class="metric"><span>Companies</span><strong>{total_companies}</strong></div>
              <div class="metric"><span>German locations</span><strong>{total_locations}</strong></div>
              <div class="metric"><span>Median listed salary</span><strong>{median_salary:,}</strong><span>{settings.default_currency}</span></div>
            </section>

            <section class="layout">
              <div>
                <div class="results-head">
                  <h2 id="results-title">All indexed jobs</h2>
                  <span class="muted" id="results-count"></span>
                </div>
                <div class="job-list" id="job-list"></div>
              </div>
              <aside class="side-stack">
                <section class="side-panel">
                  <h3>Search intelligence</h3>
                  <div class="rank-row"><span>Average salary</span><strong id="avg-salary">-</strong></div>
                  <div class="rank-row"><span>Salary samples</span><strong id="salary-samples">0</strong></div>
                  <div class="rank-row"><span>Apply links</span><strong id="apply-links">0</strong></div>
                </section>
                <section class="side-panel">
                  <h3>Top companies</h3>
                  <div id="top-companies"></div>
                </section>
                <section class="side-panel">
                  <h3>Top locations</h3>
                  <div id="top-locations"></div>
                </section>
                <section class="side-panel governance">
                  <h3>Legal data guardrails</h3>
                  <p class="muted" id="legal-position"></p>
                </section>
              </aside>
            </section>
          </main>

          <script>
            const initialPayload = {initial_payload};
            const form = document.getElementById('search-form');
            const queryInput = document.getElementById('query');
            const locationInput = document.getElementById('location');
            const workModeInput = document.getElementById('work-mode');
            const jobList = document.getElementById('job-list');
            const countLabel = document.getElementById('results-count');
            const titleLabel = document.getElementById('results-title');
            const avgSalary = document.getElementById('avg-salary');
            const salarySamples = document.getElementById('salary-samples');
            const applyLinks = document.getElementById('apply-links');
            const topCompanies = document.getElementById('top-companies');
            const topLocations = document.getElementById('top-locations');
            const legalPosition = document.getElementById('legal-position');

            function escapeHtml(value) {{
              return String(value ?? '').replace(/[&<>"']/g, (char) => ({{
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
              }}[char]));
            }}

            function renderRankRows(rows, emptyText) {{
              if (!rows || rows.length === 0) {{
                return `<div class="muted">${{emptyText}}</div>`;
              }}
              return rows.map(([name, count]) => `
                <div class="rank-row"><span>${{escapeHtml(name)}}</span><strong>${{count}}</strong></div>
              `).join('');
            }}

            function renderJobs(payload) {{
              const jobs = payload.jobs || [];
              countLabel.textContent = `${{payload.count}} matching jobs`;
              titleLabel.textContent = payload.query ? `Results for "${{payload.query}}"` : 'All indexed jobs';
              avgSalary.textContent = payload.summary.average_salary
                ? `${{Math.round(payload.summary.average_salary).toLocaleString('en-US')}} EUR`
                : '-';
              salarySamples.textContent = payload.summary.salary_sample_size || 0;
              applyLinks.textContent = payload.summary.apply_links_available || 0;
              topCompanies.innerHTML = renderRankRows(payload.summary.top_companies, 'No companies for this search.');
              topLocations.innerHTML = renderRankRows(payload.summary.top_locations, 'No locations for this search.');
              legalPosition.textContent = payload.data_governance.legal_position;

              if (jobs.length === 0) {{
                jobList.innerHTML = '<div class="empty">No matching jobs found in the loaded dataset. Try a broader profession or remove filters.</div>';
                return;
              }}

              jobList.innerHTML = jobs.map((job) => `
                <article class="job-card">
                  <div class="job-top">
                    <div>
                      <h3 class="job-title">${{escapeHtml(job.title)}}</h3>
                      <div class="job-meta">${{escapeHtml(job.company)}} · ${{escapeHtml(job.location)}} · ${{escapeHtml(job.remote_status || 'work mode unknown')}}</div>
                    </div>
                    <div class="salary">${{escapeHtml(job.salary_label)}}</div>
                  </div>
                  <p class="job-desc">${{escapeHtml(job.description)}}</p>
                  <div class="tags">
                    ${{(job.required_skills || []).slice(0, 5).map((skill) => `<span class="pill">${{escapeHtml(skill)}}</span>`).join('')}}
                    ${{job.role_type ? `<span class="pill">${{escapeHtml(job.role_type)}}</span>` : ''}}
                  </div>
                  <div class="job-actions">
                    <span class="muted">${{escapeHtml(job.source)}} · ${{escapeHtml(job.source_legal_basis || 'source policy not set')}}</span>
                    <a class="apply" href="${{escapeHtml(job.apply_endpoint)}}" target="_blank" rel="noopener noreferrer">Apply</a>
                  </div>
                </article>
              `).join('');
            }}

            async function runSearch() {{
              const params = new URLSearchParams();
              params.set('q', queryInput.value.trim());
              if (locationInput.value.trim()) params.set('location', locationInput.value.trim());
              params.set('work_mode', workModeInput.value);
              params.set('limit', '25');
              const response = await fetch('/jobs/search?' + params.toString());
              const payload = await response.json();
              renderJobs(payload);
            }}

            form.addEventListener('submit', async (event) => {{
              event.preventDefault();
              await runSearch();
            }});

            document.querySelectorAll('[data-query]').forEach((button) => {{
              button.addEventListener('click', async () => {{
                queryInput.value = button.dataset.query;
                await runSearch();
              }});
            }});

            renderJobs(initialPayload);
          </script>
        </body>
        </html>
        """
    )


@app.get("/")
async def root():
    """Germany-wide job search homepage."""
    return _render_search_dashboard()


@app.get("/jobs/search", response_model=JobSearchResponse)
async def search_jobs(
    q: str = Query("", description="Job title, keyword, company, skill, or profession"),
    location: str | None = Query(None, description="German city or region filter"),
    work_mode: str | None = Query(None, description="remote, hybrid, onsite, or any"),
    company: str | None = Query(None, description="Company-name filter"),
    role_type: str | None = Query(None, description="Role category filter"),
    salary_min: float | None = Query(None, ge=0, description="Minimum salary midpoint filter"),
    salary_max: float | None = Query(None, ge=0, description="Maximum salary midpoint filter"),
    employment_type: str | None = Query(None, description="Employment type filter"),
    sort: str = Query(
        "relevance",
        description="Sort by relevance, salary_desc, salary_asc, posted_desc, posted_asc, company, or title",
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=100, description="Deprecated alias for per_page"),
):
    """Search Germany-focused job data with salary, company, and apply-link context."""
    return job_search_service.build_search_response(
        query=q,
        location=location,
        work_mode=work_mode,
        company=company,
        role_type=role_type,
        salary_min=salary_min,
        salary_max=salary_max,
        employment_type=employment_type,
        sort=sort,
        page=page,
        per_page=limit or per_page,
    )


@app.get("/jobs/search/facets", response_model=SearchFacetsResponse)
async def get_search_facets():
    """Return available filters for the current job index."""
    return job_search_service.build_search_facets()


@app.get("/market/esco/normalize", response_model=EscoNormalizeResponse)
async def normalize_esco_query(
    q: str = Query(..., min_length=1, description="Occupation, skill, or job-search phrase"),
):
    """Normalize a query with ESCO occupation and skill context."""
    return esco_normalizer.normalize_query(q)


@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(job_id: str):
    """Return full job detail for a result page."""
    job = job_search_service.find_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job_search_service.build_job_detail(job)


@app.get("/jobs/{job_id}/similar", response_model=SimilarJobsResponse)
async def get_similar_jobs(
    job_id: str,
    limit: int = Query(5, ge=1, le=20),
):
    """Return jobs related to the selected posting."""
    job = job_search_service.find_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job_search_service.build_similar_jobs(job, limit=limit)


@app.get("/jobs/{job_id}/apply", response_model=ApplyHandoff)
async def apply_to_job(
    job_id: str,
    redirect: bool = Query(True, description="Redirect to apply URL when true; return JSON handoff when false."),
):
    """Send a candidate to the best legal apply/source page for a job."""
    job = job_search_service.find_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    handoff = job_search_service.build_apply_handoff(job)
    if not handoff["source_allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Apply handoff blocked because the job source is not approved.",
                "job_id": job_id,
                "source": handoff["source"],
            },
        )

    if redirect:
        return RedirectResponse(url=handoff["apply_url"], status_code=307)
    return handoff


@app.get("/data/governance", response_model=DataGovernanceResponse)
async def get_data_governance():
    """Return legal-source governance for the currently loaded job data."""
    return job_search_service.build_data_governance_report()


@app.get("/engine/workflow", response_model=EngineWorkflowResponse)
async def get_engine_workflow():
    """Return the platform workflow from search intent to apply handoff."""
    return job_search_service.build_engine_workflow()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "disconnected"
    if _db:
        try:
            with _db.get_session() as session:
                session.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as exc:
            logger.warning(f"Database health check failed: {exc}")
            db_status = "unhealthy"
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/data/fetch")
async def fetch_data(
    sources: list[str] = Query(settings.default_sources),
    keywords: list[str] = Query(settings.default_keywords),
    limit: int = Query(settings.default_limit_per_source, ge=10, le=1000)
):
    """Fetch job data from configured sources.
    
    Args:
        sources: Data sources (linkedin, kaggle)
        keywords: Search keywords
        limit: Maximum jobs per source
        
    Returns:
        Pipeline execution result with statistics
    """
    try:
        decisions = evaluate_sources(sources)
        blocked = [decision for decision in decisions if not decision.allowed]
        if blocked:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Live ingestion blocked by data-source governance.",
                    "blocked_sources": [
                        {
                            "source": decision.source,
                            "reason": decision.reason,
                            "required_action": decision.required_action,
                        }
                        for decision in blocked
                    ],
                    "allowed_sources": [
                        "legal_demo_csv",
                        "licensed_provider",
                        "company_feed",
                        "official_api",
                    ],
                },
            )

        logger.info(f"Fetching data from {sources}")
        jobs = pipeline.run(
            sources=sources,
            keywords=keywords,
            limit_per_source=limit
        )
        
        stats = pipeline.get_statistics()
        
        return {
            "success": True,
            "total_jobs": len(jobs),
            "statistics": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/skills")
async def analyze_skill_demand(
    min_occurrences: int = Query(5, ge=1),
    top_n: int = Query(20, ge=1, le=100)
):
    """Analyze skill demand from fetched job data.
    
    Args:
        min_occurrences: Minimum skill occurrences
        top_n: Top N skills to return
        
    Returns:
        Skill demand analysis results
    """
    try:
        analysis = _ensure_skill_analysis_loaded()
        
        if not analysis:
            raise HTTPException(status_code=500, detail="Analysis failed")
        
        return {
            "total_jobs": analysis.get("total_jobs", 0),
            "unique_skills": analysis.get("unique_skills", 0),
            "top_skills": analysis.get("top_skills", [])[:top_n],
            "skill_categories": analysis.get("skill_categories", {}),
            "timestamp": analysis.get("timestamp")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Skill analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/skills")
async def get_skill_trends(
    period: str = Query("30d", pattern="^[0-9]+d$"),
    limit: int = Query(10, ge=1, le=100)
):
    """Get trending skills for a given period.
    
    Args:
        period: Time period (e.g., 30d, 60d)
        limit: Maximum number of skills to return
        
    Returns:
        List of trending skills with demand metrics
    """
    _ensure_skill_analysis_loaded()
    trending = analyzer.get_trending_skills(top_n=limit)
    
    return {
        "period": period,
        "trending_skills": trending,
        "count": len(trending),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/skills/{skill_name}/salary-premium")
async def get_skill_salary_premium(skill_name: str):
    """Get salary premium for a specific skill.
    
    Args:
        skill_name: Name of the skill
        
    Returns:
        Salary premium analysis for the skill
    """
    _ensure_skill_analysis_loaded()
    premium = analyzer.get_salary_premium(skill_name)
    
    if not premium:
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{skill_name}' not found or has no salary data"
        )
    
    return premium


@app.get("/skills/{skill_name}/related")
async def get_related_skills(
    skill_name: str,
    min_co_occurrence: int = Query(2, ge=1)
):
    """Get skills that frequently appear with a target skill.
    
    Args:
        skill_name: Target skill name
        min_co_occurrence: Minimum co-occurrences
        
    Returns:
        List of related skills
    """
    _ensure_skill_analysis_loaded()
    related = analyzer.get_related_skills(skill_name, min_co_occurrence)
    
    return {
        "skill": skill_name,
        "related_skills": related,
        "count": len(related)
    }


@app.get("/predict/roles")
async def predict_roles(
    quarters_ahead: int = Query(1, ge=1, le=4)
):
    """Get predicted in-demand roles for future quarters.
    
    Args:
        quarters_ahead: Number of quarters to predict
        
    Returns:
        Predicted roles with confidence scores
    """
    return _get_role_prediction_payload(quarters_ahead)


@app.get("/salary/anomalies")
async def get_salary_anomalies(role: str = None):
    """Get salary anomalies and statistical outliers.
    
    Args:
        role: Optional role filter
        
    Returns:
        List of salary anomalies
    """
    _ensure_pipeline_jobs_loaded()
    jobs = _serialize_jobs(pipeline.jobs)
    filtered_jobs = jobs
    if role:
        filtered_jobs = [
            job for job in jobs
            if role.lower() in job.get("title", "").lower()
        ]

    anomalies = salary_detector.detect_anomalies(filtered_jobs)
    salary_range = salary_detector.get_salary_range(role) if role else None

    return {
        "role": role,
        "salary_range": salary_range,
        "anomalies": anomalies,
        "count": len(anomalies),
        "status": "ready",
    }


@app.get("/report/skill-demand")
async def get_skill_report():
    """Get a comprehensive skill demand report.
    
    Returns:
        Formatted skill demand report
    """
    _ensure_skill_analysis_loaded()
    report = analyzer.generate_report()
    
    return {
        "report": report,
        "format": "text"
    }


@app.get("/export/skills-csv")
async def export_skills_csv():
    """Export skill demand analysis as CSV.
    
    Returns:
        CSV formatted skill data
    """
    _ensure_skill_analysis_loaded()
    df = analyzer.export_to_dataframe()
    
    return {
        "data": df.to_csv(index=False),
        "format": "csv",
        "rows": len(df)
    }


@app.get("/status/pipeline")
async def get_pipeline_status():
    """Get data pipeline status and statistics.
    
    Returns:
        Pipeline status and metrics
    """
    _ensure_pipeline_jobs_loaded()
    return {
        "jobs_loaded": len(pipeline.jobs),
        "processing_log": pipeline.processing_log,
        "last_update": datetime.now().isoformat()
    }


@app.get("/stats/jobs")
async def get_job_statistics():
    """Get statistics about loaded jobs.
    
    Returns:
        Job statistics
    """
    _ensure_pipeline_jobs_loaded()
    stats = pipeline.get_statistics()
    
    return {
        "total_jobs": stats.get('total_jobs', 0),
        "locations": stats.get('locations', 0),
        "companies": stats.get('companies', 0),
        "unique_skills": stats.get('unique_skills', 0),
        "salary_stats": stats.get('salary_stats', {}),
        "top_skills": stats.get('top_skills', [])[:5]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG
    )
