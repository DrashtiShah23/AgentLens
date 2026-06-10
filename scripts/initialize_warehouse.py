#!/usr/bin/env python3
"""Initialize DuckDB warehouse schema."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observatory.config.logging_config import configure_logging, get_logger
from observatory.config.settings import get_settings
from observatory.warehouse.migrations import initialize_warehouse_schema

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize DuckDB warehouse")
    parser.add_argument("--force", action="store_true", help="Delete and recreate database")
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    db_path = initialize_warehouse_schema(settings, force=args.force)
    logger.info("Warehouse initialized at %s", db_path)


if __name__ == "__main__":
    main()
