#!/usr/bin/env python3
"""Run deterministic evaluations on unevaluated runs."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observatory.config.logging_config import configure_logging, get_logger
from observatory.evaluation.engine import EvaluationEngine

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluations")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    configure_logging()
    engine = EvaluationEngine()
    count = engine.run(limit=args.limit)
    logger.info("Evaluated %d runs", count)


if __name__ == "__main__":
    main()
