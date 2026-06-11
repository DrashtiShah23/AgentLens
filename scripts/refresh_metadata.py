#!/usr/bin/env python3
"""Refresh catalog.json and lineage.json from dbt manifest."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observatory.config.logging_config import configure_logging, get_logger
from observatory.metadata.catalog_writer import CatalogWriter

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    writer = CatalogWriter()
    try:
        catalog_path, lineage_path = writer.refresh()
        logger.info("Catalog written: %s", catalog_path)
        logger.info("Lineage written: %s", lineage_path)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Metadata refresh failed (last known good preserved): %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
