#!/usr/bin/env python3
"""Generate synthetic agent run data."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observatory.config.logging_config import configure_logging, get_logger
from observatory.config.settings import get_settings
from observatory.data_generation.prompt_version_generator import generate_prompt_versions
from observatory.data_generation.synthetic_run_generator import SyntheticRunGenerator
from observatory.utils.json_utils import write_json

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic agent run data")
    parser.add_argument("--count", type=int, default=None, help="Number of runs to generate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--batch-size", type=int, default=5000, help="Records per JSON file")
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    count = args.count or settings.default_run_count
    seed = args.seed or settings.default_seed
    raw_dir = settings.resolve_path(settings.raw_log_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    generator = SyntheticRunGenerator(seed=seed)
    batch = generator.generate_batch(count)

    # Write agent runs in batches
    for i in range(0, len(batch.agent_runs), args.batch_size):
        chunk = batch.agent_runs[i:i + args.batch_size]
        write_json(raw_dir / f"agent_runs_{i // args.batch_size:04d}.json", {"records": chunk})

    # Malformed records in separate file for quarantine testing
    if batch.malformed_records:
        write_json(raw_dir / "agent_runs_malformed.json", {"records": batch.malformed_records})

    write_json(raw_dir / "tool_calls.json", {"records": batch.tool_calls})
    write_json(raw_dir / "retrieval_events.json", {"records": batch.retrieval_events})

    prompt_versions = generate_prompt_versions()
    write_json(raw_dir / "prompt_versions.json", {
        "records": [p.model_dump(mode="json") for p in prompt_versions],
    })

    logger.info("Generated %d agent runs (%d malformed)", len(batch.agent_runs), len(batch.malformed_records))
    logger.info("Scenario distribution: %s", batch.scenario_counts)
    logger.info("Output directory: %s", raw_dir)


if __name__ == "__main__":
    main()
