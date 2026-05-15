"""FastAPI application for Job Market Intelligence Platform."""

from datetime import datetime
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
    """Portfolio landing page for the live German market demo."""
    _ensure_pipeline_jobs_loaded()
    stats = pipeline.get_statistics()
    try:
        analysis = _ensure_skill_analysis_loaded()
        top_skills = analysis.get("top_skills", [])[:5]
    except Exception:
        top_skills = []

    salary_stats = stats.get("salary_stats", {})
    median_salary = int(salary_stats.get("median", 0)) if salary_stats else 0
    top_skill_rows = "".join(
        f"<li><span>{skill.get('skill', 'Unknown')}</span><strong>{skill.get('demand', 0)}</strong></li>"
        for skill in top_skills
    )
    if not top_skill_rows:
        top_skill_rows = "<li><span>No skill data loaded</span><strong>0</strong></li>"

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
              color-scheme: light;
              --ink: #17202a;
              --muted: #5d6875;
              --line: #d9e0e7;
              --panel: #f6f8fa;
              --accent: #0f766e;
              --accent-2: #b45309;
              --surface: #ffffff;
            }}
            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              background: var(--surface);
              color: var(--ink);
            }}
            main {{
              width: min(1120px, calc(100% - 32px));
              margin: 0 auto;
              padding: 48px 0;
            }}
            .hero {{
              display: grid;
              grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
              gap: 32px;
              align-items: center;
              min-height: 62vh;
            }}
            h1 {{
              margin: 0;
              max-width: 760px;
              font-size: clamp(40px, 7vw, 76px);
              line-height: 0.96;
              letter-spacing: 0;
            }}
            .lede {{
              max-width: 660px;
              margin: 22px 0 0;
              color: var(--muted);
              font-size: 19px;
              line-height: 1.6;
            }}
            .actions {{
              display: flex;
              flex-wrap: wrap;
              gap: 12px;
              margin-top: 28px;
            }}
            a {{
              color: inherit;
              text-decoration: none;
            }}
            .button {{
              display: inline-flex;
              align-items: center;
              min-height: 44px;
              padding: 0 16px;
              border: 1px solid var(--line);
              background: var(--ink);
              color: white;
              font-weight: 700;
            }}
            .button.secondary {{
              background: white;
              color: var(--ink);
            }}
            .snapshot {{
              border: 1px solid var(--line);
              background: var(--panel);
              padding: 22px;
            }}
            .metric-grid {{
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: 12px;
            }}
            .metric {{
              min-height: 108px;
              padding: 16px;
              background: white;
              border: 1px solid var(--line);
            }}
            .metric span {{
              display: block;
              color: var(--muted);
              font-size: 13px;
            }}
            .metric strong {{
              display: block;
              margin-top: 12px;
              font-size: 28px;
            }}
            section {{
              padding: 36px 0 0;
            }}
            h2 {{
              margin: 0 0 16px;
              font-size: 22px;
            }}
            .skill-list {{
              display: grid;
              gap: 10px;
              padding: 0;
              margin: 0;
              list-style: none;
            }}
            .skill-list li {{
              display: flex;
              justify-content: space-between;
              gap: 16px;
              padding: 12px 14px;
              border: 1px solid var(--line);
              background: white;
            }}
            .bars {{
              display: grid;
              gap: 12px;
              margin-top: 18px;
            }}
            .bar span {{
              display: block;
              margin-bottom: 6px;
              color: var(--muted);
              font-size: 13px;
            }}
            .track {{
              height: 14px;
              border: 1px solid var(--line);
              background: white;
            }}
            .fill {{
              height: 100%;
              background: var(--accent);
            }}
            .fill.alt {{
              background: var(--accent-2);
            }}
            @media (max-width: 780px) {{
              main {{ padding: 32px 0; }}
              .hero {{ grid-template-columns: 1fr; min-height: auto; }}
              .metric-grid {{ grid-template-columns: 1fr; }}
            }}
          </style>
        </head>
        <body>
          <main>
            <section class="hero">
              <div>
                <h1>German Job Market Intelligence</h1>
                <p class="lede">
                  A live FastAPI portfolio demo focused on Germany's tech hiring market:
                  skill demand, role forecasts, salary signals, and grounded explanations.
                </p>
                <div class="actions">
                  <a class="button" href="/docs">Open API Docs</a>
                  <a class="button secondary" href="/stats/jobs">View Job Stats</a>
                  <a class="button secondary" href="/trends/skills">Skill Trends JSON</a>
                </div>
              </div>
              <aside class="snapshot" aria-label="Market snapshot">
                <div class="metric-grid">
                  <div class="metric"><span>Market</span><strong>{settings.market_region}</strong></div>
                  <div class="metric"><span>Jobs loaded</span><strong>{stats.get("total_jobs", 0)}</strong></div>
                  <div class="metric"><span>Locations</span><strong>{stats.get("locations", 0)}</strong></div>
                  <div class="metric"><span>Median salary</span><strong>{median_salary:,} {settings.default_currency}</strong></div>
                </div>
                <section>
                  <h2>Top Skills</h2>
                  <ul class="skill-list">{top_skill_rows}</ul>
                </section>
                <section>
                  <h2>Demo Focus</h2>
                  <div class="bars">
                    <div class="bar"><span>Berlin and Munich tech roles</span><div class="track"><div class="fill" style="width: 86%"></div></div></div>
                    <div class="bar"><span>Cloud, data, and AI demand</span><div class="track"><div class="fill alt" style="width: 78%"></div></div></div>
                  </div>
                </section>
              </aside>
            </section>
          </main>
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
