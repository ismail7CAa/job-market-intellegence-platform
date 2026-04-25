"""Natural Language Processing for user queries about the job market."""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Process natural language questions about the job market."""

    def __init__(self, model_name: str = "bert-base-uncased"):
        """Initialize NLP query processor with a language model."""
        self.model_name = model_name
        self.model = None

    def process_query(self, question: str) -> Dict[str, Any]:
        """Convert natural language question into structured query."""
        logger.info(f"Processing query: {question}")
        normalized = question.lower().strip()
        intent = "summary"

        if any(keyword in normalized for keyword in ["top skill", "most in-demand skill", "trending skill"]):
            intent = "top_skills"
        elif any(keyword in normalized for keyword in ["salary anomaly", "salary outlier", "anomalies"]):
            intent = "salary_anomalies"
        elif "salary" in normalized:
            intent = "salary_range"
        elif any(keyword in normalized for keyword in ["predict", "next quarter", "in-demand roles"]):
            intent = "predicted_roles"
        elif "remote" in normalized:
            intent = "remote_summary"
        elif any(keyword in normalized for keyword in ["how many", "count", "total jobs"]):
            intent = "job_count"

        quoted_terms = re.findall(r"'([^']+)'|\"([^\"]+)\"", question)
        entities = [term[0] or term[1] for term in quoted_terms]
        top_n_match = re.search(r"top\s+(\d+)", normalized)

        return {
            "intent": intent,
            "entities": entities,
            "query": {
                "top_n": int(top_n_match.group(1)) if top_n_match else 5,
                "subject": entities[0] if entities else None,
            },
        }

    def answer_question(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Answer a question about the job market."""
        parsed = self.process_query(question)
        context = context or {}

        if parsed["intent"] == "top_skills" and context.get("top_skills"):
            skills = ", ".join(
                f"{item['skill']} ({item['demand']})"
                for item in context["top_skills"][: parsed["query"]["top_n"]]
            )
            return f"Top skills right now: {skills}."

        if parsed["intent"] == "salary_anomalies":
            anomalies = context.get("anomalies", [])
            if not anomalies:
                return "No salary anomalies were detected in the current dataset."
            return f"I found {len(anomalies)} salary anomalies in the current dataset."

        if parsed["intent"] == "salary_range" and context.get("salary_range"):
            salary_range = context["salary_range"]
            if salary_range.get("count", 0) == 0:
                return "I could not find salary data for that role in the current dataset."
            return (
                f"{salary_range['role']} currently ranges from ${salary_range['min']:,.0f} "
                f"to ${salary_range['max']:,.0f}, with a median of ${salary_range['median']:,.0f}."
            )

        if parsed["intent"] == "predicted_roles" and context.get("predicted_roles"):
            roles = ", ".join(
                f"{item['role']} ({item['projected_demand_index']:.1f})"
                for item in context["predicted_roles"][: parsed["query"]["top_n"]]
            )
            return f"Projected in-demand roles: {roles}."

        if parsed["intent"] == "remote_summary":
            remote_jobs = context.get("remote_jobs", 0)
            total_jobs = context.get("total_jobs", 0)
            return f"There are {remote_jobs} remote jobs out of {total_jobs} jobs in the current dataset."

        if parsed["intent"] == "job_count":
            return f"The current dataset contains {context.get('total_jobs', 0)} jobs."

        return context.get(
            "summary",
            "I can summarize jobs, skills, salary anomalies, and role predictions once data is loaded.",
        )
