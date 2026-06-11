# Data Model

## Raw Tables (DuckDB)

- `agent_runs` — execution events
- `tool_calls`, `retrieval_events`, `prompt_versions`
- `evaluation_results`, `failure_modes`
- `quarantine_records`, `ingestion_audit`

## Mart Tables (dbt)

- `mart_agent_reliability` — daily per-agent reliability
- `mart_failure_trends` — failures by category/severity/day
- `mart_prompt_regression` — prompt version comparison
- `mart_model_comparison` — model scoring matrix
- `mart_cost_latency` — cost/latency spikes
- `mart_incident_summary` — grouped incidents

## Contracts

All external payloads validated with Pydantic v2 schemas in `app/api/schemas/`.
