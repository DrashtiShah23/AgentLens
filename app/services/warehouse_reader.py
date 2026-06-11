"""Read-only DuckDB access for dashboard, API, and investigation agent."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import duckdb
import pandas as pd

from observatory.config.settings import Settings, get_settings
from observatory.warehouse.duckdb_connection import connection_context


class WarehouseUnavailableError(Exception):
    """Raised when the warehouse file is missing or unreachable."""


ALLOWED_TABLES = frozenset({
    "agent_runs", "tool_calls", "retrieval_events", "prompt_versions",
    "evaluation_results", "failure_modes",
    "stg_agent_runs", "stg_evaluation_results", "stg_tool_calls",
    "stg_retrieval_events", "stg_prompt_versions",
    "int_run_quality", "int_failure_classification", "int_prompt_performance",
    "int_model_performance", "int_tool_performance",
    "mart_agent_reliability", "mart_failure_trends", "mart_prompt_regression",
    "mart_model_comparison", "mart_cost_latency", "mart_incident_summary",
})

MAX_ROWS = 1000


class WarehouseReader:
    """Safe read-only warehouse queries."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._db_path = self.settings.resolve_path(self.settings.warehouse_path)

    @property
    def db_path_exists(self) -> bool:
        return self._db_path.exists()

    def ensure_available(self) -> None:
        if not self.db_path_exists:
            raise WarehouseUnavailableError(
                "Analytics warehouse is not available. Run: python scripts/run_local_pipeline.py"
            )

    def table_exists(self, table_name: str) -> bool:
        if table_name not in ALLOWED_TABLES:
            return False
        if not self.db_path_exists:
            return False
        try:
            with connection_context(self.settings, read_only=True) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                    [table_name],
                ).fetchone()
                return bool(row and row[0] > 0)
        except Exception:
            return False

    def query_df(self, sql: str, params: Optional[list[Any]] = None) -> pd.DataFrame:
        self.ensure_available()
        with connection_context(self.settings, read_only=True) as conn:
            if params:
                return conn.execute(sql, params).fetchdf()
            return conn.execute(sql).fetchdf()

    def safe_query(
        self,
        sql: str,
        params: Optional[list[Any]] = None,
        limit: int = MAX_ROWS,
    ) -> pd.DataFrame:
        """Run query; return empty DataFrame on missing tables or errors."""
        if not self.db_path_exists:
            return pd.DataFrame()
        try:
            wrapped = f"SELECT * FROM ({sql}) q LIMIT {int(limit)}"
            return self.query_df(wrapped, params)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def default_start_date(days: int = 7) -> date:
        return date.today() - timedelta(days=days)
