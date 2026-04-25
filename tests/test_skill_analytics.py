"""Tests for skill demand analysis."""

from datetime import datetime

import pytest

from src.analytics.skill_demand import SkillDemandAnalyzer
from src.data_pipeline.models import JobPosting


def _dump_jobs(sample_jobs):
    """Serialize Pydantic jobs compatibly across versions."""
    return [
        job.model_dump(mode="json") if hasattr(job, "model_dump") else job.dict()
        for job in sample_jobs
    ]


class TestSkillDemandAnalyzer:
    """Test suite for SkillDemandAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return SkillDemandAnalyzer()
    
    @pytest.fixture
    def sample_jobs(self):
        """Create sample job postings."""
        return [
            JobPosting(
                id="job_1",
                title="Python Developer",
                company="TechCorp",
                location="San Francisco, CA",
                salary_min=100000,
                salary_max=150000,
                job_type="Full-time",
                description="Senior Python developer role",
                required_skills=["Python", "FastAPI", "PostgreSQL"],
                posted_date=datetime.now(),
                source="linkedin"
            ),
            JobPosting(
                id="job_2",
                title="Data Scientist",
                company="DataCorp",
                location="New York, NY",
                salary_min=120000,
                salary_max=180000,
                job_type="Full-time",
                description="Data science position",
                required_skills=["Python", "Machine Learning", "SQL"],
                posted_date=datetime.now(),
                source="linkedin"
            ),
            JobPosting(
                id="job_3",
                title="DevOps Engineer",
                company="CloudCorp",
                location="Austin, TX",
                salary_min=110000,
                salary_max=160000,
                job_type="Full-time",
                description="Infrastructure engineer",
                required_skills=["Docker", "Kubernetes", "AWS"],
                posted_date=datetime.now(),
                source="kaggle"
            ),
            JobPosting(
                id="job_4",
                title="Backend Engineer",
                company="TechCorp",
                location="San Francisco, CA",
                salary_min=130000,
                salary_max=180000,
                job_type="Full-time",
                description="Backend development role",
                required_skills=["Python", "Docker", "PostgreSQL"],
                posted_date=datetime.now(),
                source="linkedin"
            ),
        ]
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.skill_trends == {}
        assert analyzer.job_data == []
    
    def test_analyze_jobs(self, analyzer, sample_jobs):
        """Test job analysis."""
        result = analyzer.analyze_jobs(_dump_jobs(sample_jobs))
        
        assert result['total_jobs'] == 4
        assert result['unique_skills'] > 0
        assert 'top_skills' in result
        assert len(result['top_skills']) > 0
    
    def test_top_skills(self, analyzer, sample_jobs):
        """Test getting top skills."""
        analyzer.analyze_jobs(_dump_jobs(sample_jobs))
        top_skills = analyzer.get_trending_skills(top_n=5)
        
        assert len(top_skills) <= 5
        assert all('skill' in skill for skill in top_skills)
        assert all('demand' in skill for skill in top_skills)
    
    def test_salary_premium(self, analyzer, sample_jobs):
        """Test salary premium calculation."""
        analyzer.analyze_jobs(_dump_jobs(sample_jobs))
        
        premium = analyzer.get_salary_premium("Python")
        
        assert premium is not None
        assert 'premium_percentage' in premium
        assert 'skill_salary' in premium
        assert 'base_salary' in premium
    
    def test_related_skills(self, analyzer, sample_jobs):
        """Test finding related skills."""
        analyzer.analyze_jobs(_dump_jobs(sample_jobs))
        
        related = analyzer.get_related_skills("Python", co_occurrence_threshold=1)
        
        assert len(related) > 0
        assert "Python" not in related
    
    def test_skill_categorization(self, analyzer, sample_jobs):
        """Test skill categorization."""
        result = analyzer.analyze_jobs(_dump_jobs(sample_jobs))
        categories = result.get('skill_categories', {})
        
        assert len(categories) > 0
    
    def test_export_to_dataframe(self, analyzer, sample_jobs):
        """Test DataFrame export."""
        analyzer.analyze_jobs(_dump_jobs(sample_jobs))
        df = analyzer.export_to_dataframe()
        
        assert len(df) > 0
        assert 'skill' in df.columns
        assert 'demand' in df.columns
    
    def test_report_generation(self, analyzer, sample_jobs):
        """Test report generation."""
        analyzer.analyze_jobs(_dump_jobs(sample_jobs))
        report = analyzer.generate_report()
        
        assert isinstance(report, str)
        assert "SKILL DEMAND ANALYSIS REPORT" in report
        assert "TOP 10 SKILLS BY DEMAND" in report
    
    def test_empty_job_list(self, analyzer):
        """Test handling empty job list."""
        result = analyzer.analyze_jobs([])
        
        assert result == {}
    
    def test_analyze_with_missing_skills(self, analyzer):
        """Test analysis with jobs missing skills."""
        jobs = [
            {
                "title": "Job 1",
                "company": "Corp",
                "location": "City",
                "required_skills": ["Python", "Docker"],
                "salary_min": 100000,
                "salary_max": 150000
            },
            {
                "title": "Job 2",
                "company": "Corp",
                "location": "City",
                # No required_skills key
                "salary_min": 100000,
                "salary_max": 150000
            }
        ]
        
        result = analyzer.analyze_jobs(jobs)
        
        assert result['total_jobs'] == 2
        assert result['unique_skills'] == 2


class TestSkillStatistics:
    """Test skill statistics calculations."""
    
    def test_skill_salary_stats(self):
        """Test salary statistics per skill."""
        analyzer = SkillDemandAnalyzer()
        jobs = [
            {
                "title": "Role 1",
                "company": "Corp",
                "location": "City",
                "required_skills": ["Python"],
                "salary_min": 100000,
                "salary_max": 120000
            },
            {
                "title": "Role 2",
                "company": "Corp",
                "location": "City",
                "required_skills": ["Python"],
                "salary_min": 130000,
                "salary_max": 150000
            },
        ]
        
        result = analyzer.analyze_jobs(jobs)
        python_data = result['skills']['Python']
        
        assert python_data['occurrences'] == 2
        assert python_data['salary'] is not None
        assert python_data['salary']['mean'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
