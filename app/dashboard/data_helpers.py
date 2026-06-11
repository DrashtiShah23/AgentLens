"""Dashboard-only read queries — does not modify backend services."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import pandas as pd

from app.dashboard.components.display_helpers import TASK_DISPLAY_ORDER
from app.dashboard.components.metrics_validation import normalize_rate, validate_rates_in_df
from app.services.warehouse_reader import WarehouseReader
from observatory.config.settings import Settings, get_settings


def _start(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def extended_overview_kpis(reader: WarehouseReader, days: int = 7) -> dict[str, Any]:
    """Extra KPIs for dashboard UI computed from DuckDB."""
    if not reader.db_path_exists:
        return {}
    start = _start(days)
    kpis: dict[str, Any] = {}

    hall = reader.safe_query(
        """SELECT COUNT(*) AS cnt FROM failure_modes f
           JOIN agent_runs r ON f.run_id = r.run_id
           WHERE f.primary_category = 'hallucination'
             AND CAST(f.classified_at AS DATE) >= ?""",
        [start], limit=1,
    )
    total_fail = reader.safe_query(
        """SELECT COUNT(*) AS cnt FROM failure_modes f
           WHERE CAST(f.classified_at AS DATE) >= ?""",
        [start], limit=1,
    )
    total_runs = reader.safe_query(
        """SELECT COUNT(*) AS cnt FROM agent_runs r
           WHERE r.is_duplicate = FALSE AND CAST(r.started_at AS DATE) >= ?""",
        [start], limit=1,
    )
    hall_cnt = int(hall.iloc[0]["cnt"]) if not hall.empty else 0
    run_cnt = int(total_runs.iloc[0]["cnt"]) if not total_runs.empty else 0
    kpis["hallucination_rate"] = hall_cnt / run_cnt if run_cnt else None

    sql = reader.safe_query(
        """SELECT AVG(e.sql_score) AS sql_success
           FROM agent_runs r JOIN evaluation_results e ON r.run_id = e.run_id
           WHERE r.task_type = 'text_to_sql' AND r.is_duplicate = FALSE
             AND CAST(r.started_at AS DATE) >= ? AND e.sql_score IS NOT NULL""",
        [start], limit=1,
    )
    kpis["sql_success_rate"] = float(sql.iloc[0]["sql_success"]) if not sql.empty and sql.iloc[0]["sql_success"] is not None else None

    if reader.table_exists("mart_prompt_regression"):
        reg = reader.safe_query(
            "SELECT COUNT(*) AS cnt FROM mart_prompt_regression WHERE regression_detected = TRUE",
            limit=1,
        )
    else:
        reg = reader.safe_query(
            """SELECT COUNT(DISTINCT prompt_version_id) AS cnt
               FROM agent_runs r JOIN evaluation_results e ON r.run_id = e.run_id
               WHERE r.prompt_version_id = 'prompt_v5_regression_case'
                 AND e.overall_score < 0.7""",
            limit=1,
        )
    kpis["prompt_regressions"] = int(reg.iloc[0]["cnt"]) if not reg.empty else 0
    kpis["has_marts"] = reader.table_exists("mart_agent_reliability")
    kpis["has_data"] = run_cnt > 0
    kpis["v5_regression"] = kpis["prompt_regressions"] > 0
    return kpis


def cost_latency_trends(reader: WarehouseReader, days: int = 30) -> pd.DataFrame:
    start = _start(days)
    if reader.table_exists("mart_cost_latency"):
        return reader.safe_query(
            """SELECT run_date, AVG(avg_latency_ms) AS avg_latency_ms,
                      AVG(avg_cost_usd) AS avg_cost_usd, SUM(run_count) AS run_count
               FROM mart_cost_latency WHERE run_date >= ?
               GROUP BY run_date ORDER BY run_date""",
            [start],
        )
    return reader.safe_query(
        """SELECT CAST(started_at AS DATE) AS run_date,
                  AVG(latency_ms) AS avg_latency_ms,
                  AVG(estimated_cost_usd) AS avg_cost_usd,
                  COUNT(*) AS run_count
           FROM agent_runs WHERE is_duplicate = FALSE AND CAST(started_at AS DATE) >= ?
           GROUP BY 1 ORDER BY 1""",
        [start],
    )


def failure_trends_stacked(reader: WarehouseReader, days: int = 30) -> pd.DataFrame:
    start = _start(days)
    if reader.table_exists("mart_failure_trends"):
        df = reader.safe_query(
            """SELECT CAST(failure_date AS DATE) AS failure_date, failure_category,
                      SUM(failure_count) AS failure_count
               FROM mart_failure_trends WHERE failure_date >= ?
               GROUP BY 1, 2 ORDER BY 1""",
            [start],
        )
    else:
        df = reader.safe_query(
            """SELECT CAST(classified_at AS DATE) AS failure_date,
                      primary_category AS failure_category, COUNT(*) AS failure_count
               FROM failure_modes WHERE CAST(classified_at AS DATE) >= ?
               GROUP BY 1, 2 ORDER BY 1""",
            [start],
        )
    if not df.empty and "failure_date" in df.columns:
        df["failure_date"] = pd.to_datetime(df["failure_date"], errors="coerce").dt.normalize()
    return df


def prompt_baseline_delta(reader: WarehouseReader) -> pd.DataFrame:
    df = reader.safe_query(
        """SELECT prompt_version_id,
                  AVG(overall_score) AS reliability_score,
                  AVG(estimated_cost_usd) AS avg_cost_usd,
                  AVG(latency_ms) AS avg_latency_ms
           FROM agent_runs r JOIN evaluation_results e ON r.run_id = e.run_id
           WHERE r.is_duplicate = FALSE
           GROUP BY prompt_version_id""",
    )
    if df.empty:
        return df
    baseline = df[df["prompt_version_id"] == "prompt_v1_baseline"]
    if baseline.empty:
        return df
    b_rel = baseline.iloc[0]["reliability_score"]
    b_cost = baseline.iloc[0]["avg_cost_usd"]
    b_lat = baseline.iloc[0]["avg_latency_ms"]
    df = df.copy()
    df["reliability_delta"] = df["reliability_score"] - b_rel
    df["cost_delta"] = df["avg_cost_usd"] - b_cost
    df["latency_delta"] = df["avg_latency_ms"] - b_lat
    if reader.table_exists("mart_prompt_regression"):
        reg = reader.safe_query("SELECT prompt_version_id, regression_detected FROM mart_prompt_regression")
        if not reg.empty:
            df = df.merge(reg.groupby("prompt_version_id")["regression_detected"].max().reset_index(),
                          on="prompt_version_id", how="left")
    return df


def top_failing_agents(reader: WarehouseReader, days: int = 30, limit: int = 8) -> pd.DataFrame:
    start = _start(days)
    return reader.safe_query(
        """SELECT r.agent_name, COUNT(*) AS failure_count
           FROM failure_modes f JOIN agent_runs r ON f.run_id = r.run_id
           WHERE CAST(f.classified_at AS DATE) >= ?
           GROUP BY 1 ORDER BY failure_count DESC LIMIT ?""",
        [start, limit],
    )


def model_failure_rates_by_model(reader: WarehouseReader) -> pd.DataFrame:
    """Failure rate per model = failed_run_count / total_run_count (never sum of rates)."""
    if reader.table_exists("mart_model_comparison"):
        raw = reader.safe_query(
            "SELECT model_name, run_count, failure_rate FROM mart_model_comparison",
        )
        if raw.empty:
            return raw
        raw = raw.copy()
        raw["failed_run_count"] = raw["failure_rate"].fillna(0) * raw["run_count"].fillna(0)
        agg = raw.groupby("model_name", as_index=False).agg(
            run_count=("run_count", "sum"),
            failed_run_count=("failed_run_count", "sum"),
        )
        agg["failure_rate"] = agg["failed_run_count"] / agg["run_count"].replace(0, pd.NA)
    else:
        agg = reader.safe_query(
            """SELECT r.model_name,
                      COUNT(*) AS run_count,
                      SUM(CASE WHEN e.overall_score < 0.7 THEN 1 ELSE 0 END) AS failed_run_count,
                      SUM(CASE WHEN e.overall_score < 0.7 THEN 1.0 ELSE 0.0 END) / COUNT(*) AS failure_rate
               FROM agent_runs r
               JOIN evaluation_results e ON r.run_id = e.run_id
               WHERE r.is_duplicate = FALSE
               GROUP BY r.model_name
               ORDER BY failure_rate DESC""",
        )
    agg["failure_rate"] = agg["failure_rate"].apply(normalize_rate)
    return validate_rates_in_df(agg, ["failure_rate"])


def best_model_by_task(reader: WarehouseReader) -> pd.DataFrame:
    """Highest-reliability model per task type."""
    df = ranked_models(reader)
    if df.empty or "task_type" not in df.columns:
        return df.iloc[0:0]
    idx = df.groupby("task_type")["reliability_score"].idxmax()
    best = df.loc[idx].copy()
    order = {t: i for i, t in enumerate(TASK_DISPLAY_ORDER)}
    best["_sort"] = best["task_type"].map(lambda t: order.get(t, 99))
    return best.sort_values("_sort").drop(columns="_sort")


def ranked_models(reader: WarehouseReader) -> pd.DataFrame:
    if reader.table_exists("mart_model_comparison"):
        df = reader.safe_query(
            "SELECT * FROM mart_model_comparison ORDER BY reliability_score DESC",
        )
    else:
        df = reader.safe_query(
            """SELECT r.model_name, r.task_type, COUNT(*) AS run_count,
                      AVG(e.overall_score) AS reliability_score,
                      AVG(e.correctness_score) AS correctness_score,
                      AVG(e.sql_score) AS sql_score,
                      AVG(e.retrieval_score) AS retrieval_score,
                      AVG(e.tool_score) AS tool_score,
                      AVG(r.latency_ms) AS avg_latency_ms,
                      AVG(r.estimated_cost_usd) AS avg_cost_usd,
                      AVG(CASE WHEN e.overall_score < 0.7 THEN 1.0 ELSE 0.0 END) AS failure_rate
               FROM agent_runs r JOIN evaluation_results e ON r.run_id = e.run_id
               WHERE r.is_duplicate = FALSE
               GROUP BY r.model_name, r.task_type ORDER BY reliability_score DESC""",
        )
    return validate_rates_in_df(df, ["reliability_score", "failure_rate"])
