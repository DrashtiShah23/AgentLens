# AI Failure Observatory — Project Spec

## One Sentence Pitch

Built AI Failure Observatory, an Airflow and dbt powered observability platform that ingests AI agent execution logs, evaluates agent reliability using deterministic scoring, classifies hallucination, retrieval, tool, SQL, and prompt failures, and uses a LangGraph investigation agent to answer natural language root cause questions against aggregated DuckDB metrics — LLM is called once per human question, never once per run.

---

## Problem Statement

AI agents are being deployed into real workflows for text-to-SQL, retrieval QA, tool automation, customer support, and internal copilots. When they fail, teams know something went wrong but cannot identify the root cause.

Common unknowns:

- Did the model misunderstand the task
- Did the prompt regress between versions
- Did retrieval miss the relevant context
- Did the agent call the wrong tool
- Did generated SQL fail or return wrong results
- Did the agent produce unsupported claims
- Did latency or cost spike
- Did a data pipeline fail upstream of the agent
- Did schema changes break the agent
- Did the same failure pattern occur before

AI Failure Observatory solves this by building a full reliability layer. Every agent execution is treated as an event. Those events are ingested, validated, evaluated with deterministic logic, classified by failure mode, transformed into analytics models, and made available to a natural language investigation agent that queries aggregated metrics — not individual runs — to produce root cause summaries.

---

## Core Architecture Principle

**LLM calls are triggered by human investigation queries against aggregated metrics. They are never triggered per run.**

This is not a preference. It is a hard architectural constraint driven by cost and correctness.

At 1 million runs, even a single LLM call per run at the cheapest available model costs hundreds of dollars. At 5 to 6 million runs it becomes thousands. That blows any reasonable budget before a single dashboard loads.

More importantly, per-run LLM evaluation is also worse evaluation. A deterministic SQL parser knows whether SQL is valid. A keyword overlap function knows whether the answer contains the expected terms. An LLM guessing at run quality introduces noise, inconsistency, and latency with no accuracy benefit for structured signals.

The correct design:

```
deterministic evaluators score every run      ← zero LLM cost
dbt aggregates scores into metrics            ← zero LLM cost
human asks investigation question             ← one LLM call
LLM reads aggregated metrics from DuckDB     ← summarizes thousands of runs at once
LLM returns root cause + recommendation      ← one call, fractions of a cent
```

This means the $15 budget is spent entirely on investigation agent queries. At roughly $0.0002 per query with gpt-4o-mini or claude-haiku, $15 buys approximately 75,000 investigation queries. For a demo or portfolio project, this is effectively unlimited.

---

## Stack

All required components are free. LLM API usage is optional and pay-per-query only for investigation.

| Component | Tool | Cost |
|---|---|---|
| Language | Python 3.11+ | Free |
| Warehouse | DuckDB | Free |
| Transformation | dbt Core | Free |
| Orchestration | Apache Airflow (local) | Free |
| Dashboard | Streamlit | Free |
| API | FastAPI | Free |
| Agent framework | LangGraph | Free |
| Schema validation | Pydantic v2 | Free |
| Testing | pytest | Free |
| Storage | Parquet + local JSON | Free |
| Local LLM fallback | Ollama (llama3) | Free |
| Investigation LLM | gpt-4o-mini or claude-haiku | Pay per query only |

Do not require AWS, paid databases, hosted dashboards, or paid metadata platforms.

The project must run fully from a clean clone with no cloud credentials.

---

## Data Volume Targets

| Phase | Run Count | Purpose |
|---|---|---|
| Phase 1 | 10,000 | Foundation and schema validation |
| Phase 2 | 100,000 | Evaluation engine development |
| Phase 3 | 1,000,000 | dbt model and analytics layer |
| Final demo | 1,000,000+ | Full platform demonstration |

DuckDB handles 10 to 50 million rows on a standard laptop without performance issues. The constraint is data generation speed, not query performance. Design the synthetic generator to be fast.

---

## Pydantic v2 Usage

Pydantic is not just a type checker in this project. It is the validation and normalization layer for every external data contract.

Use the full Pydantic v2 feature set:

**Cross-field validation with model_validator:**
```python
from pydantic import BaseModel, model_validator

class AgentRun(BaseModel):
    started_at: datetime
    completed_at: datetime
    latency_ms: int

    @model_validator(mode='after')
    def validate_timing(self) -> 'AgentRun':
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")
        return self
```

**Input normalization with field_validator:**
```python
from pydantic import field_validator

class AgentRun(BaseModel):
    latency_ms: int

    @field_validator('latency_ms', mode='before')
    @classmethod
    def coerce_latency(cls, v: Any) -> int:
        if isinstance(v, str):
            return int(v)
        return v
```

**Derived fields with computed_field:**
```python
from pydantic import computed_field

class AgentRun(BaseModel):
    started_at: datetime
    completed_at: datetime

    @computed_field
    @property
    def duration_seconds(self) -> float:
        return (self.completed_at - self.started_at).total_seconds()
```

**Strict mode to reject silent coercion:**
```python
class AgentRun(BaseModel):
    model_config = ConfigDict(strict=True)
```

**Use model_json_schema() to generate contract documentation:**
```python
schema = AgentRun.model_json_schema()
```

Every schema must handle dirty input gracefully. If a field arrives as a string when an int is expected, coerce it or reject it with a structured error message that identifies the field and the reason. Never let bad data pass through silently and fail later in DuckDB.

---

## Data Contracts

### AgentRun

```python
run_id: str                          # required, unique
agent_name: str                      # required
task_type: TaskType                  # required, enum
user_query: str                      # required
prompt_version_id: str               # required
model_name: str                      # required
started_at: datetime                 # required
completed_at: datetime               # required
latency_ms: int                      # required, >= 0
input_tokens: int                    # required, >= 0
output_tokens: int                   # required, >= 0
estimated_cost_usd: float            # required, >= 0
final_answer: str                    # required
success_flag: bool                   # required
error_message: Optional[str]         # nullable
generated_sql: Optional[str]         # nullable
expected_answer: Optional[str]       # nullable
metadata: Optional[dict]             # nullable
```

TaskType enum values: `text_to_sql`, `retrieval_qa`, `tool_use`, `summarization`, `classification`

Cross-field validation rules enforced at model level:
- `completed_at >= started_at`
- `latency_ms >= 0`
- `input_tokens >= 0`
- `output_tokens >= 0`
- `estimated_cost_usd >= 0`

### ToolCall

```python
tool_call_id: str                    # required, unique
run_id: str                          # required, FK to agent_runs
tool_name: str                       # required
tool_input: dict                     # required
tool_output: Optional[dict]          # nullable
tool_status: ToolStatus              # required, enum
error_message: Optional[str]         # nullable
started_at: datetime                 # required
completed_at: datetime               # required
latency_ms: int                      # required, >= 0
```

ToolStatus enum values: `success`, `failed`, `skipped`

### RetrievalEvent

```python
retrieval_id: str                    # required, unique
run_id: str                          # required, FK to agent_runs
query_text: str                      # required
document_id: str                     # required
chunk_text: str                      # required
rank_position: int                   # required, > 0
relevance_score: float               # required, 0.0 to 1.0
was_used_in_answer: bool             # required
```

### PromptVersion

```python
prompt_version_id: str               # required, unique
agent_name: str                      # required
prompt_name: str                     # required
prompt_text: str                     # required, not empty
created_at: datetime                 # required
active_flag: bool                    # required
change_reason: str                   # required, not empty
```

### EvaluationResult

```python
evaluation_id: str                   # required, unique
run_id: str                          # required, FK to agent_runs
correctness_score: Optional[float]   # 0.0 to 1.0
sql_score: Optional[float]           # 0.0 to 1.0
tool_score: Optional[float]          # 0.0 to 1.0
retrieval_score: Optional[float]     # 0.0 to 1.0
format_score: Optional[float]        # 0.0 to 1.0
latency_score: Optional[float]       # 0.0 to 1.0
cost_score: Optional[float]          # 0.0 to 1.0
overall_score: float                 # required, 0.0 to 1.0
failure_category: Optional[str]      # nullable
severity: Optional[str]              # nullable
evaluator_notes: Optional[str]       # nullable
evaluated_at: datetime               # required
```

---

## Synthetic Data Strategy

Real data is not used for the following reasons:

- Production AI agent logs are not publicly available without privacy and legal constraints
- Real data is messy in uncontrolled ways that consume time better spent building the platform
- Synthetic data allows precise injection of failure modes with known ground truth
- Deterministic failure rates make evaluation logic testable and demo behavior predictable

The generator must produce realistic failure distributions, not random noise.

### Synthetic Agents

```
sql_analyst_agent
research_assistant_agent
support_triage_agent
data_ops_agent
tool_router_agent
```

### Synthetic Models

```
gpt_4o_mini_simulated
claude_sonnet_simulated
gemini_flash_simulated
llama_local_simulated
```

### Synthetic Prompt Versions

```
prompt_v1_baseline
prompt_v2_more_context
prompt_v3_short_prompt
prompt_v4_schema_aware
prompt_v5_regression_case
```

### Required Failure Scenarios

The generator must inject these failure types at configurable rates:

| Scenario | Target Rate |
|---|---|
| Successful runs | 60% |
| SQL syntax failures | 5% |
| SQL semantic failures | 5% |
| Retrieval misses | 7% |
| Hallucinated answers | 6% |
| Wrong tool calls | 4% |
| Prompt regressions (on v5) | 8% |
| Latency spikes | 3% |
| Cost spikes | 2% |
| Format violations | 3% |
| Malformed records (quarantine bait) | 2% |
| Duplicate run ids | 1% |

Prompt v5 must have a measurably worse reliability score than v1 through v4. This is the regression the investigation agent should detect.

---

## Evaluation Engine

All evaluators are deterministic. No LLM is called during evaluation.

### Correctness Evaluator

For numerical answers: exact match with small decimal tolerance.
For text answers: keyword overlap score between final_answer and expected_answer.
Score range: 0.0 to 1.0.
If expected_answer is null, score is null and excluded from overall calculation.

### SQL Evaluator

Checks in order:
1. generated_sql is not empty — fail fast if empty
2. SQL parses without syntax error using sqlglot
3. SQL references only allowed tables
4. SQL references only existing columns
5. SQL does not contain destructive commands: DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE, CREATE
6. SQL result matches expected answer if expected_answer is provided

Score is computed from how many checks pass. A syntax error scores 0.0. Passing all checks scores 1.0.

### Tool Evaluator

Checks:
1. Required tool was called for the task
2. Correct tool name was used
3. Tool input matched expected schema
4. Tool completed with status success
5. Tool output was non-empty

### Retrieval Evaluator

Checks:
1. At least one retrieval event exists for the run
2. Top-ranked chunk has relevance_score above threshold (default 0.5)
3. At least one chunk was marked was_used_in_answer
4. Retrieval result is not empty

### Format Evaluator

Checks:
1. final_answer is not empty
2. If task requires JSON output, final_answer parses as valid JSON
3. Required output fields are present
4. No extra fields when strict mode is active

### Latency Evaluator

Thresholds (configurable in settings):
- Under 2000ms: score 1.0
- 2000ms to 5000ms: score 0.5
- Over 5000ms: score 0.0

### Cost Evaluator

Thresholds (configurable in settings):
- Under $0.001: score 1.0
- $0.001 to $0.005: score 0.5
- Over $0.005: score 0.0

### Overall Reliability Score

Weighted average. Weights are task-type aware.

Default weights:
```
correctness: 0.35
sql:         0.20  (elevated for text_to_sql tasks)
tool:        0.15  (elevated for tool_use tasks)
retrieval:   0.15  (elevated for retrieval_qa tasks)
format:      0.10
latency:     0.03
cost:        0.02
```

If a component score is null (evaluator did not run or data was missing), exclude it from the weighted average and redistribute its weight proportionally across remaining components. Never let a missing evaluator silently push the overall score to zero.

---

## Failure Classification

Classification is deterministic rule-based logic. No LLM is called.

### Failure Taxonomy

| Category | Primary Signals |
|---|---|
| hallucination | High correctness failure, retrieval events exist, SQL valid or not applicable |
| retrieval_failure | Low retrieval score, correct tool and format |
| tool_failure | tool_status failed or skipped, tool_score below threshold |
| sql_failure | SQL parse error or execution error, task_type is text_to_sql |
| prompt_regression | Reliability score drops after prompt version change on same benchmark |
| reasoning_failure | Retrieval good, tools valid, SQL valid, answer still wrong |
| format_failure | Format score below threshold, other scores acceptable |
| latency_failure | Latency score zero, other scores acceptable |
| cost_failure | Cost score zero, other scores acceptable |
| pipeline_failure | Missing data, duplicate run_id, ingestion error, dbt failure |
| unknown | No clear signal pattern matched |

### Severity Assignment

| Severity | Criteria |
|---|---|
| critical | >50% failure rate on one agent, mart model fails, investigation agent cannot query |
| high | >20% failure rate spike, model latency doubles, hallucination rate exceeds threshold |
| medium | One benchmark category degrades, one tool intermittently failing |
| low | Missing optional metadata, single malformed record, minor latency increase |

When multiple failure signals exist, assign the primary category by the strongest signal and store secondary signals in a separate column. Store a confidence score. Flag classifications below 0.6 confidence for human review. Never fabricate a root cause when signals are ambiguous.

---

## LangGraph Investigation Agent

The investigation agent is a constrained reliability analyst. It is not a general chatbot.

### What It Does

1. Parses the human question to identify the metric of interest and time window
2. Selects the correct tool to query DuckDB
3. Executes a read-only parameterized query against aggregated mart tables
4. Passes the query result to an LLM to produce a natural language summary
5. Returns the summary with the metric name, time window, and recommended next action

The LLM receives aggregated query results, not raw run logs. A question about reliability this week might summarize 50,000 runs in a single tool response that fits in 500 tokens.

### Agent Tools

All tools execute read-only parameterized queries. No raw SQL is accepted from users.

```
get_overall_reliability(time_window_days: int) -> ReliabilityMetrics
get_failure_trends(time_window_days: int, agent_name: Optional[str]) -> FailureTrends
get_prompt_comparison(agent_name: str) -> PromptComparisonMetrics
get_model_comparison(task_type: Optional[str]) -> ModelComparisonMetrics
get_run_details(run_id: str) -> RunDetail
get_recent_incidents(severity: Optional[str], limit: int) -> List[Incident]
get_cost_latency_summary(time_window_days: int) -> CostLatencyMetrics
get_lineage_for_model(model_name: str) -> LineageInfo
```

### Safety Rules

- Only parameterized queries against known mart tables
- No raw SQL accepted from user input under any circumstances
- Block any input containing DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE, CREATE
- Validate table names against a whitelist before execution
- Limit returned rows to 1000 maximum
- If the question is outside reliability scope, say so and redirect
- If data is missing or stale, say so explicitly
- Never invent a metric or fabricate a trend
- Never expose internal table names, column names, or DuckDB file path

### LLM Call Budget

Each investigation query costs approximately $0.0001 to $0.0003 with gpt-4o-mini or claude-haiku-3.

At $15 budget with $0.0002 average per query: approximately 75,000 investigation queries available.

For a demo or portfolio project this is effectively unlimited.

Use Ollama with llama3 as the local fallback when LLM API is disabled. The project must function fully with LLM disabled, returning raw metric data as structured output instead of a natural language summary.

---

## Airflow DAGs

### dag_ingest_agent_logs

Tasks:
1. `discover_raw_files` — scan raw log directory for unprocessed JSON files
2. `validate_records` — run Pydantic validation, quarantine failures with reason
3. `write_valid_parquet` — write valid records to partitioned Parquet
4. `write_invalid_quarantine` — write invalid records with failure reason
5. `load_duckdb` — upsert valid records into DuckDB, flag duplicates
6. `write_ingestion_audit` — write summary with processed, valid, invalid, duplicate counts

Failure handling:
- One bad file does not fail the whole DAG
- Every invalid record gets a structured rejection reason
- Duplicate run_ids are flagged, not silently dropped
- Empty files are flagged, not silently skipped

### dag_run_evaluations

Tasks:
1. `fetch_unevaluated_runs` — query DuckDB for runs without evaluation records
2. `evaluate_sql_runs` — run SQL evaluator on text_to_sql runs
3. `evaluate_retrieval_runs` — run retrieval evaluator on retrieval_qa runs
4. `evaluate_tool_runs` — run tool evaluator on tool_use runs
5. `evaluate_format` — run format evaluator on all runs
6. `evaluate_latency_cost` — run latency and cost evaluators on all runs
7. `compute_overall_scores` — compute weighted overall reliability score
8. `write_evaluation_results` — write to DuckDB evaluation table

Failure handling:
- Evaluator crash stores the error, does not erase the run
- Missing components excluded from overall score, not counted as zero
- Unsupported task types are marked with clear reason, not silently skipped

### dag_classify_failures

Tasks:
1. `fetch_low_score_runs` — query runs with overall_score below threshold
2. `classify_failure_mode` — apply rule-based classifier
3. `assign_severity` — apply severity rules
4. `generate_recommendation` — select recommendation from taxonomy
5. `write_failure_records` — write to DuckDB failure table

Failure handling:
- Unknown patterns classified as unknown with low confidence flag
- Low confidence classifications flagged for human review
- Classification errors written to audit log, do not fail pipeline

### dag_refresh_dbt_models

Tasks:
1. `dbt_debug` — verify DuckDB connection
2. `dbt_run_staging` — run staging models
3. `dbt_run_intermediate` — run intermediate models
4. `dbt_run_marts` — run mart models
5. `dbt_test` — run all dbt tests
6. `dbt_docs_generate` — generate documentation

Failure handling:
- dbt test failure fails the DAG, not just the task
- Failed model names stored and surfaced in dashboard
- Dashboard shows stale model warning when mart refresh is overdue

### dag_refresh_metadata

Tasks:
1. `read_dbt_manifest` — parse dbt manifest.json
2. `extract_models` — extract model names, descriptions, columns
3. `build_lineage` — build upstream/downstream dependency graph
4. `write_catalog` — write catalog.json
5. `write_lineage` — write lineage.json

Failure handling:
- Partial metadata does not overwrite last known good metadata
- Missing manifest produces clear error with remediation hint
- Invalid lineage references flagged, do not fail the entire refresh

### dag_airflow_migration_parity

Purpose: demonstrate Airflow 2 to 3 migration thinking.

Do not install two Airflow versions. Instead implement:
- `run_legacy_pipeline`: classic operator style with PythonOperator and XCom
- `run_modern_pipeline`: TaskFlow API with @task decorator and direct return values
- `compare_row_counts`: assert output row counts match between both implementations
- `compare_schema`: assert column names and types match
- `compare_metric_hashes`: assert aggregated metric values match
- `write_parity_report`: write comparison result with mismatched fields explained

The legacy pipeline is marked retired only when parity passes. This DAG exists to demonstrate migration awareness, not to simulate an environment you don't have.

---

## dbt Models

### Staging

| Model | Source | Purpose |
|---|---|---|
| stg_agent_runs | raw DuckDB table | Rename, cast, deduplicate |
| stg_tool_calls | raw DuckDB table | Rename, cast, FK reference |
| stg_retrieval_events | raw DuckDB table | Rename, cast, validate scores |
| stg_prompt_versions | raw DuckDB table | Rename, cast, active flag |
| stg_evaluation_results | raw DuckDB table | Rename, cast, score ranges |

Staging rules: rename to consistent snake_case, cast timestamps to UTC, cast booleans, normalize task_type to enum values, remove duplicates, add `loaded_at` metadata column.

### Intermediate

| Model | Purpose |
|---|---|
| int_run_quality | Join runs with evaluations, compute run-level quality label |
| int_failure_classification | Join with failure records, add category and severity |
| int_prompt_performance | Aggregate reliability, cost, latency by prompt version |
| int_model_performance | Aggregate reliability, cost, latency by model |
| int_tool_performance | Aggregate success rate, error rate by tool name |

### Marts

| Model | Purpose |
|---|---|
| mart_agent_reliability | Per-agent reliability over time, dashboard primary table |
| mart_failure_trends | Failure counts by category, severity, day |
| mart_prompt_regression | Prompt version comparison with regression detection |
| mart_model_comparison | Model scoring matrix across task types |
| mart_cost_latency | Cost and latency trends with spike detection |
| mart_incident_summary | Grouped incident records with affected agents and recommendations |

Mart rules: column names must be human readable, schema.yml must include description for every public column, metric definitions included, tests on all primary keys and critical metrics.

### dbt Tests

Required tests:

```yaml
- unique: run_id, tool_call_id, retrieval_id, prompt_version_id, evaluation_id
- not_null: run_id, agent_name, task_type, prompt_version_id, model_name, overall_score
- accepted_values: task_type, failure_category, severity
- relationships: tool_calls.run_id -> agent_runs.run_id
- relationships: retrieval_events.run_id -> agent_runs.run_id
- relationships: evaluation_results.run_id -> agent_runs.run_id
- dbt_utils.between: overall_score (0, 1), failure_rate (0, 1), reliability_score (0, 1)
```

Use `safe_divide` macro for all rate calculations to prevent division-by-zero failures.

---

## Metadata Layer

Lightweight local metadata, no DataHub required.

### catalog.json structure

```json
{
  "models": [
    {
      "model_name": "mart_agent_reliability",
      "layer": "mart",
      "description": "...",
      "owner": "data_engineering",
      "columns": [...],
      "tests": [...],
      "row_count": 1000000,
      "last_updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### lineage.json structure

```json
{
  "edges": [
    {
      "upstream": "stg_agent_runs",
      "downstream": "int_run_quality",
      "transformation_type": "join_and_aggregate",
      "description": "..."
    }
  ]
}
```

Never overwrite last known good metadata if refresh fails. Write to a temp file first, validate it, then rename to replace the production file.

---

## FastAPI Routes

### Health
```
GET  /health                          warehouse + log dir status
```

### Runs
```
POST /runs                            ingest agent run payload
GET  /runs                            list runs with filters
GET  /runs/{run_id}                   single run with evaluations and failures
```

### Evaluations
```
GET  /evaluations                     list evaluation records
POST /evaluations/run                 trigger evaluation for selected runs
```

### Metrics
```
GET  /metrics/overview                dashboard summary metrics
GET  /metrics/failures                failure trend metrics
GET  /metrics/prompts                 prompt comparison metrics
GET  /metrics/models                  model comparison metrics
```

### Investigation
```
POST /investigate                     natural language question → investigation summary
```

All routes return structured Pydantic response models. All routes handle DuckDB connection errors with a 503 response and actionable message. No route exposes raw SQL or internal file paths.

---

## Streamlit Dashboard

### Page 1 — Overview

Metrics: total runs, reliability score, failure rate, average latency, estimated cost, most common failure category, most affected agent, most affected prompt version.

Charts: reliability over time, failure rate over time, failure counts by category, run volume by day.

### Page 2 — Failures

Filters: severity, agent, prompt version, failure category, date range.

Display: failure records with root cause and recommended fix.

Charts: failure categories by day, severity distribution, top failing agents, top failing tools.

### Page 3 — Prompt Performance

Display: prompt versions with change reasons, reliability, cost, latency, regression alerts.

Charts: prompt score comparison, regression trend over time, failure category by prompt version.

### Page 4 — Model Performance

Display: model name, reliability, correctness, SQL, retrieval, tool scores, cost, latency.

Charts: reliability by model, cost by model, latency by model, failure rate by model.

### Page 5 — Run Explorer

Searchable table with filters: date range, agent, model, prompt version, task type, success flag, failure category, severity.

Clicking a run shows: user query, final answer, generated SQL, expected answer, tool calls, retrieval events, evaluation scores, failure classification, recommended fix.

### Page 6 — Investigation Agent

Chat interface. User types a question. Response shows natural language summary, metric values cited, recommended next action.

Example questions supported:
- Why did reliability drop yesterday
- Which prompt version caused the most failures
- Which model is best for text-to-SQL
- What are the top failure modes this week
- Which runs need human review
- Did prompt_v5_regression_case make things worse
- Which agent is most expensive
- Which tool causes the most failures

### Dashboard Engineering Rules

- Cache expensive DuckDB queries with `@st.cache_data(ttl=300)`
- Show clear empty state when no data matches a filter
- Show actionable error message when DuckDB is unreachable
- Default to last 7 days time window
- Limit run explorer to 500 rows per page
- Do not crash on null metric values

---

## Repository Structure

```
ai_failure_observatory/
  README.md
  PROJECT_SPEC.md
  pyproject.toml
  requirements.txt
  docker-compose.yml
  Makefile
  .env.example
  .gitignore

  docs/
    architecture.md
    data_model.md
    failure_taxonomy.md
    evaluation_methodology.md
    local_setup.md
    interview_story.md
    resume_bullets.md
    llm_cost_design.md          ← explains why LLM is called per query not per run

  airflow/
    dags/
      dag_ingest_agent_logs.py
      dag_run_evaluations.py
      dag_classify_failures.py
      dag_refresh_dbt_models.py
      dag_refresh_metadata.py
      dag_airflow_migration_parity.py
    include/
      airflow_helpers.py
      path_config.py
    tests/
      test_dag_imports.py

  app/
    api/
      main.py
      dependencies.py
      routes/
        health.py
        runs.py
        evaluations.py
        metrics.py
        investigations.py
      schemas/
        agent_run.py
        evaluation_result.py
        tool_call.py
        retrieval_event.py
        prompt_version.py
      services/
        log_writer.py
        warehouse_reader.py
        metric_service.py
    dashboard/
      streamlit_app.py
      pages/
        page_overview.py
        page_failures.py
        page_prompts.py
        page_models.py
        page_runs.py
        page_investigation.py
      components/
        metric_cards.py
        charts.py
        filters.py
    agent/
      graph.py
      state.py
      prompts.py
      tools.py
      response_formatter.py

  observatory/
    config/
      settings.py
      logging_config.py
    data_generation/
      synthetic_run_generator.py
      benchmark_question_generator.py
      prompt_version_generator.py
    ingestion/
      json_reader.py
      schema_validator.py
      parquet_writer.py
      duckdb_loader.py
    evaluation/
      base_evaluator.py
      sql_evaluator.py
      retrieval_evaluator.py
      tool_call_evaluator.py
      format_evaluator.py
      cost_evaluator.py
      latency_evaluator.py
      overall_score.py
    classification/
      failure_classifier.py
      severity_classifier.py
      recommendation_engine.py
    metadata/
      lineage_builder.py
      catalog_writer.py
      dbt_manifest_parser.py
    warehouse/
      duckdb_connection.py
      queries.py
      migrations.py
    utils/
      time_utils.py
      id_utils.py
      json_utils.py
      file_utils.py

  dbt_project/
    dbt_project.yml
    profiles.yml.example
    models/
      staging/
        stg_agent_runs.sql
        stg_tool_calls.sql
        stg_retrieval_events.sql
        stg_prompt_versions.sql
        stg_evaluation_results.sql
        schema.yml
      intermediate/
        int_run_quality.sql
        int_failure_classification.sql
        int_prompt_performance.sql
        int_model_performance.sql
        int_tool_performance.sql
        schema.yml
      marts/
        mart_agent_reliability.sql
        mart_failure_trends.sql
        mart_prompt_regression.sql
        mart_model_comparison.sql
        mart_cost_latency.sql
        mart_incident_summary.sql
        schema.yml
    macros/
      reliability_score.sql
      safe_divide.sql
    seeds/
      benchmark_questions.csv
      expected_answers.csv
      failure_taxonomy.csv

  data/
    raw/agent_runs/
    processed/parquet/
    warehouse/observatory.duckdb
    metadata/
      catalog.json
      lineage.json

  scripts/
    generate_synthetic_data.py
    initialize_warehouse.py
    run_local_pipeline.py
    run_evaluations.py
    classify_failures.py
    refresh_metadata.py
    demo_questions.py

  tests/
    unit/
      test_agent_run_schema.py
      test_sql_evaluator.py
      test_failure_classifier.py
      test_reliability_score.py
      test_metadata_lineage.py
      test_pydantic_validation.py
    integration/
      test_ingestion_pipeline.py
      test_dbt_outputs.py
      test_dashboard_queries.py
      test_investigation_agent.py
```

---

## Environment Variables

`.env.example`:

```
OBSERVATORY_ENV=local
OBSERVATORY_WAREHOUSE_PATH=data/warehouse/observatory.duckdb
OBSERVATORY_RAW_LOG_DIR=data/raw/agent_runs
OBSERVATORY_PARQUET_DIR=data/processed/parquet
OBSERVATORY_METADATA_DIR=data/metadata
OBSERVATORY_USE_LLM=false
OBSERVATORY_LLM_PROVIDER=ollama
OBSERVATORY_LLM_MODEL=llama3
OBSERVATORY_API_HOST=localhost
OBSERVATORY_API_PORT=8000
OBSERVATORY_LATENCY_THRESHOLD_MS=5000
OBSERVATORY_COST_THRESHOLD_USD=0.005
OBSERVATORY_RELIABILITY_ALERT_THRESHOLD=0.70
OBSERVATORY_CLASSIFICATION_CONFIDENCE_THRESHOLD=0.60
```

`OBSERVATORY_USE_LLM=false` is the default. The full platform runs without it. Set to `true` and configure provider only for investigation agent natural language summaries.

---

## Local Commands

```bash
python scripts/generate_synthetic_data.py     # generate 1M synthetic runs
python scripts/initialize_warehouse.py        # create DuckDB schema
python scripts/run_local_pipeline.py          # ingest + evaluate + classify
python scripts/run_evaluations.py             # run evaluators only
python scripts/classify_failures.py           # run classifier only
python scripts/refresh_metadata.py            # rebuild catalog.json and lineage.json
dbt run                                        # run all dbt models
dbt test                                       # run all dbt tests
streamlit run app/dashboard/streamlit_app.py  # launch dashboard
uvicorn app.api.main:app --reload             # launch API
pytest                                         # run all tests
```

---

## Testing Strategy

### Unit Tests

- Pydantic schema validation including cross-field rules
- Pydantic coercion of dirty input (string latency_ms, missing optional fields)
- Synthetic data generator produces correct failure rate distributions
- SQL evaluator correctly scores valid SQL, syntax errors, missing tables, destructive commands
- Tool evaluator correctly scores success and failure cases
- Retrieval evaluator correctly scores empty and ranked results
- Failure classifier assigns correct category for each failure signal pattern
- Reliability score computation with missing components
- Metadata lineage builder produces valid graph
- DuckDB query helper handles connection errors

### Integration Tests

- Raw JSON to Parquet ingestion including quarantine behavior
- Parquet to DuckDB upsert including duplicate detection
- Full evaluation pipeline output matches expected scores
- Full classification pipeline assigns expected categories
- dbt mart output matches expected metrics for known input
- Dashboard queries return expected shapes against test DuckDB
- Investigation agent tool calls return valid structured output

### Data Quality Tests (dbt)

- Uniqueness on all primary keys
- Not null on all required fields
- Accepted values on task_type, failure_category, severity
- Relationships between all foreign keys
- Score ranges between 0 and 1
- Row count expectations on staging models

---

## Edge Cases

### Ingestion

| Case | Behavior |
|---|---|
| Empty JSON file | Flag in audit log, skip, do not fail DAG |
| Malformed JSON | Quarantine with parse error reason |
| Missing required field | Quarantine with field name and reason |
| Duplicate run_id | Flag as duplicate, keep first occurrence |
| completed_at < started_at | Quarantine, Pydantic model_validator catches this |
| Negative latency_ms | Quarantine, Pydantic validator catches this |
| String latency_ms | Coerce to int via field_validator before_mode |
| File already processed | Skip, log as already processed |

### Evaluation

| Case | Behavior |
|---|---|
| SQL does not parse | SQL score 0.0, store parse error |
| expected_answer missing | Correctness score null, excluded from overall |
| Evaluator crashes | Store error, mark component as failed, continue |
| Unsupported task type | Mark clearly, do not compute irrelevant component scores |
| Final answer empty | Format score 0.0 |

### Investigation Agent

| Case | Behavior |
|---|---|
| Ambiguous time window | Default to last 7 days, state assumption explicitly |
| Metric not available | Say metric is not available, do not invent it |
| Raw SQL in user input | Reject, explain only natural language questions are accepted |
| Query returns zero rows | Return zero rows result, do not fabricate a trend |
| LLM disabled | Return structured metric data, skip natural language summary |
| Warehouse unreachable | Return clear error with remediation steps |

---

## Cost Statement

Base project: $0.00

Optional LLM for investigation agent:
- Provider: gpt-4o-mini or claude-haiku-3
- Called: once per human investigation query
- Estimated cost per query: $0.0001 to $0.0003
- $15 budget: approximately 50,000 to 75,000 investigation queries
- Per-run LLM evaluation: explicitly not used

LLM is disabled by default. Set `OBSERVATORY_USE_LLM=true` to enable.

---

## Implementation Rules For Cursor

- Every file must contain working code, documentation, configuration, or tests. No empty files.
- Use explicit imports in every Python file.
- Use type hints in all functions.
- Use Pydantic v2 features: model_validator, field_validator, computed_field, ConfigDict.
- Use classes where domain boundaries are clear.
- Use docstrings on all public functions.
- Use pytest for all tests.
- Use relative paths everywhere. No hardcoded absolute paths.
- Do not call LLM APIs during evaluation. Evaluation is deterministic.
- Do not call LLM APIs during classification. Classification is rule-based.
- LLM is called only in the investigation agent, only when OBSERVATORY_USE_LLM=true.
- Do not silently ignore invalid records. Quarantine them with a reason.
- Do not overwrite last good metadata on refresh failure.
- Do not allow raw SQL from user input into DuckDB.
- Do not expose internal paths, table names, or warehouse location through the API.
- The dashboard must not crash on empty data, null metrics, or missing warehouse file.
- The investigation agent must work in degraded mode when LLM is disabled.

---

## Build Order For Cursor

Build in this exact order. Do not skip phases.

1. Repository structure and settings
2. Pydantic v2 schemas with full validation
3. Synthetic data generator with configurable failure rates
4. DuckDB initialization and migrations
5. Ingestion pipeline with quarantine
6. Evaluation engine (all evaluators, overall score)
7. Failure classifier and severity engine
8. dbt project with staging, intermediate, mart models and tests
9. Local pipeline script connecting all steps
10. Streamlit dashboard all six pages
11. FastAPI routes
12. LangGraph investigation agent with metric tools
13. Metadata and lineage layer
14. Airflow DAGs
15. Migration parity DAG
16. Unit and integration tests
17. README and docs

---

## Interview Story

I built AI Failure Observatory because AI agents are being deployed into production workflows, but teams lack visibility into why they fail. Standard logs show that a request failed, not whether the root cause was the prompt, model, retrieval, tool call, SQL generation, or the data pipeline upstream of the agent.

The core architectural decision was to separate evaluation from investigation. Every run is scored by deterministic evaluators — no LLM involved. dbt aggregates those scores into reliability metrics. Only when a human asks a question does an LLM get called, and it reads aggregated metrics, not raw logs. One natural language query can summarize a million runs at a cost of fractions of a cent.

The platform combines Airflow for orchestration, dbt for transformation, DuckDB as the analytical warehouse, Streamlit for observability dashboards, FastAPI for the log collection layer, and LangGraph for the investigation agent. I also built prompt regression detection, model comparison scoring, a failure taxonomy with severity levels, a lightweight metadata and lineage layer, and a simulated Airflow 2 to 3 migration parity workflow.

---

## Resume Bullets

**Data Engineering:**
Built an Airflow and dbt powered data platform that ingests AI agent execution logs, validates schemas with Pydantic v2, transforms event data into DuckDB reliability marts, and monitors failure trends across prompts, models, tools, and task types at 1M+ run scale.

**AI Engineering:**
Built a deterministic AI evaluation engine that scores LangGraph-style agent runs across correctness, SQL quality, tool usage, retrieval relevance, format compliance, latency, and cost — then uses a LangGraph investigation agent to answer natural language root cause questions against aggregated metrics at near-zero LLM cost.

**Software Engineering:**
Designed a modular Python observability platform with FastAPI, DuckDB, dbt, Airflow, Streamlit, and pytest, using Pydantic v2 model validators and computed fields for contract enforcement, parameterized read-only DuckDB queries for safe investigation, and deterministic failure classification with quarantine and audit logging.

**Platform Engineering:**
Built a local-first AI observability system with orchestration, data quality checks, metadata lineage, failure quarantine, retry-aware pipelines, and Airflow migration parity validation — designed so LLM API cost stays near zero by calling the model once per human query against pre-aggregated metrics rather than once per agent run.