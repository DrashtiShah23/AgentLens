"""Load validated records into DuckDB with duplicate detection."""

from __future__ import annotations

import json
from typing import Any, Optional

import pandas as pd

from observatory.config.settings import Settings, get_settings
from observatory.utils.id_utils import generate_uuid
from observatory.warehouse.duckdb_connection import connection_context


class DuckDBLoader:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def load_agent_runs(self, records: list[dict[str, Any]]) -> tuple[int, int]:
        if not records:
            return 0, 0
        seen: set[str] = set()
        to_insert: list[dict[str, Any]] = []
        duplicates = 0
        with connection_context(self.settings) as conn:
            existing = {r[0] for r in conn.execute("SELECT run_id FROM agent_runs").fetchall()}
            for rec in records:
                rid = rec["run_id"]
                is_dup = rid in seen or rid in existing
                if is_dup:
                    duplicates += 1
                seen.add(rid)
                row = dict(rec)
                row["is_duplicate"] = is_dup
                if row.get("metadata") is not None and not isinstance(row["metadata"], str):
                    row["metadata"] = json.dumps(row["metadata"])
                to_insert.append(row)
            df = pd.DataFrame(to_insert)
            conn.register("_runs_df", df)
            conn.execute("""
                INSERT OR REPLACE INTO agent_runs
                SELECT run_id, agent_name, task_type, user_query, prompt_version_id, model_name,
                       started_at, completed_at, latency_ms, input_tokens, output_tokens,
                       estimated_cost_usd, final_answer, success_flag, error_message,
                       generated_sql, expected_answer, metadata, is_duplicate, CURRENT_TIMESTAMP
                FROM _runs_df
            """)
        return len(to_insert), duplicates

    def load_tool_calls(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        rows = []
        for rec in records:
            row = dict(rec)
            for key in ("tool_input", "tool_output"):
                if row.get(key) is not None and not isinstance(row[key], str):
                    row[key] = json.dumps(row[key])
            rows.append(row)
        with connection_context(self.settings) as conn:
            df = pd.DataFrame(rows)
            conn.register("_tools_df", df)
            conn.execute("""
                INSERT OR REPLACE INTO tool_calls
                SELECT tool_call_id, run_id, tool_name, tool_input, tool_output, tool_status,
                       error_message, started_at, completed_at, latency_ms, CURRENT_TIMESTAMP
                FROM _tools_df
            """)
        return len(rows)

    def load_retrieval_events(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        with connection_context(self.settings) as conn:
            df = pd.DataFrame(records)
            conn.register("_ret_df", df)
            conn.execute("""
                INSERT OR REPLACE INTO retrieval_events
                SELECT retrieval_id, run_id, query_text, document_id, chunk_text,
                       rank_position, relevance_score, was_used_in_answer, CURRENT_TIMESTAMP
                FROM _ret_df
            """)
        return len(records)

    def load_prompt_versions(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        with connection_context(self.settings) as conn:
            df = pd.DataFrame(records)
            conn.register("_pv_df", df)
            conn.execute("""
                INSERT OR REPLACE INTO prompt_versions
                SELECT prompt_version_id, agent_name, prompt_name, prompt_text, created_at,
                       active_flag, change_reason, CURRENT_TIMESTAMP FROM _pv_df
            """)
        return len(records)

    def write_quarantine(self, source_file: str, record_type: str,
                         raw_payload: dict[str, Any], rejection_reason: str) -> str:
        qid = generate_uuid()
        with connection_context(self.settings) as conn:
            conn.execute(
                """INSERT INTO quarantine_records
                   (quarantine_id, source_file, record_type, raw_payload, rejection_reason)
                   VALUES (?, ?, ?, ?, ?)""",
                [qid, source_file, record_type, json.dumps(raw_payload), rejection_reason],
            )
        return qid

    def write_audit(self, source_file: str, checksum: str | None, total: int,
                    valid: int, invalid: int, duplicates: int, status: str,
                    notes: str | None = None) -> str:
        aid = generate_uuid()
        with connection_context(self.settings) as conn:
            conn.execute(
                """INSERT INTO ingestion_audit
                   (audit_id, source_file, file_checksum, total_records, valid_records,
                    invalid_records, duplicate_records, status, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [aid, source_file, checksum, total, valid, invalid, duplicates, status, notes],
            )
        return aid
