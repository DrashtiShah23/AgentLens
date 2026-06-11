# Interview Story

> Dashboard screenshots and demo script: [README.md](../README.md)

I built AI Failure Observatory because production AI agents fail in ways standard logs cannot explain — prompt regressions, retrieval misses, SQL errors, tool failures, and hallucinations all look like "request failed."

**Be explicit in interviews:** scores are deterministic metrics from synthetic demo runs. The project demonstrates observability logic; it does not claim to benchmark real provider production traffic. LLM is off by default.

The key architectural decision: **separate evaluation from investigation**. Every run is scored deterministically at zero LLM cost. dbt aggregates those scores into reliability marts. Only when a human asks a question does an optional LLM summarize pre-aggregated metrics — one query can represent a million runs for fractions of a cent.

The platform combines DuckDB, dbt, Pydantic validation, Streamlit dashboards, FastAPI ingestion, and a constrained investigation agent with read-only tools. Prompt regression detection (prompt_v5) is built into both the synthetic generator and mart models.
