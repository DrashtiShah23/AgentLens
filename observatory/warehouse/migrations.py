from pathlib import Path
from typing import Optional

from observatory.config.settings import Settings, get_settings
from observatory.warehouse.duckdb_connection import get_connection

SCHEMA_VERSION = 1

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_runs (
    run_id VARCHAR PRIMARY KEY,
    agent_name VARCHAR NOT NULL,
    task_type VARCHAR NOT NULL,
    user_query VARCHAR NOT NULL,
    prompt_version_id VARCHAR NOT NULL,
    model_name VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    latency_ms INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    estimated_cost_usd DOUBLE NOT NULL,
    final_answer VARCHAR NOT NULL,
    success_flag BOOLEAN NOT NULL,
    error_message VARCHAR,
    generated_sql VARCHAR,
    expected_answer VARCHAR,
    metadata JSON,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    tool_name VARCHAR NOT NULL,
    tool_input JSON NOT NULL,
    tool_output JSON,
    tool_status VARCHAR NOT NULL,
    error_message VARCHAR,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    latency_ms INTEGER NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS retrieval_events (
    retrieval_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    query_text VARCHAR NOT NULL,
    document_id VARCHAR NOT NULL,
    chunk_text VARCHAR NOT NULL,
    rank_position INTEGER NOT NULL,
    relevance_score DOUBLE NOT NULL,
    was_used_in_answer BOOLEAN NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    prompt_version_id VARCHAR NOT NULL,
    agent_name VARCHAR NOT NULL,
    prompt_name VARCHAR NOT NULL,
    prompt_text VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    active_flag BOOLEAN NOT NULL,
    change_reason VARCHAR NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (prompt_version_id, agent_name)
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    evaluation_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    correctness_score DOUBLE,
    sql_score DOUBLE,
    tool_score DOUBLE,
    retrieval_score DOUBLE,
    format_score DOUBLE,
    latency_score DOUBLE,
    cost_score DOUBLE,
    overall_score DOUBLE NOT NULL,
    failure_category VARCHAR,
    severity VARCHAR,
    evaluator_notes VARCHAR,
    evaluated_at TIMESTAMP NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS failure_modes (
    failure_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    primary_category VARCHAR NOT NULL,
    secondary_signals JSON,
    confidence_score DOUBLE NOT NULL,
    severity VARCHAR NOT NULL,
    recommendation VARCHAR,
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    classified_at TIMESTAMP NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quarantine_records (
    quarantine_id VARCHAR PRIMARY KEY,
    source_file VARCHAR NOT NULL,
    record_type VARCHAR NOT NULL,
    raw_payload JSON NOT NULL,
    rejection_reason VARCHAR NOT NULL,
    rejected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_audit (
    audit_id VARCHAR PRIMARY KEY,
    source_file VARCHAR NOT NULL,
    file_checksum VARCHAR,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_records INTEGER NOT NULL DEFAULT 0,
    valid_records INTEGER NOT NULL DEFAULT 0,
    invalid_records INTEGER NOT NULL DEFAULT 0,
    duplicate_records INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL,
    notes VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_runs_agent ON agent_runs(agent_name);
CREATE INDEX IF NOT EXISTS idx_runs_prompt ON agent_runs(prompt_version_id);
CREATE INDEX IF NOT EXISTS idx_tool_run ON tool_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_run ON retrieval_events(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_run ON evaluation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_failure_run ON failure_modes(run_id);
"""


def initialize_warehouse_schema(settings: Optional[Settings] = None, force: bool = False) -> Path:
    s = settings or get_settings()
    db_path = s.resolve_path(s.warehouse_path)
    if force and db_path.exists():
        db_path.unlink()
    s.ensure_directories()
    conn = get_connection(s)
    try:
        conn.execute(DDL)
        row = conn.execute("SELECT version FROM schema_migrations WHERE version = ?", [SCHEMA_VERSION]).fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", [SCHEMA_VERSION])
    finally:
        conn.close()
    return db_path
