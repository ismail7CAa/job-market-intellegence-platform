"""Module for detecting salary anomalies."""

from __future__ import annotations

import logging
from collections import defaultdict
from statistics import median
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SalaryAnomalyDetector:
    """Detect unusual salary patterns and outliers."""

    def __init__(self):
        """Initialize the salary anomaly detector."""
        self.salary_stats = {}
        self._all_salaries = []

    @staticmethod
    def _average_salary(job: Dict) -> Optional[float]:
        """Return the midpoint salary when both bounds are available."""
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        if salary_min is None or salary_max is None:
            return None
        return (float(salary_min) + float(salary_max)) / 2

    @staticmethod
    def _quantile(sorted_values: List[float], fraction: float) -> float:
        """Calculate a simple quantile for a small numeric sample."""
        if not sorted_values:
            return 0.0
        index = int((len(sorted_values) - 1) * fraction)
        return sorted_values[index]

    def detect_anomalies(self, job_listings: List[Dict]) -> List[Dict]:
        """Identify salary anomalies in job postings."""
        logger.info(f"Detecting salary anomalies in {len(job_listings)} listings")
        role_salaries = defaultdict(list)
        anomalies = []

        for job in job_listings:
            average_salary = self._average_salary(job)
            if average_salary is None:
                continue
            role_salaries[job.get("title", "Unknown Role")].append(average_salary)

        self._all_salaries = [
            salary
            for salaries in role_salaries.values()
            for salary in salaries
        ]

        self.salary_stats = {}
        for role, salaries in role_salaries.items():
            ordered = sorted(salaries)
            self.salary_stats[role] = {
                "min": min(ordered),
                "max": max(ordered),
                "median": median(ordered),
                "count": len(ordered),
                "q1": self._quantile(ordered, 0.25),
                "q3": self._quantile(ordered, 0.75),
            }

        overall_sorted = sorted(self._all_salaries)
        overall_q1 = self._quantile(overall_sorted, 0.25)
        overall_q3 = self._quantile(overall_sorted, 0.75)
        overall_iqr = overall_q3 - overall_q1
        overall_upper = overall_q3 + (1.5 * overall_iqr if overall_iqr else 15000)
        overall_lower = overall_q1 - (1.5 * overall_iqr if overall_iqr else 15000)

        for job in job_listings:
            average_salary = self._average_salary(job)
            if average_salary is None:
                continue

            role = job.get("title", "Unknown Role")
            role_stats = self.salary_stats.get(role, {})
            role_iqr = role_stats.get("q3", 0) - role_stats.get("q1", 0)
            role_upper = role_stats.get("q3", average_salary) + (1.5 * role_iqr if role_iqr else 0)
            role_lower = role_stats.get("q1", average_salary) - (1.5 * role_iqr if role_iqr else 0)

            reasons = []
            if average_salary > overall_upper or average_salary < overall_lower:
                reasons.append("overall_outlier")
            if role_stats.get("count", 0) >= 4 and (average_salary > role_upper or average_salary < role_lower):
                reasons.append("role_outlier")

            if reasons:
                anomalies.append({
                    "job_id": job.get("id"),
                    "title": role,
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "salary_avg": average_salary,
                    "expected_salary_range": {
                        "min": role_stats.get("q1", overall_q1),
                        "max": role_stats.get("q3", overall_q3),
                    },
                    "reasons": reasons,
                })

        return anomalies

    def get_salary_range(self, role: str) -> Dict:
        """Get salary statistics for a specific role."""
        for known_role, stats in self.salary_stats.items():
            if role.lower() in known_role.lower():
                return {
                    "role": known_role,
                    "min": stats["min"],
                    "max": stats["max"],
                    "median": stats["median"],
                    "count": stats["count"],
                }

        return {"role": role, "min": 0, "max": 0, "median": 0, "count": 0}
