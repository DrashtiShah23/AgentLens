# Architecture

> See [README.md](../README.md) for the full project overview, screenshots, and demo script.

AI Failure Observatory separates **deterministic evaluation** from **human investigation**.

**Disclaimer:** All scores and dashboard metrics come from deterministic evaluation of **synthetic demo agent runs**. This does not benchmark real production GPT, Claude, Gemini, or Llama traffic. LLM is disabled by default (`OBSERVATORY_USE_LLM=false`).

## Layers

1. **Ingestion** — Pydantic validation, quarantine, Parquet, DuckDB
2. **Evaluation** — Deterministic scorers (no LLM)
3. **Classification** — Rule-based failure taxonomy (no LLM)
4. **Transformation** — dbt staging → intermediate → marts
5. **Serving** — Streamlit dashboard, FastAPI, investigation agent
6. **Metadata** — catalog.json and lineage.json from dbt manifest

## Core Constraint

```
Every run → deterministic evaluators (zero LLM cost)
dbt → aggregated metrics (zero LLM cost)
Human question → one optional LLM call against aggregates
```

## Components

| Component | Role |
|---|---|
| DuckDB | Analytical warehouse |
| dbt Core | Transform raw tables to marts |
| Streamlit | Direct mart queries for dashboards |
| FastAPI | Validated ingestion + read-only metrics API |
| LangGraph / fallback | Investigation agent with safe tools |
| Ollama (optional) | Local LLM for investigation summaries only |
