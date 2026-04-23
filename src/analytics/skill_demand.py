"""Analysis module for tracking skill demand trends."""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import Counter
import statistics
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SkillDemandAnalyzer:
    """Track and analyze demand shifts for skills over time."""

    def __init__(self):
        """Initialize the skill demand analyzer."""
        self.skill_trends = {}
        self.job_data = []
        self.skill_salaries = {}

    def analyze_jobs(self, job_listings: List[Dict]) -> Dict:
        """Analyze skill demand from job listings.
        
        Args:
            job_listings: List of job posting dictionaries
            
        Returns:
            Dictionary with skill demand analysis
        """
        logger.info(f"Analyzing skill demand from {len(job_listings)} job listings")
        
        if not job_listings:
            logger.warning("No job listings provided")
            return {}
        
        self.job_data = job_listings
        
        # Extract all skills
        all_skills = []
        skill_salary_data = {}
        
        for job in job_listings:
            if isinstance(job, dict):
                skills = job.get('required_skills', [])
                salary_min = job.get('salary_min')
                salary_max = job.get('salary_max')
            else:
                # Handle JobPosting model
                skills = job.required_skills
                salary_min = job.salary_min
                salary_max = job.salary_max
            
            all_skills.extend(skills)
            
            # Track salaries by skill
            if salary_min and salary_max:
                avg_salary = (salary_min + salary_max) / 2
                for skill in skills:
                    if skill not in skill_salary_data:
                        skill_salary_data[skill] = []
                    skill_salary_data[skill].append(avg_salary)
        
        # Count skill occurrences
        skill_counts = Counter(all_skills)
        
        # Calculate statistics
        analysis = {
            "total_jobs": len(job_listings),
            "unique_skills": len(skill_counts),
            "skills": self._calculate_skill_stats(skill_counts, skill_salary_data),
            "top_skills": self._get_top_skills(skill_counts, skill_salary_data, top_n=20),
            "skill_categories": self._categorize_skills(skill_counts),
            "timestamp": datetime.now().isoformat()
        }
        
        self.skill_trends = analysis
        return analysis

    def _calculate_skill_stats(
        self, 
        skill_counts: Counter,
        skill_salaries: Dict[str, List[float]]
    ) -> Dict[str, Dict]:
        """Calculate detailed statistics for each skill.
        
        Args:
            skill_counts: Counter of skill occurrences
            skill_salaries: Salary data per skill
            
        Returns:
            Dictionary with detailed skill statistics
        """
        skills = {}
        
        for skill, count in skill_counts.items():
            salaries = skill_salaries.get(skill, [])
            
            if salaries:
                salary_stats = {
                    "min": min(salaries),
                    "max": max(salaries),
                    "mean": statistics.mean(salaries),
                    "median": statistics.median(salaries),
                    "stdev": statistics.stdev(salaries) if len(salaries) > 1 else 0
                }
            else:
                salary_stats = None
            
            skills[skill] = {
                "occurrences": count,
                "percentage": (count / sum(skill_counts.values())) * 100 if skill_counts else 0,
                "salary": salary_stats
            }
        
        return skills

    def _get_top_skills(
        self,
        skill_counts: Counter,
        skill_salaries: Dict[str, List[float]],
        top_n: int = 10
    ) -> List[Dict]:
        """Get top trending skills with details.
        
        Args:
            skill_counts: Counter of skill occurrences
            skill_salaries: Salary data per skill
            top_n: Number of top skills to return
            
        Returns:
            List of top skills with metadata
        """
        top_skills = []
        
        for skill, count in skill_counts.most_common(top_n):
            salaries = skill_salaries.get(skill, [])
            
            top_skills.append({
                "skill": skill,
                "demand": count,
                "demand_percentage": (count / sum(skill_counts.values())) * 100 if skill_counts else 0,
                "average_salary": statistics.mean(salaries) if salaries else None,
                "salary_range": {
                    "min": min(salaries),
                    "max": max(salaries)
                } if salaries else None
            })
        
        return top_skills

    def _categorize_skills(self, skill_counts: Counter) -> Dict[str, List[str]]:
        """Categorize skills into groups.
        
        Args:
            skill_counts: Counter of skill occurrences
            
        Returns:
            Dictionary with skill categories
        """
        categories = {
            "Programming Languages": [
                "Python", "Java", "JavaScript", "Go", "Rust", "C++", "C#", "PHP", "Ruby", "TypeScript"
            ],
            "Web Frameworks": [
                "Django", "FastAPI", "React", "Vue", "Angular", "Node.js", "Express", "Flask"
            ],
            "Data & Analytics": [
                "SQL", "Machine Learning", "Data Science", "Analytics", "Pandas", "NumPy", "Spark"
            ],
            "DevOps & Cloud": [
                "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Jenkins", "Terraform", "CI/CD"
            ],
            "Databases": [
                "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "MySQL", "DynamoDB"
            ]
        }
        
        categorized = {}
        for category, keywords in categories.items():
            matching_skills = [
                skill for skill in skill_counts.keys()
                if any(kw.lower() in skill.lower() for kw in keywords)
            ]
            if matching_skills:
                categorized[category] = matching_skills
        
        return categorized

    def calculate_skill_growth(
        self,
        current_demand: Dict,
        previous_demand: Dict = None,
        period_days: int = 30
    ) -> Dict[str, float]:
        """Calculate growth rate for skills.
        
        Args:
            current_demand: Current skill demand data
            previous_demand: Previous period skill demand data
            period_days: Days in the period
            
        Returns:
            Dictionary with skill growth rates
        """
        logger.info("Calculating skill growth rates")
        
        if not previous_demand:
            logger.warning("No previous demand data, unable to calculate growth")
            return {}
        
        growth_rates = {}
        
        for skill in current_demand:
            current_count = current_demand[skill].get('occurrences', 0)
            previous_count = previous_demand.get(skill, {}).get('occurrences', 0)
            
            if previous_count > 0:
                growth = ((current_count - previous_count) / previous_count) * 100
                growth_rates[skill] = growth
        
        return dict(sorted(growth_rates.items(), key=lambda x: x[1], reverse=True))

    def get_trending_skills(
        self,
        min_occurrences: int = 5,
        top_n: int = 10
    ) -> List[Dict]:
        """Get trending skills based on demand.
        
        Args:
            min_occurrences: Minimum occurrences to be considered trending
            top_n: Number of trending skills to return
            
        Returns:
            List of trending skills
        """
        if not self.skill_trends:
            logger.warning("No skill trends available, analyze jobs first")
            return []
        
        trending = [
            skill for skill in self.skill_trends.get('top_skills', [])
            if skill['demand'] >= min_occurrences
        ]
        
        return trending[:top_n]

    def get_salary_premium(self, skill: str) -> Optional[Dict]:
        """Calculate salary premium for a specific skill.
        
        Args:
            skill: Skill name
            
        Returns:
            Dictionary with salary premium information
        """
        if not self.skill_trends or 'skills' not in self.skill_trends:
            return None
        
        skill_data = self.skill_trends['skills'].get(skill)
        if not skill_data or not skill_data['salary']:
            return None
        
        # Calculate base salary (mean of all jobs)
        all_salaries = []
        for data in self.skill_trends['skills'].values():
            if data['salary']:
                all_salaries.append(data['salary']['mean'])
        
        if not all_salaries:
            return None
        
        base_salary = statistics.mean(all_salaries)
        skill_salary = skill_data['salary']['mean']
        premium = ((skill_salary - base_salary) / base_salary) * 100
        
        return {
            "skill": skill,
            "base_salary": base_salary,
            "skill_salary": skill_salary,
            "premium_percentage": premium,
            "premium_amount": skill_salary - base_salary
        }

    def get_related_skills(self, skill: str, co_occurrence_threshold: int = 2) -> List[str]:
        """Find skills that frequently appear together.
        
        Args:
            skill: Target skill
            co_occurrence_threshold: Minimum co-occurrences
            
        Returns:
            List of related skills
        """
        if not self.job_data:
            logger.warning("No job data available")
            return []
        
        co_occurrences = Counter()
        
        for job in self.job_data:
            skills = job.get('required_skills', []) if isinstance(job, dict) else job.required_skills
            if skill in skills:
                for other_skill in skills:
                    if other_skill != skill:
                        co_occurrences[other_skill] += 1
        
        related = [
            skill for skill, count in co_occurrences.items()
            if count >= co_occurrence_threshold
        ]
        
        return sorted(related, key=lambda s: co_occurrences[s], reverse=True)

    def export_to_dataframe(self) -> pd.DataFrame:
        """Export skill demand analysis to pandas DataFrame.
        
        Returns:
            DataFrame with skill analysis
        """
        if not self.skill_trends or 'top_skills' not in self.skill_trends:
            return pd.DataFrame()
        
        data = []
        for skill_info in self.skill_trends['top_skills']:
            row = {
                'skill': skill_info['skill'],
                'demand': skill_info['demand'],
                'demand_percentage': skill_info['demand_percentage'],
                'average_salary': skill_info['average_salary'],
                'salary_min': skill_info['salary_range']['min'] if skill_info['salary_range'] else None,
                'salary_max': skill_info['salary_range']['max'] if skill_info['salary_range'] else None
            }
            data.append(row)
        
        return pd.DataFrame(data)

    def generate_report(self) -> str:
        """Generate a human-readable skill demand report.
        
        Returns:
            Formatted report string
        """
        if not self.skill_trends:
            return "No analysis data available"
        
        report = []
        report.append("=" * 60)
        report.append("SKILL DEMAND ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 60)
        report.append(f"Total Jobs Analyzed: {self.skill_trends['total_jobs']}")
        report.append(f"Unique Skills Found: {self.skill_trends['unique_skills']}")
        report.append(f"Report Generated: {self.skill_trends['timestamp']}")
        report.append("")
        
        # Top Skills
        report.append("TOP 10 SKILLS BY DEMAND")
        report.append("-" * 60)
        for i, skill in enumerate(self.skill_trends['top_skills'][:10], 1):
            salary_str = ""
            if skill['average_salary']:
                salary_str = f" | Avg Salary: ${skill['average_salary']:,.0f}"
            report.append(
                f"{i:2}. {skill['skill']:30} | Demand: {skill['demand']:4} "
                f"({skill['demand_percentage']:5.1f}%){salary_str}"
            )
        report.append("")
        
        # Skill Categories
        if self.skill_trends['skill_categories']:
            report.append("SKILL CATEGORIES")
            report.append("-" * 60)
            for category, skills in self.skill_trends['skill_categories'].items():
                report.append(f"{category}: {', '.join(skills[:5])}")
                if len(skills) > 5:
                    report.append(f"  ... and {len(skills) - 5} more")
            report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)
