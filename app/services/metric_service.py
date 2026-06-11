"""High-level metric queries for dashboard and API."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pandas as pd

from app.services.warehouse_reader import WarehouseReader
from observatory.config.settings import Settings, get_settings


class MetricService:
    """Aggregated metrics from DuckDB marts and raw tables."""

    def __init__(self, reader: Optional[WarehouseReader] = None,
                 settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.reader = reader or WarehouseReader(self.settings)

    def overview_metrics(self, days: int = 7) -> dict[str, Any]:
        start = WarehouseReader.default_start_date(days)
        if not self.reader.db_path_exists:
            return self._empty_overview()

        runs = self.reader.safe_query(
            """SELECT COUNT(*) AS total_runs,
                      AVG(e.overall_score) AS reliability_score,
                      AVG(r.latency_ms) AS avg_latency_ms,
                      SUM(r.estimated_cost_usd) AS total_cost_usd,
                      AVG(CASE WHEN e.overall_score < 0.7 THEN 1.0 ELSE 0.0 END) AS failure_rate
               FROM agent_runs r
               JOIN evaluation_results e ON r.run_id = e.run_id
               WHERE r.is_duplicate = FALSE AND CAST(r.started_at AS DATE) >= ?""",
            [start.isoformat()],
            limit=1,
        )
        failures = self.reader.safe_query(
            """SELECT primary_category, COUNT(*) AS cnt
               FROM failure_modes f
               JOIN agent_runs r ON f.run_id = r.run_id
               WHERE CAST(f.classified_at AS DATE) >= ?
               GROUP BY 1 ORDER BY cnt DESC LIMIT 1""",
            [start.isoformat()], limit=1,
        )
        agents = self.reader.safe_query(
            """SELECT r.agent_name, COUNT(*) AS cnt
               FROM failure_modes f JOIN agent_runs r ON f.run_id = r.run_id
               WHERE CAST(f.classified_at AS DATE) >= ?
               GROUP BY 1 ORDER BY cnt DESC LIMIT 1""",
            [start.isoformat()], limit=1,
        )
        prompts = self.reader.safe_query(
            """SELECT r.prompt_version_id, COUNT(*) AS cnt
               FROM failure_modes f JOIN agent_runs r ON f.run_id = r.run_id
               WHERE CAST(f.classified_at AS DATE) >= ?
               GROUP BY 1 ORDER BY cnt DESC LIMIT 1""",
            [start.isoformat()], limit=1,
        )
        row = runs.iloc[0] if not runs.empty else {}
        return {
            "time_window_days": days,
            "total_runs": int(row.get("total_runs") or 0),
            "reliability_score": _safe_float(row.get("reliability_score")),
            "failure_rate": _safe_float(row.get("failure_rate")),
            "avg_latency_ms": _safe_float(row.get("avg_latency_ms")),
            "total_cost_usd": _safe_float(row.get("total_cost_usd")),
            "top_failure_category": failures.iloc[0]["primary_category"] if not failures.empty else None,
            "top_affected_agent": agents.iloc[0]["agent_name"] if not agents.empty else None,
            "top_affected_prompt": prompts.iloc[0]["prompt_version_id"] if not prompts.empty else None,
        }

    def reliability_over_time(self, days: int = 7) -> pd.DataFrame:
        start = WarehouseReader.default_start_date(days)
        if self.reader.table_exists("mart_agent_reliability"):
            return self.reader.safe_query(
                """SELECT run_date,
                          SUM(reliability_score * total_runs) / NULLIF(SUM(total_runs), 0) AS reliability_score,
                          SUM(failure_rate * total_runs) / NULLIF(SUM(total_runs), 0) AS failure_rate,
                          SUM(total_runs) AS total_runs
                   FROM mart_agent_reliability
                   WHERE run_date >= ? GROUP BY run_date ORDER BY run_date""",
                [start.isoformat()],
            )
        return self.reader.safe_query(
            """SELECT CAST(r.started_at AS DATE) AS run_date,
                      AVG(e.overall_score) AS reliability_score,
                      AVG(CASE WHEN e.overall_score < 0.7 THEN 1.0 ELSE 0.0 END) AS failure_rate,
                      COUNT(*) AS total_runs
               FROM agent_runs r JOIN evaluation_results e ON r.run_id = e.run_id
               WHERE r.is_duplicate = FALSE AND CAST(r.started_at AS DATE) >= ?
               GROUP BY 1 ORDER BY 1""",
            [start.isoformat()],
        )

    def failures_by_category(self, days: int = 7) -> pd.DataFrame:
        start = WarehouseReader.default_start_date(days)
        if self.reader.table_exists("mart_failure_trends"):
            return self.reader.safe_query(
                """SELECT failure_category, SUM(failure_count) AS failure_count
                   FROM mart_failure_trends WHERE failure_date >= ?
                   GROUP BY failure_category ORDER BY failure_count DESC""",
                [start.isoformat()],
            )
        return self.reader.safe_query(
            """SELECT primary_category AS failure_category, COUNT(*) AS failure_count
               FROM failure_modes WHERE CAST(classified_at AS DATE) >= ?
               GROUP BY 1 ORDER BY failure_count DESC""",
            [start.isoformat()],
        )

    def failure_records(
        self,
        days: int = 30,
        severity: Optional[str] = None,
        agent_name: Optional[str] = None,
        prompt_version_id: Optional[str] = None,
        failure_category: Optional[str] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        start = WarehouseReader.default_start_date(days)
        clauses = ["CAST(f.classified_at AS DATE) >= ?"]
        params: list[Any] = [start.isoformat()]
        if severity:
            clauses.append("f.severity = ?")
            params.append(severity)
        if agent_name:
            clauses.append("r.agent_name = ?")
            params.append(agent_name)
        if prompt_version_id:
            clauses.append("r.prompt_version_id = ?")
            params.append(prompt_version_id)
        if failure_category:
            clauses.append("f.primary_category = ?")
            params.append(failure_category)
        where = " AND ".join(clauses)
        return self.reader.safe_query(
            f"""SELECT f.failure_id, f.run_id, f.primary_category AS failure_category,
                       f.severity, f.confidence_score, f.recommendation, f.requires_human_review,
                       r.agent_name, r.prompt_version_id, r.user_query, r.final_answer,
                       f.classified_at
                FROM failure_modes f JOIN agent_runs r ON f.run_id = r.run_id
                WHERE {where} ORDER BY f.classified_at DESC""",
            params, limit=limit,
        )

    def prompt_performance(self) -> pd.DataFrame:
        if self.reader.table_exists("mart_prompt_regression"):
            return self.reader.safe_query(
                """SELECT prompt_version_id, agent_name, change_reason, reliability_score,
                          failure_rate, avg_latency_ms, avg_cost_usd, regression_detected, run_count
                   FROM mart_prompt_regression ORDER BY reliability_score""",
            )
        return self.reader.safe_query(
            """SELECT r.prompt_version_id, r.agent_name,
                      AVG(e.overall_score) AS reliability_score,
                      AVG(CASE WHEN e.overall_score < 0.7 THEN 1.0 ELSE 0.0 END) AS failure_rate,
                      AVG(r.latency_ms) AS avg_latency_ms,
                      AVG(r.estimated_cost_usd) AS avg_cost_usd,
                      COUNT(*) AS run_count,
                      FALSE AS regression_detected, '' AS change_reason
               FROM agent_runs r JOIN evaluation_results e ON r.run_id = e.run_id
               WHERE r.is_duplicate = FALSE
               GROUP BY r.prompt_version_id, r.agent_name""",
        )

    def model_performance(self) -> pd.DataFrame:
        if self.reader.table_exists("mart_model_comparison"):
            return self.reader.safe_query("SELECT * FROM mart_model_comparison ORDER BY reliability_score DESC")
        return self.reader.safe_query(
            """SELECT r.model_name, r.task_type, COUNT(*) AS run_count,
                      AVG(e.overall_score) AS reliability_score,
                      AVG(e.correctness_score) AS correctness_score,
                      AVG(r.latency_ms) AS avg_latency_ms,
                      AVG(r.estimated_cost_usd) AS avg_cost_usd,
                      AVG(CASE WHEN e.overall_score < 0.7 THEN 1.0 ELSE 0.0 END) AS failure_rate
               FROM agent_runs r JOIN evaluation_results e ON r.run_id = e.run_id
               WHERE r.is_duplicate = FALSE
               GROUP BY r.model_name, r.task_type""",
        )

    def search_runs(
        self,
        days: int = 30,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_version_id: Optional[str] = None,
        task_type: Optional[str] = None,
        success_flag: Optional[bool] = None,
        failure_category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        start = WarehouseReader.default_start_date(days)
        clauses = ["r.is_duplicate = FALSE", "CAST(r.started_at AS DATE) >= ?"]
        params: list[Any] = [start.isoformat()]
        for col, val in [
            ("r.agent_name", agent_name), ("r.model_name", model_name),
            ("r.prompt_version_id", prompt_version_id), ("r.task_type", task_type),
            ("f.primary_category", failure_category), ("f.severity", severity),
        ]:
            if val is not None:
                clauses.append(f"{col} = ?")
                params.append(val)
        if success_flag is not None:
            clauses.append("r.success_flag = ?")
            params.append(success_flag)
        where = " AND ".join(clauses)
        return self.reader.safe_query(
            f"""SELECT r.run_id, r.agent_name, r.model_name, r.prompt_version_id,
                       r.task_type, r.started_at, r.latency_ms, r.estimated_cost_usd,
                       r.success_flag, e.overall_score, f.primary_category AS failure_category,
                       f.severity, f.recommendation
                FROM agent_runs r
                LEFT JOIN evaluation_results e ON r.run_id = e.run_id
                LEFT JOIN failure_modes f ON r.run_id = f.run_id
                WHERE {where} ORDER BY r.started_at DESC""",
            params, limit=limit,
        )

    def run_detail(self, run_id: str) -> dict[str, Any]:
        run = self.reader.safe_query("SELECT * FROM agent_runs WHERE run_id = ?", [run_id], limit=1)
        if run.empty:
            return {}
        evals = self.reader.safe_query(
            "SELECT * FROM evaluation_results WHERE run_id = ?", [run_id], limit=1,
        )
        failure = self.reader.safe_query(
            "SELECT * FROM failure_modes WHERE run_id = ?", [run_id], limit=1,
        )
        tools = self.reader.safe_query("SELECT * FROM tool_calls WHERE run_id = ?", [run_id])
        rets = self.reader.safe_query("SELECT * FROM retrieval_events WHERE run_id = ?", [run_id])
        return {
            "run": run.iloc[0].to_dict(),
            "evaluation": evals.iloc[0].to_dict() if not evals.empty else None,
            "failure": failure.iloc[0].to_dict() if not failure.empty else None,
            "tool_calls": tools.to_dict(orient="records"),
            "retrieval_events": rets.to_dict(orient="records"),
        }

    def _empty_overview(self) -> dict[str, Any]:
        return {
            "time_window_days": 7, "total_runs": 0, "reliability_score": None,
            "failure_rate": None, "avg_latency_ms": None, "total_cost_usd": None,
            "top_failure_category": None, "top_affected_agent": None, "top_affected_prompt": None,
        }


def _safe_float(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)
