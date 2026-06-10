"""Deterministic recommendation selection from taxonomy."""

RECOMMENDATIONS = {
    "hallucination": "Review retrieval grounding and add citation requirements to the prompt.",
    "retrieval_failure": "Tune retrieval index, increase top-k, or improve chunking strategy.",
    "tool_failure": "Verify tool schema definitions and add tool-selection guardrails.",
    "sql_failure": "Add schema validation layer and SQL linting before execution.",
    "prompt_regression": "Roll back to prompt_v4_schema_aware and A/B test changes.",
    "reasoning_failure": "Add chain-of-thought verification or secondary checker step.",
    "format_failure": "Enforce output schema with structured response templates.",
    "latency_failure": "Profile slow steps; consider caching or model downgrade.",
    "cost_failure": "Reduce context window or switch to a lower-cost model tier.",
    "pipeline_failure": "Inspect ingestion logs and quarantine records for data quality issues.",
    "unknown": "Manual review required — signals are ambiguous.",
}


class RecommendationEngine:
    def recommend(self, primary_category: str) -> str:
        return RECOMMENDATIONS.get(primary_category, RECOMMENDATIONS["unknown"])
