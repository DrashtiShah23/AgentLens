"""End-to-end ingestion pipeline with quarantine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.api.schemas.agent_run import AgentRun
from app.api.schemas.prompt_version import PromptVersion
from app.api.schemas.retrieval_event import RetrievalEvent
from app.api.schemas.tool_call import ToolCall
from observatory.config.settings import Settings, get_settings
from observatory.ingestion.duckdb_loader import DuckDBLoader
from observatory.ingestion.json_reader import read_json_file
from observatory.ingestion.parquet_writer import write_parquet
from observatory.ingestion.schema_validator import validate_record
from observatory.utils.file_utils import file_checksum, list_json_files
from observatory.utils.id_utils import generate_uuid


@dataclass
class IngestionSummary:
    files_processed: int = 0
    files_skipped: int = 0
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    parquet_files: list[str] = field(default_factory=list)
    audit_ids: list[str] = field(default_factory=list)


class IngestionPipeline:
    RECORD_TYPE_MAP = {
        "agent_runs": AgentRun,
        "tool_calls": ToolCall,
        "retrieval_events": RetrievalEvent,
        "prompt_versions": PromptVersion,
    }

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.loader = DuckDBLoader(self.settings)
        self._processed_files: set[str] = set()

    def run(self, raw_dir: Optional[Path] = None) -> IngestionSummary:
        summary = IngestionSummary()
        raw = self.settings.resolve_path(raw_dir or self.settings.raw_log_dir)
        parquet_base = self.settings.resolve_path(self.settings.parquet_dir)

        for path in list_json_files(raw):
            fname = path.name
            if fname in self._processed_files:
                summary.files_skipped += 1
                continue

            read_result = read_json_file(path)
            if read_result.is_empty:
                self.loader.write_audit(fname, file_checksum(path), 0, 0, 0, 0, "empty_file",
                                        "file is empty")
                summary.files_processed += 1
                continue

            if read_result.parse_errors:
                for err in read_result.parse_errors:
                    self.loader.write_quarantine(fname, "parse_error", {"file": fname}, err)
                    self.loader.write_audit(fname, file_checksum(path), 0, 0, 1, 0, "parse_error", err)
                summary.invalid_records += 1
                summary.files_processed += 1
                continue

            record_type = self._detect_type(read_result.records, fname)
            model_cls = self.RECORD_TYPE_MAP.get(record_type, AgentRun)
            valid_rows: list[dict[str, Any]] = []
            invalid_count = 0
            dup_count = 0

            for raw_rec in read_result.records:
                outcome = validate_record(raw_rec, model_cls)
                if not outcome.valid:
                    self.loader.write_quarantine(fname, record_type, raw_rec,
                                                 outcome.rejection_reason or "validation failed")
                    invalid_count += 1
                    continue
                valid_rows.append(outcome.model.model_dump(mode="json"))  # type: ignore[union-attr]

            summary.total_records += len(read_result.records)

            if record_type == "agent_runs":
                loaded, dup_count = self.loader.load_agent_runs(valid_rows)
                summary.valid_records += loaded - dup_count
                summary.duplicate_records += dup_count
            elif record_type == "tool_calls":
                summary.valid_records += self.loader.load_tool_calls(valid_rows)
            elif record_type == "retrieval_events":
                summary.valid_records += self.loader.load_retrieval_events(valid_rows)
            elif record_type == "prompt_versions":
                summary.valid_records += self.loader.load_prompt_versions(valid_rows)
            else:
                summary.valid_records += len(valid_rows)

            summary.invalid_records += invalid_count
            if valid_rows:
                pq_path = parquet_base / record_type / f"{path.stem}.parquet"
                write_parquet(valid_rows, pq_path)
                try:
                    summary.parquet_files.append(str(pq_path.relative_to(self.settings.project_root())))
                except ValueError:
                    summary.parquet_files.append(str(pq_path))

            audit_id = self.loader.write_audit(
                fname, file_checksum(path), len(read_result.records),
                len(valid_rows), invalid_count, dup_count,
                "success" if invalid_count == 0 else "partial_success",
            )
            summary.audit_ids.append(audit_id)
            summary.files_processed += 1
            self._processed_files.add(fname)

        return summary

    def _detect_type(self, records: list[dict[str, Any]], filename: str) -> str:
        if "tool_calls" in filename:
            return "tool_calls"
        if "retrieval" in filename:
            return "retrieval_events"
        if "prompt" in filename:
            return "prompt_versions"
        if records:
            sample = records[0]
            if "tool_call_id" in sample:
                return "tool_calls"
            if "retrieval_id" in sample:
                return "retrieval_events"
            if "prompt_text" in sample:
                return "prompt_versions"
        return "agent_runs"
