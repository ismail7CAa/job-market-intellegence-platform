"""FastAPI application for Job Market Intelligence Platform."""

import json
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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
from src.analytics.salary_analysis import SalaryAnomalyDetector
from src.database import init_database
from src.analytics.skill_demand import SkillDemandAnalyzer
from src.data_pipeline.pipeline import DataPipeline
from src.data_pipeline.models import JobPosting
from src.nlp.market_agent import MarketIntelligenceAgent
from src.nlp.query_processor import QueryProcessor
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
query_processor = QueryProcessor(currency=settings.default_currency)
market_agent = MarketIntelligenceAgent(salary_detector=salary_detector)
TRAINING_DATA_PATH = settings.training_data_path
PRODUCTION_DATA_PATH = settings.production_data_path


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
    frame = pd.read_csv(dataset_path, parse_dates=["posted_date"])
    jobs = []
    for record in frame.to_dict(orient="records"):
        jobs.append(
            JobPosting(
                id=str(record["id"]),
                title=record["title"],
                company=record["company"],
                location=record["location"],
                salary_min=record.get("salary_min"),
                salary_max=record.get("salary_max"),
                job_type=record.get("job_type", "Full-time"),
                description=record.get("description", ""),
                required_skills=[
                    skill.strip()
                    for skill in str(record.get("required_skills", "")).split(";")
                    if skill.strip()
                ],
                posted_date=record["posted_date"].to_pydatetime()
                if hasattr(record["posted_date"], "to_pydatetime")
                else record["posted_date"],
                source=record.get("source", "local_csv"),
            )
        )
    return jobs


def _ensure_pipeline_jobs_loaded() -> None:
    """Load local sample jobs when the in-memory pipeline is empty."""
    if pipeline.jobs:
        return
    if PRODUCTION_DATA_PATH.exists():
        pipeline.jobs = _load_jobs_from_csv(PRODUCTION_DATA_PATH)
        pipeline.processing_log.append({
            "source": "local_csv",
            "job_count": len(pipeline.jobs),
            "timestamp": datetime.now().isoformat(),
        })


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


@app.get("/")
async def root():
    """Portfolio dashboard for the live German market demo."""
    _ensure_pipeline_jobs_loaded()
    stats = pipeline.get_statistics()
    try:
        analysis = _ensure_skill_analysis_loaded()
        top_skills = analysis.get("top_skills", [])[:8]
    except Exception:
        analysis = {}
        top_skills = []

    try:
        role_payload = _get_role_prediction_payload(quarters_ahead=1)
        predicted_roles = role_payload.get("predicted_roles", [])[:5]
    except Exception as exc:
        logger.warning(f"Role forecast unavailable on dashboard: {exc}")
        predicted_roles = []

    jobs = _serialize_jobs(pipeline.jobs)
    anomalies = salary_detector.detect_anomalies(jobs)[:4] if jobs else []
    remote_jobs = sum(
        1
        for job in jobs
        if str(job.get("remote_status", "")).lower() == "remote"
    )
    hybrid_jobs = sum(
        1
        for job in jobs
        if str(job.get("remote_status", "")).lower() == "hybrid"
    )
    onsite_jobs = sum(
        1
        for job in jobs
        if str(job.get("remote_status", "")).lower() == "onsite"
    )

    salary_stats = stats.get("salary_stats", {})
    median_salary = int(salary_stats.get("median", 0)) if salary_stats else 0
    max_skill_demand = max(
        [skill.get("demand", 0) for skill in top_skills] or [1]
    )
    top_skill_rows = "".join(
        f"""
        <div class="skill-row">
          <div>
            <strong>{escape(str(skill.get("skill", "Unknown")))}</strong>
            <span>{skill.get("demand_percentage", 0):.1f}% of skill mentions</span>
          </div>
          <div class="skill-meter" aria-label="Demand for {escape(str(skill.get("skill", "Unknown")))}">
            <i style="width: {int((skill.get("demand", 0) / max_skill_demand) * 100)}%"></i>
          </div>
          <b>{skill.get("demand", 0)}</b>
        </div>
        """
        for skill in top_skills
    ) or """
        <div class="skill-row">
          <div><strong>No skill data loaded</strong><span>Run ingestion or load demo data</span></div>
          <div class="skill-meter"><i style="width: 0%"></i></div>
          <b>0</b>
        </div>
    """

    max_role_index = max(
        [role.get("projected_demand_index", 0) for role in predicted_roles] or [1]
    )
    role_rows = "".join(
        f"""
        <div class="role-row">
          <div>
            <strong>{escape(str(role.get("role", "Unknown role")))}</strong>
            <span>Confidence {role.get("confidence_score", 0):.2f}</span>
          </div>
          <div class="role-score">
            <i style="width: {int((role.get("projected_demand_index", 0) / max_role_index) * 100)}%"></i>
          </div>
          <b>{role.get("projected_demand_index", 0):.1f}</b>
        </div>
        """
        for role in predicted_roles
    ) or """
        <div class="role-row">
          <div><strong>Forecast unavailable</strong><span>Model output not loaded</span></div>
          <div class="role-score"><i style="width: 0%"></i></div>
          <b>0.0</b>
        </div>
    """

    anomaly_rows = "".join(
        f"""
        <tr>
          <td>{escape(str(item.get("title", "Unknown")))}</td>
          <td>{escape(str(item.get("location", "Unknown")))}</td>
          <td>{item.get("salary_avg", 0):,.0f} {settings.default_currency}</td>
          <td>{escape(", ".join(item.get("reasons", [])))}</td>
        </tr>
        """
        for item in anomalies
    ) or """
        <tr>
          <td colspan="4">No salary anomalies detected in the loaded dataset.</td>
        </tr>
    """

    city_counts = {}
    for job in jobs:
        location = str(job.get("location", "Unknown")).replace(", Germany", "")
        city_counts[location] = city_counts.get(location, 0) + 1
    city_rows = "".join(
        f"""
        <span class="city-pill">
          {escape(city)}
          <b>{count}</b>
        </span>
        """
        for city, count in sorted(city_counts.items(), key=lambda item: (-item[1], item[0]))
    )

    dashboard_payload = json.dumps(
        {
            "totalJobs": stats.get("total_jobs", 0),
            "locations": stats.get("locations", 0),
            "companies": stats.get("companies", 0),
            "uniqueSkills": stats.get("unique_skills", 0),
            "medianSalary": median_salary,
            "currency": settings.default_currency,
            "remoteJobs": remote_jobs,
            "hybridJobs": hybrid_jobs,
            "onsiteJobs": onsite_jobs,
        }
    )

    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>German Job Market Intelligence</title>
          <style>
            :root {{
              color-scheme: dark;
              --bg: #0b0f14;
              --surface: #111821;
              --surface-2: #17212c;
              --ink: #edf4f8;
              --muted: #9eb0bf;
              --line: #263544;
              --green: #3ddc97;
              --blue: #66a6ff;
              --amber: #f2b84b;
              --red: #ff6b6b;
              --white: #ffffff;
            }}
            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              background:
                radial-gradient(circle at top left, rgba(61, 220, 151, 0.12), transparent 28rem),
                linear-gradient(180deg, #0b0f14 0%, #0e141b 48%, #0b0f14 100%);
              color: var(--ink);
            }}
            a {{ color: inherit; text-decoration: none; }}
            main {{
              width: min(1280px, calc(100% - 28px));
              margin: 0 auto;
              padding: 22px 0 42px;
            }}
            .topbar {{
              display: flex;
              justify-content: space-between;
              align-items: center;
              gap: 18px;
              min-height: 60px;
              border-bottom: 1px solid var(--line);
            }}
            .brand {{
              display: flex;
              align-items: center;
              gap: 12px;
              font-weight: 800;
            }}
            .mark {{
              display: grid;
              place-items: center;
              width: 34px;
              height: 34px;
              border: 1px solid rgba(61, 220, 151, 0.55);
              background: rgba(61, 220, 151, 0.12);
              color: var(--green);
              font-size: 13px;
            }}
            .nav {{
              display: flex;
              align-items: center;
              gap: 10px;
              color: var(--muted);
              font-size: 14px;
            }}
            .nav a {{
              padding: 8px 10px;
              border: 1px solid transparent;
            }}
            .nav a:hover {{
              border-color: var(--line);
              color: var(--ink);
            }}
            .status-dot {{
              width: 8px;
              height: 8px;
              background: var(--green);
              border-radius: 50%;
              box-shadow: 0 0 0 4px rgba(61, 220, 151, 0.12);
            }}
            .hero-grid {{
              display: grid;
              grid-template-columns: minmax(0, 1fr) 420px;
              gap: 18px;
              padding: 26px 0 18px;
              align-items: stretch;
            }}
            .hero-panel {{
              min-height: 410px;
              display: flex;
              flex-direction: column;
              justify-content: space-between;
              padding: 28px;
              border: 1px solid var(--line);
              background:
                linear-gradient(135deg, rgba(102, 166, 255, 0.12), transparent 42%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.015));
            }}
            h1 {{
              margin: 0;
              max-width: 780px;
              font-size: clamp(44px, 7vw, 88px);
              line-height: 0.92;
              letter-spacing: 0;
            }}
            .eyebrow {{
              display: inline-flex;
              align-items: center;
              gap: 10px;
              width: fit-content;
              margin-bottom: 18px;
              padding: 7px 10px;
              border: 1px solid rgba(61, 220, 151, 0.35);
              background: rgba(61, 220, 151, 0.08);
              color: var(--green);
              font-size: 13px;
              font-weight: 700;
            }}
            .lede {{
              max-width: 720px;
              margin: 22px 0 0;
              color: var(--muted);
              font-size: 18px;
              line-height: 1.6;
            }}
            .actions {{
              display: flex;
              flex-wrap: wrap;
              gap: 12px;
              margin-top: 30px;
            }}
            .button {{
              display: inline-flex;
              align-items: center;
              justify-content: center;
              min-height: 42px;
              padding: 0 14px;
              border: 1px solid var(--line);
              background: var(--green);
              color: #06110c;
              font-weight: 700;
              font-size: 14px;
            }}
            .button.secondary {{
              background: transparent;
              color: var(--ink);
            }}
            .button.ghost {{
              background: var(--surface-2);
              color: var(--ink);
            }}
            .system-panel, .panel {{
              border: 1px solid var(--line);
              background: rgba(17, 24, 33, 0.86);
            }}
            .system-panel {{
              padding: 20px;
              display: grid;
              gap: 14px;
            }}
            .terminal {{
              min-height: 172px;
              padding: 16px;
              border: 1px solid var(--line);
              background: #070a0e;
              color: #c9f7df;
              font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
              font-size: 13px;
              line-height: 1.65;
            }}
            .terminal span {{ color: var(--muted); }}
            .mini-chart {{
              display: grid;
              grid-template-columns: repeat(14, 1fr);
              align-items: end;
              gap: 5px;
              height: 150px;
              padding: 16px;
              border: 1px solid var(--line);
              background: var(--surface);
            }}
            .mini-chart i {{
              display: block;
              background: linear-gradient(180deg, var(--blue), var(--green));
              min-height: 12px;
            }}
            .metric-strip {{
              display: grid;
              grid-template-columns: repeat(4, minmax(0, 1fr));
              gap: 12px;
              margin-bottom: 18px;
            }}
            .metric {{
              min-height: 122px;
              padding: 16px;
              border: 1px solid var(--line);
              background: var(--surface);
            }}
            .metric span, .panel-title span, .skill-row span, .role-row span {{
              display: block;
              color: var(--muted);
              font-size: 13px;
            }}
            .metric strong {{
              display: block;
              margin-top: 16px;
              font-size: 32px;
              letter-spacing: 0;
            }}
            .metric small {{
              display: block;
              margin-top: 8px;
              color: var(--muted);
            }}
            .dashboard-grid {{
              display: grid;
              grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
              gap: 12px;
            }}
            .panel {{
              padding: 18px;
              min-width: 0;
            }}
            .panel-title {{
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              gap: 16px;
              margin-bottom: 16px;
            }}
            h2 {{
              margin: 0;
              font-size: 20px;
              letter-spacing: 0;
            }}
            .skill-stack, .role-stack {{
              display: grid;
              gap: 10px;
            }}
            .skill-row, .role-row {{
              display: grid;
              grid-template-columns: minmax(120px, 1fr) minmax(110px, 0.7fr) 42px;
              align-items: center;
              gap: 14px;
              padding: 12px;
              border: 1px solid var(--line);
              background: rgba(255, 255, 255, 0.025);
            }}
            .skill-meter, .role-score {{
              height: 8px;
              background: #0a0f15;
              overflow: hidden;
            }}
            .skill-meter i, .role-score i {{
              display: block;
              height: 100%;
              background: var(--green);
            }}
            .role-score i {{ background: var(--blue); }}
            .market-layout {{
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 12px;
              margin-top: 12px;
            }}
            .work-mode {{
              display: grid;
              gap: 10px;
              padding: 14px;
              border: 1px solid var(--line);
              background: rgba(255, 255, 255, 0.025);
            }}
            .mode-track {{
              height: 12px;
              background: #0a0f15;
              display: flex;
              overflow: hidden;
            }}
            .mode-track i:nth-child(1) {{ background: var(--green); }}
            .mode-track i:nth-child(2) {{ background: var(--blue); }}
            .mode-track i:nth-child(3) {{ background: var(--amber); }}
            .city-cloud {{
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
            }}
            .city-pill {{
              display: inline-flex;
              align-items: center;
              gap: 8px;
              padding: 8px 10px;
              border: 1px solid var(--line);
              background: rgba(255, 255, 255, 0.035);
              color: var(--muted);
              font-size: 13px;
            }}
            .city-pill b {{ color: var(--ink); }}
            table {{
              width: 100%;
              border-collapse: collapse;
              font-size: 14px;
            }}
            th, td {{
              padding: 12px 10px;
              text-align: left;
              border-bottom: 1px solid var(--line);
            }}
            th {{
              color: var(--muted);
              font-size: 12px;
              text-transform: uppercase;
              font-weight: 700;
            }}
            .agent {{
              margin-top: 12px;
              display: grid;
              grid-template-columns: minmax(0, 1fr) 170px;
              gap: 10px;
            }}
            .agent input {{
              min-height: 44px;
              padding: 0 12px;
              border: 1px solid var(--line);
              background: #0a0f15;
              color: var(--ink);
              font: inherit;
            }}
            .agent-output {{
              margin-top: 12px;
              min-height: 84px;
              padding: 14px;
              border: 1px solid var(--line);
              background: #0a0f15;
              color: var(--muted);
              line-height: 1.55;
            }}
            .footer-band {{
              margin-top: 18px;
              padding: 18px;
              border: 1px solid var(--line);
              color: var(--muted);
              background: rgba(255, 255, 255, 0.025);
              display: flex;
              justify-content: space-between;
              gap: 18px;
              flex-wrap: wrap;
            }}
            @media (max-width: 980px) {{
              .hero-grid, .dashboard-grid, .market-layout {{
                grid-template-columns: 1fr;
              }}
              .metric-strip {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
              }}
            }}
            @media (max-width: 640px) {{
              main {{ width: min(100% - 20px, 1280px); padding-top: 12px; }}
              .topbar {{ align-items: flex-start; flex-direction: column; padding-bottom: 14px; }}
              .nav {{ flex-wrap: wrap; }}
              .hero-panel {{ padding: 18px; min-height: 360px; }}
              .metric-strip {{ grid-template-columns: 1fr; }}
              .skill-row, .role-row {{ grid-template-columns: 1fr; }}
              .agent {{ grid-template-columns: 1fr; }}
            }}
          </style>
        </head>
        <body>
          <main>
            <header class="topbar">
              <a class="brand" href="/">
                <span class="mark">DE</span>
                <span>German Job Market Intelligence</span>
              </a>
              <nav class="nav" aria-label="Primary">
                <span class="status-dot" aria-hidden="true"></span>
                <span>Live EC2 demo</span>
                <a href="/docs">API Docs</a>
                <a href="/health">Health</a>
                <a href="/stats/jobs">JSON</a>
              </nav>
            </header>

            <section class="hero-grid">
              <div class="hero-panel">
                <div>
                  <div class="eyebrow">AWS EC2 · FastAPI · Postgres · MLflow-ready</div>
                  <h1>German tech labor signals, modeled and explained.</h1>
                  <p class="lede">
                    A portfolio-grade data and ML platform for skill demand, salary anomalies,
                    role forecasts, and grounded market explanations across German tech roles.
                  </p>
                  <div class="actions">
                    <a class="button" href="/docs">Explore API</a>
                    <a class="button secondary" href="/agent/explain?question=Why%20is%20this%20salary%20anomalous%3F&job_id=prod_005">Agent Evidence</a>
                    <a class="button ghost" href="/predict/roles">Role Forecast</a>
                  </div>
                </div>
                <div class="footer-band">
                  <span>Dataset: reproducible German demo market</span>
                  <span>Currency: {settings.default_currency}</span>
                  <span>Region: {settings.market_region}</span>
                </div>
              </div>

              <aside class="system-panel" aria-label="System telemetry">
                <div class="terminal">
                  <span>$ curl /health</span><br>
                  status: connected<br>
                  database: postgres<br>
                  deploy: docker compose on ec2<br>
                  agent: grounded explanations ready
                </div>
                <div class="mini-chart" aria-label="Demand signal chart">
                  <i style="height: 36%"></i><i style="height: 48%"></i><i style="height: 42%"></i>
                  <i style="height: 58%"></i><i style="height: 62%"></i><i style="height: 54%"></i>
                  <i style="height: 74%"></i><i style="height: 66%"></i><i style="height: 80%"></i>
                  <i style="height: 72%"></i><i style="height: 88%"></i><i style="height: 84%"></i>
                  <i style="height: 92%"></i><i style="height: 96%"></i>
                </div>
              </aside>
            </section>

            <section class="metric-strip" aria-label="Market metrics">
              <div class="metric"><span>Jobs loaded</span><strong>{stats.get("total_jobs", 0)}</strong><small>validated postings</small></div>
              <div class="metric"><span>Median salary</span><strong>{median_salary:,}</strong><small>{settings.default_currency} annual midpoint</small></div>
              <div class="metric"><span>Locations</span><strong>{stats.get("locations", 0)}</strong><small>German hiring markets</small></div>
              <div class="metric"><span>Skills tracked</span><strong>{stats.get("unique_skills", 0)}</strong><small>normalized demand signals</small></div>
            </section>

            <section class="dashboard-grid">
              <article class="panel">
                <div class="panel-title">
                  <div>
                    <h2>Skill Demand</h2>
                    <span>Ranked by occurrence across loaded German tech roles</span>
                  </div>
                  <a class="button secondary" href="/trends/skills">Open JSON</a>
                </div>
                <div class="skill-stack">{top_skill_rows}</div>
              </article>

              <article class="panel">
                <div class="panel-title">
                  <div>
                    <h2>Role Forecast</h2>
                    <span>Model-backed projected demand index</span>
                  </div>
                  <a class="button secondary" href="/predict/roles">Endpoint</a>
                </div>
                <div class="role-stack">{role_rows}</div>
              </article>
            </section>

            <section class="dashboard-grid" style="margin-top: 12px;">
              <article class="panel">
                <div class="panel-title">
                  <div>
                    <h2>Salary Anomaly Watch</h2>
                    <span>Outliers detected from salary midpoint distributions</span>
                  </div>
                  <a class="button secondary" href="/salary/anomalies">Inspect</a>
                </div>
                <table>
                  <thead>
                    <tr><th>Role</th><th>Location</th><th>Salary Avg</th><th>Reason</th></tr>
                  </thead>
                  <tbody>{anomaly_rows}</tbody>
                </table>
              </article>

              <article class="panel">
                <div class="panel-title">
                  <div>
                    <h2>Market Coverage</h2>
                    <span>Locations and work-mode distribution in the demo dataset</span>
                  </div>
                </div>
                <div class="market-layout">
                  <div class="work-mode">
                    <strong>Work modes</strong>
                    <div class="mode-track" aria-label="Work mode distribution">
                      <i style="width: {remote_jobs * 10}%"></i>
                      <i style="width: {hybrid_jobs * 10}%"></i>
                      <i style="width: {onsite_jobs * 10}%"></i>
                    </div>
                    <span>Remote {remote_jobs} · Hybrid {hybrid_jobs} · Onsite {onsite_jobs}</span>
                  </div>
                  <div class="city-cloud">{city_rows}</div>
                </div>
              </article>
            </section>

            <section class="panel" style="margin-top: 12px;">
              <div class="panel-title">
                <div>
                  <h2>Ask the Market Agent</h2>
                  <span>Grounded answers from skill analytics, salary checks, role forecasts, and loaded job evidence</span>
                </div>
              </div>
              <form class="agent" id="agent-form">
                <input id="agent-question" name="question" value="What are the top 3 skills?" aria-label="Market question">
                <button class="button" type="submit">Ask Agent</button>
              </form>
              <div class="agent-output" id="agent-output">
                Ask a question about the German market dataset. The agent will answer from platform evidence.
              </div>
            </section>

            <footer class="footer-band">
              <span>Built with FastAPI, Pandera, scikit-learn, SQLAlchemy, Postgres, Docker, GHCR, and AWS EC2.</span>
              <span>Last refreshed {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
            </footer>
          </main>

          <script>
            window.dashboard = {dashboard_payload};
            const form = document.getElementById('agent-form');
            const output = document.getElementById('agent-output');
            form.addEventListener('submit', async (event) => {{
              event.preventDefault();
              const question = document.getElementById('agent-question').value.trim();
              if (!question) return;
              output.textContent = 'Thinking with platform evidence...';
              try {{
                const response = await fetch('/query?question=' + encodeURIComponent(question), {{ method: 'POST' }});
                const payload = await response.json();
                output.textContent = payload.answer || 'No answer returned.';
              }} catch (error) {{
                output.textContent = 'The agent could not answer right now. Check API health and try again.';
              }}
            }});
          </script>
        </body>
        </html>
        """
    )
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


@app.post("/query")
async def query_market(question: str):
    """Ask a natural language question about the job market.
    
    Args:
        question: Natural language question
        
    Returns:
        Answer to the question
    """
    analysis = _ensure_skill_analysis_loaded()
    anomalies = salary_detector.detect_anomalies(_serialize_jobs(pipeline.jobs))
    role_prediction = _get_role_prediction_payload(quarters_ahead=1)
    stats = pipeline.get_statistics()
    parsed_query = query_processor.process_query(question)
    subject = parsed_query["query"].get("subject") or ""

    return {
        "question": question,
        "parsed_query": parsed_query,
        "answer": query_processor.answer_question(
            question,
            context={
                "summary": f"Current dataset covers {stats['total_jobs']} jobs across {stats['locations']} locations.",
                "total_jobs": stats["total_jobs"],
                "remote_jobs": sum(
                    1
                    for job in _serialize_jobs(pipeline.jobs)
                    if str(job.get("remote_status", "")).lower() == "remote"
                ),
                "top_skills": analysis.get("top_skills", []),
                "anomalies": anomalies,
                "salary_range": salary_detector.get_salary_range(subject) if subject else {},
                "predicted_roles": role_prediction["predicted_roles"] if role_prediction else [],
            },
        ),
        "status": "ready",
    }


@app.post("/agent/explain")
async def explain_with_agent(question: str, job_id: str = None):
    """Ask the agent to explain an analytics or model output with evidence."""
    _ensure_pipeline_jobs_loaded()
    if not pipeline.jobs:
        raise HTTPException(status_code=400, detail="No job data available.")

    result = market_agent.answer(
        question=question,
        jobs=_serialize_jobs(pipeline.jobs),
        job_id=job_id,
    )
    return {
        "question": question,
        **result,
    }


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
