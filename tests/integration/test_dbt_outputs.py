import json
import shutil
import subprocess
from pathlib import Path

import pytest

from observatory.data_generation.synthetic_run_generator import SyntheticRunGenerator
from observatory.evaluation.engine import EvaluationEngine
from observatory.ingestion.pipeline import IngestionPipeline
from observatory.warehouse.migrations import initialize_warehouse_schema


@pytest.fixture
def dbt_ready_db(test_settings, tmp_path):
    settings = test_settings
    initialize_warehouse_schema(settings, force=True)
    raw = settings.resolve_path(settings.raw_log_dir)
    batch = SyntheticRunGenerator(seed=3).generate_batch(300)
    with (raw / "runs.json").open("w") as f:
        json.dump({"records": batch.agent_runs}, f)
    with (raw / "tools.json").open("w") as f:
        json.dump({"records": batch.tool_calls}, f)
    with (raw / "retrieval.json").open("w") as f:
        json.dump({"records": batch.retrieval_events}, f)
    IngestionPipeline(settings).run()
    EvaluationEngine(settings).run()
    return settings


def test_dbt_models_build(dbt_ready_db, test_settings):
    root = test_settings.project_root()
    dbt_dir = root / "dbt_project"
    profiles = dbt_dir / "profiles.yml"
    db_path = test_settings.resolve_path(test_settings.warehouse_path)
    profiles.write_text(f"""observatory:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: '{db_path}'
      schema: main
      threads: 2
""")
    result = subprocess.run(
        ["dbt", "run", "--project-dir", str(dbt_dir), "--profiles-dir", str(dbt_dir)],
        capture_output=True, text=True, cwd=str(root),
    )
    assert result.returncode == 0, result.stderr + result.stdout

    import duckdb
    conn = duckdb.connect(str(db_path))
    tables = [
        "stg_agent_runs", "mart_agent_reliability", "mart_prompt_regression",
        "mart_failure_trends", "mart_model_comparison",
    ]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count >= 0
    conn.close()
