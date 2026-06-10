#!/usr/bin/env python3
"""Run full local pipeline: init → ingest → evaluate → classify → dbt."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observatory.config.logging_config import configure_logging, get_logger
from observatory.config.settings import get_settings
from observatory.classification.engine import ClassificationEngine
from observatory.evaluation.engine import EvaluationEngine
from observatory.ingestion.pipeline import IngestionPipeline
from observatory.warehouse.migrations import initialize_warehouse_schema
from observatory.warehouse.queries import count_table

logger = get_logger(__name__)


def write_dbt_profiles(dbt_dir: Path, warehouse_path: Path) -> None:
    """Write dbt profiles.yml pointing at the project warehouse."""
    profiles = dbt_dir / "profiles.yml"
    profiles.write_text(f"""observatory:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: '{warehouse_path.resolve()}'
      schema: main
      threads: 4
""")


def run_dbt(project_root: Path, warehouse_path: Path) -> None:
    dbt_dir = project_root / "dbt_project"
    write_dbt_profiles(dbt_dir, warehouse_path)
    result = subprocess.run(
        ["dbt", "run", "--project-dir", str(dbt_dir), "--profiles-dir", str(dbt_dir)],
        capture_output=True, text=True, cwd=str(project_root),
    )
    if result.returncode != 0:
        logger.error("dbt run failed:\n%s", result.stderr)
        raise RuntimeError("dbt run failed")
    logger.info("dbt run completed")
    test_result = subprocess.run(
        ["dbt", "test", "--project-dir", str(dbt_dir), "--profiles-dir", str(dbt_dir)],
        capture_output=True, text=True, cwd=str(project_root),
    )
    if test_result.returncode != 0:
        logger.warning("dbt test had failures:\n%s", test_result.stderr)
    else:
        logger.info("dbt test passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local pipeline")
    parser.add_argument("--skip-dbt", action="store_true")
    parser.add_argument("--skip-generate", action="store_true")
    parser.add_argument("--count", type=int, default=None)
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    root = settings.project_root()

    initialize_warehouse_schema(settings)
    logger.info("Warehouse initialized")

    if not args.skip_generate:
        from scripts.generate_synthetic_data import main as gen_main
        sys.argv = ["generate_synthetic_data.py"]
        if args.count:
            sys.argv += ["--count", str(args.count)]
        gen_main()

    ingestion = IngestionPipeline(settings)
    summary = ingestion.run()
    logger.info("Ingestion: %d valid, %d invalid, %d duplicates",
                summary.valid_records, summary.invalid_records, summary.duplicate_records)

    eval_count = EvaluationEngine(settings).run()
    logger.info("Evaluated %d runs", eval_count)

    class_count = ClassificationEngine(settings).run()
    logger.info("Classified %d runs", class_count)

    if not args.skip_dbt:
        run_dbt(root, settings.resolve_path(settings.warehouse_path))

    logger.info("Pipeline complete. Runs=%d Evals=%d Failures=%d Quarantine=%d",
                count_table("agent_runs", settings),
                count_table("evaluation_results", settings),
                count_table("failure_modes", settings),
                count_table("quarantine_records", settings))


if __name__ == "__main__":
    main()
