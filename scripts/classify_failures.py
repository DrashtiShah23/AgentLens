#!/usr/bin/env python3
"""Classify failures for low-scoring runs."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observatory.config.logging_config import configure_logging, get_logger
from observatory.classification.engine import ClassificationEngine

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify failures")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=0.70)
    args = parser.parse_args()

    configure_logging()
    engine = ClassificationEngine(score_threshold=args.threshold)
    count = engine.run(limit=args.limit)
    logger.info("Classified %d runs", count)


if __name__ == "__main__":
    main()
