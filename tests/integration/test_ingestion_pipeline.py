import json
from datetime import datetime, timezone
from pathlib import Path

from observatory.data_generation.synthetic_run_generator import SyntheticRunGenerator
from observatory.ingestion.pipeline import IngestionPipeline
from observatory.warehouse.queries import count_table


def test_ingestion_quarantine_and_valid_load(initialized_db):
    settings = initialized_db
    raw = settings.resolve_path(settings.raw_log_dir)
    gen = SyntheticRunGenerator(seed=7)
    batch = gen.generate_batch(100)

    with (raw / "agent_runs_test.json").open("w") as f:
        json.dump({"records": batch.agent_runs}, f)
    with (raw / "agent_runs_malformed.json").open("w") as f:
        json.dump({"records": batch.malformed_records}, f)

    pipeline = IngestionPipeline(settings)
    summary = pipeline.run()

    assert summary.valid_records > 0
    assert summary.invalid_records > 0
    assert count_table("agent_runs", settings) > 0
    assert count_table("quarantine_records", settings) > 0
    assert count_table("ingestion_audit", settings) > 0


def test_empty_file_handled(initialized_db):
    settings = initialized_db
    raw = settings.resolve_path(settings.raw_log_dir)
    (raw / "empty.json").write_text("")
    summary = IngestionPipeline(settings).run()
    assert summary.files_processed >= 1


def test_malformed_json_quarantined(initialized_db):
    settings = initialized_db
    raw = settings.resolve_path(settings.raw_log_dir)
    (raw / "bad.json").write_text("{not valid json")
    IngestionPipeline(settings).run()
    assert count_table("quarantine_records", settings) >= 1
