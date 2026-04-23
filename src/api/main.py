"""FastAPI application for Job Market Intelligence Platform."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from datetime import datetime
import json

from config.settings import API_HOST, API_PORT, DEBUG, DATABASE_URL
from src.database import init_database, get_database, SkillRepository, SalaryRepository
from src.analytics.skill_demand import SkillDemandAnalyzer
from src.data_pipeline.pipeline import DataPipeline

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
        if not pipeline.jobs:
            raise HTTPException(
                status_code=400,
                detail="No job data available. Run /data/fetch first."
            )
        
        # Convert JobPosting objects to dicts
        jobs_data = [job.dict() if hasattr(job, 'dict') else job for job in pipeline.jobs]
        
        # Analyze
        analysis = analyzer.analyze_jobs(jobs_data)
        
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
    if not analyzer.skill_trends:
        raise HTTPException(
            status_code=400,
            detail="No skill trends available. Run /analyze/skills first."
        )
    
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
    if not analyzer.skill_trends:
        raise HTTPException(
            status_code=400,
            detail="No analysis data available. Run /analyze/skills first."
        )
    
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
    if not pipeline.jobs:
        raise HTTPException(
            status_code=400,
            detail="No job data available. Run /data/fetch first."
        )
    
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
    # Placeholder for role prediction model
    return {
        "message": "Role prediction model coming soon",
        "quarters_ahead": quarters_ahead,
        "status": "under development"
    }


@app.post("/query")
async def query_market(question: str):
    """Ask a natural language question about the job market.
    
    Args:
        question: Natural language question
        
    Returns:
        Answer to the question
    """
    # Placeholder for NLP query processor
    return {
        "question": question,
        "answer": "NLP query processor coming soon",
        "status": "under development"
    }


@app.get("/salary/anomalies")
async def get_salary_anomalies(role: str = None):
    """Get salary anomalies and statistical outliers.
    
    Args:
        role: Optional role filter
        
    Returns:
        List of salary anomalies
    """
    # Placeholder for salary anomaly detection
    return {
        "role": role,
        "anomalies": [],
        "message": "Salary anomaly detection coming soon",
        "status": "under development"
    }


@app.get("/report/skill-demand")
async def get_skill_report():
    """Get a comprehensive skill demand report.
    
    Returns:
        Formatted skill demand report
    """
    if not analyzer.skill_trends:
        raise HTTPException(
            status_code=400,
            detail="No analysis data available. Run /analyze/skills first."
        )
    
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
    if not analyzer.skill_trends:
        raise HTTPException(
            status_code=400,
            detail="No analysis data available. Run /analyze/skills first."
        )
    
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
    if not pipeline.jobs:
        return {
            "total_jobs": 0,
            "statistics": {}
        }
    
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

