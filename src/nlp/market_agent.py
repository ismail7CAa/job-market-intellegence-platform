"""Grounded agent layer for explaining job market analytics outputs."""

from __future__ import annotations

import re
from statistics import mean, median
from typing import Any, Dict, List, Optional

from src.analytics.salary_analysis import SalaryAnomalyDetector


class MarketIntelligenceAgent:
    """Retrieve analysis evidence and narrate grounded answers."""

    def __init__(self, salary_detector: Optional[SalaryAnomalyDetector] = None):
        """Initialize the agent with reusable analysis tools."""
        self.salary_detector = salary_detector or SalaryAnomalyDetector()

    @staticmethod
    def _average_salary(job: Dict[str, Any]) -> Optional[float]:
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        if salary_min is None or salary_max is None:
            return None
        return (float(salary_min) + float(salary_max)) / 2

    @staticmethod
    def _extract_job_id(question: str) -> Optional[str]:
        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", question)
        if quoted:
            return next((left or right for left, right in quoted if left or right), None)

        match = re.search(r"\b(?:job[_\s-]?id|id)\s*[:=]?\s*([A-Za-z0-9_-]+)", question, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _find_job(jobs: List[Dict[str, Any]], job_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not job_id:
            return None
        return next((job for job in jobs if str(job.get("id")) == str(job_id)), None)

    def _salary_context(self, jobs: List[Dict[str, Any]], target_job: Dict[str, Any]) -> Dict[str, Any]:
        salaries = [
            salary
            for salary in (self._average_salary(job) for job in jobs)
            if salary is not None
        ]
        target_salary = self._average_salary(target_job)
        if not salaries or target_salary is None:
            return {
                "target_salary": target_salary,
                "dataset_salary_count": len(salaries),
                "dataset_median_salary": None,
                "dataset_mean_salary": None,
                "percent_difference_from_median": None,
            }

        dataset_median = median(salaries)
        percent_difference = (
            ((target_salary - dataset_median) / dataset_median) * 100
            if dataset_median
            else 0
        )
        return {
            "target_salary": target_salary,
            "dataset_salary_count": len(salaries),
            "dataset_median_salary": dataset_median,
            "dataset_mean_salary": mean(salaries),
            "percent_difference_from_median": percent_difference,
        }

    @staticmethod
    def _anomaly_for_job(anomalies: List[Dict[str, Any]], job_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not job_id:
            return anomalies[0] if anomalies else None
        return next((item for item in anomalies if str(item.get("job_id")) == str(job_id)), None)

    def explain_salary_anomaly(
        self,
        question: str,
        jobs: List[Dict[str, Any]],
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Explain why a salary was or was not flagged as anomalous."""
        resolved_job_id = job_id or self._extract_job_id(question)
        anomalies = self.salary_detector.detect_anomalies(jobs)
        anomaly = self._anomaly_for_job(anomalies, resolved_job_id)

        if anomaly and not resolved_job_id:
            resolved_job_id = anomaly.get("job_id")

        target_job = self._find_job(jobs, resolved_job_id)
        if target_job is None and anomaly:
            target_job = next(
                (job for job in jobs if str(job.get("id")) == str(anomaly.get("job_id"))),
                None,
            )

        if target_job is None:
            return {
                "intent": "explain_salary_anomaly",
                "answer": "I could not find the job posting needed to explain that salary flag.",
                "evidence": {
                    "requested_job_id": resolved_job_id,
                    "available_anomaly_count": len(anomalies),
                },
                "tool_trace": ["detect_salary_anomalies", "retrieve_job_posting"],
                "status": "not_found",
            }

        salary_context = self._salary_context(jobs, target_job)
        is_flagged = anomaly is not None
        answer = self._narrate_salary_anomaly(target_job, anomaly, salary_context, is_flagged)

        return {
            "intent": "explain_salary_anomaly",
            "answer": answer,
            "evidence": {
                "job": {
                    "id": target_job.get("id"),
                    "title": target_job.get("title"),
                    "company": target_job.get("company"),
                    "location": target_job.get("location"),
                    "salary_min": target_job.get("salary_min"),
                    "salary_max": target_job.get("salary_max"),
                },
                "anomaly": anomaly,
                "salary_context": salary_context,
            },
            "tool_trace": [
                "detect_salary_anomalies",
                "retrieve_job_posting",
                "compute_salary_context",
                "generate_grounded_narrative",
            ],
            "status": "ready",
        }

    @staticmethod
    def _narrate_salary_anomaly(
        job: Dict[str, Any],
        anomaly: Optional[Dict[str, Any]],
        salary_context: Dict[str, Any],
        is_flagged: bool,
    ) -> str:
        title = job.get("title", "this role")
        company = job.get("company", "the company")
        salary = salary_context.get("target_salary")
        median_salary = salary_context.get("dataset_median_salary")
        percent_difference = salary_context.get("percent_difference_from_median")

        if salary is None:
            return (
                f"I cannot explain a salary anomaly for {title} at {company} because "
                "the posting does not include both salary bounds."
            )

        comparison = ""
        if median_salary is not None and percent_difference is not None:
            direction = "above" if percent_difference >= 0 else "below"
            comparison = (
                f" Its midpoint salary is ${salary:,.0f}, which is "
                f"{abs(percent_difference):.1f}% {direction} the dataset median of "
                f"${median_salary:,.0f}."
            )

        if not is_flagged:
            return (
                f"{title} at {company} was not flagged as a salary anomaly by the current "
                f"detector.{comparison}"
            )

        reasons = ", ".join(anomaly.get("reasons", []))
        expected = anomaly.get("expected_salary_range", {})
        return (
            f"The salary for {title} at {company} was flagged because it matched "
            f"the detector reason(s): {reasons}.{comparison} The expected interquartile "
            f"range for the relevant comparison group is roughly "
            f"${expected.get('min', 0):,.0f} to ${expected.get('max', 0):,.0f}."
        )

    def answer(self, question: str, jobs: List[Dict[str, Any]], job_id: Optional[str] = None) -> Dict[str, Any]:
        """Route a natural-language question to the right explanation workflow."""
        normalized = question.lower()
        if "salary" in normalized and any(word in normalized for word in ["anomal", "outlier", "flag"]):
            return self.explain_salary_anomaly(question=question, jobs=jobs, job_id=job_id)

        return {
            "intent": "general_market_question",
            "answer": (
                "I can currently explain salary anomaly flags by retrieving the job posting, "
                "running the anomaly detector, and summarizing the evidence."
            ),
            "evidence": {"job_count": len(jobs)},
            "tool_trace": ["classify_question"],
            "status": "ready",
        }
