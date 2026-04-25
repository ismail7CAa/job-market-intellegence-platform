"""FastAPI application for Job Market Intelligence Platform."""

from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import API_HOST, API_PORT, BASE_DIR, DATABASE_URL, DEBUG, MLFLOW_REGISTERED_MODEL_NAME
from src.analytics.salary_analysis import SalaryAnomalyDetector
from src.database import init_database
from src.analytics.skill_demand import SkillDemandAnalyzer
from src.data_pipeline.pipeline import DataPipeline
from src.data_pipeline.models import JobPosting
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
    title="Job Market Intelligence Platform",
    description="Analyze job market trends, skill demand, and predict future roles",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
analyzer = SkillDemandAnalyzer()
pipeline = DataPipeline()
role_predictor = RolePredictor()
salary_detector = SalaryAnomalyDetector()
query_processor = QueryProcessor()
TRAINING_DATA_PATH = BASE_DIR / "data" / "job_postings_training.csv"
PRODUCTION_DATA_PATH = BASE_DIR / "data" / "job_postings_production.csv"


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
        top_n=10,
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
    """Root endpoint."""
    return {
        "message": "Welcome to Job Market Intelligence Platform",
        "status": "under deployment",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "trends": "/trends/skills",
            "predict": "/predict/roles",
            "query": "/query",
            "salary": "/salary/anomalies"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "connected" if _db else "disconnected"
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/data/fetch")
async def fetch_data(
    sources: list[str] = Query(["linkedin", "kaggle"]),
    keywords: list[str] = Query(["Python Developer", "Data Scientist"]),
    limit: int = Query(100, ge=10, le=1000)
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
    period: str = Query("30d", regex="^[0-9]+d$"),
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
