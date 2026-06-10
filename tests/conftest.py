"""Shared pytest fixtures."""

import shutil
from pathlib import Path

import pytest

from observatory.config.settings import Settings, get_settings
from observatory.warehouse.migrations import initialize_warehouse_schema


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Isolated settings with temp directories."""
    get_settings.cache_clear()
    settings = Settings(
        env="test",
        warehouse_path=tmp_path / "warehouse" / "test.duckdb",
        raw_log_dir=tmp_path / "raw",
        parquet_dir=tmp_path / "parquet",
        quarantine_dir=tmp_path / "quarantine",
        metadata_dir=tmp_path / "metadata",
        default_run_count=200,
        default_seed=99,
    )
    settings.ensure_directories()
    yield settings
    get_settings.cache_clear()


@pytest.fixture
def initialized_db(test_settings: Settings):
    """Initialize warehouse schema in temp db."""
    initialize_warehouse_schema(test_settings, force=True)
    return test_settings
