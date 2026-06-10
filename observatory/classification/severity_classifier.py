"""Rule-based severity assignment."""

from typing import Any


class SeverityClassifier:
    def assign(self, context: dict[str, Any], primary_category: str,
               confidence: float) -> str:
        overall = context.get("overall_score", 1.0)
        latency = context.get("latency_ms", 0)
        cost = context.get("estimated_cost_usd", 0)

        if primary_category == "pipeline_failure":
            return "medium" if context.get("is_duplicate") else "high"
        if overall < 0.3:
            return "critical"
        if primary_category in {"hallucination", "sql_failure"} and overall < 0.5:
            return "high"
        if primary_category in {"latency_failure", "cost_failure"}:
            if latency > 10000 or cost > 0.01:
                return "high"
            return "medium"
        if confidence < 0.6:
            return "low"
        if overall < 0.6:
            return "medium"
        return "low"
