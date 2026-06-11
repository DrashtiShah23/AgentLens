"""Read-only investigation tools — parameterized queries only."""

from __future__ import annotations

import inspect
import re
from typing import Any, Callable, Optional

from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader
from observatory.config.settings import Settings, get_settings

KNOWN_METRICS = frozenset({
    "reliability", "failure", "failures", "prompt", "model", "cost", "latency",
    "incident", "run", "lineage", "trend",
})

# Line-anchored SQL patterns — natural language may use words like "drop" or "delete".
_DESTRUCTIVE_SQL_PATTERNS = (
    re.compile(r"^\s*drop\s+table\b", re.IGNORECASE),
    re.compile(r"^\s*delete\s+from\b", re.IGNORECASE),
    re.compile(r"^\s*truncate\s+table\b", re.IGNORECASE),
    re.compile(r"^\s*alter\s+table\b", re.IGNORECASE),
    re.compile(r"^\s*insert\s+into\b", re.IGNORECASE),
    re.compile(r"^\s*update\s+\w+\s+set\b", re.IGNORECASE),
    re.compile(r"^\s*create\s+table\b", re.IGNORECASE),
)
_RAW_SELECT_PATTERN = re.compile(r"^\s*select\s+.+\s+from\b", re.IGNORECASE)


def _sql_segments(text: str) -> list[str]:
    """Split on semicolons to catch chained SQL statements."""
    return [part.strip() for part in text.split(";") if part.strip()]


def reject_unsafe_input(text: str) -> Optional[str]:
    """Return error message if input looks like raw or destructive SQL."""
    for segment in _sql_segments(text):
        for pattern in _DESTRUCTIVE_SQL_PATTERNS:
            if pattern.search(segment):
                return "Destructive SQL keywords are not allowed. Ask a natural language question."
        if _RAW_SELECT_PATTERN.search(segment):
            return "Raw SQL is not accepted. Ask a natural language reliability question."
    return None


def parse_time_window(question: str, default_days: int = 7) -> tuple[int, list[str]]:
    """Extract time window from question; default to last 7 days."""
    assumptions: list[str] = []
    lower = question.lower()
    if "yesterday" in lower:
        return 1, ["Assumed time window: yesterday (1 day)"]
    if "this week" in lower or "last week" in lower:
        return 7, ["Assumed time window: last 7 days"]
    if "this month" in lower or "last month" in lower:
        return 30, ["Assumed time window: last 30 days"]
    match = re.search(r"last\s+(\d+)\s+days?", lower)
    if match:
        days = int(match.group(1))
        return days, [f"Assumed time window: last {days} days"]
    return default_days, [f"Assumed time window: last {default_days} days (default)"]


def detect_tool(question: str) -> str:
    """Select investigation tool from question keywords."""
    lower = question.lower()
    if "lineage" in lower or "upstream" in lower or "downstream" in lower:
        return "get_lineage_for_model"
    if "run_id" in lower or (re.search(r"run_[a-f0-9]{8,}", lower) and "detail" in lower):
        return "get_run_details"
    if "human review" in lower or "need review" in lower or "needs review" in lower:
        return "get_recent_incidents"
    if "incident" in lower:
        return "get_recent_incidents"
    if "expensive" in lower or "most cost" in lower:
        return "get_cost_latency_summary"
    if "cost" in lower or "latency" in lower or "slow" in lower:
        return "get_cost_latency_summary"
    if "prompt" in lower or "v5" in lower or "regression" in lower or "worse" in lower:
        return "get_prompt_comparison"
    if "model" in lower or "safest" in lower or "text-to-sql" in lower or "text to sql" in lower:
        return "get_model_comparison"
    if "failure" in lower or "fail" in lower or "top failure" in lower:
        return "get_failure_trends"
    if "reliability" in lower or "drop" in lower or "decreased" in lower:
        return "get_overall_reliability"
    return "get_overall_reliability"


def build_tool_kwargs(tool_name: str, question: str, days: int,
                      run_id: Optional[str] = None,
                      model_name: Optional[str] = None) -> dict[str, Any]:
    """Return only kwargs accepted by the target tool."""
    if tool_name == "get_run_details":
        return {"run_id": run_id} if run_id else {}
    if tool_name == "get_lineage_for_model":
        return {"model_name": model_name or "mart_agent_reliability"}
    if tool_name in {"get_overall_reliability", "get_failure_trends", "get_cost_latency_summary"}:
        return {"time_window_days": days}
    if tool_name == "get_model_comparison":
        lower = question.lower()
        if "text to sql" in lower or "text-to-sql" in lower or "text_to_sql" in lower:
            return {"task_type": "text_to_sql"}
        return {}
    return {}


class InvestigationTools:
    """Safe read-only tools for the investigation agent."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.reader = WarehouseReader(self.settings)
        self.metrics = MetricService(self.reader, self.settings)

    def get_overall_reliability(self, time_window_days: int = 7) -> dict[str, Any]:
        data = self.metrics.overview_metrics(time_window_days)
        trend = self.metrics.reliability_over_time(time_window_days)
        return {
            "metric": "overall_reliability",
            "time_window_days": time_window_days,
            "summary": data,
            "trend_rows": trend.to_dict(orient="records") if not trend.empty else [],
        }

    def get_failure_trends(self, time_window_days: int = 7,
                           agent_name: Optional[str] = None) -> dict[str, Any]:
        df = self.metrics.failures_by_category(time_window_days)
        records = self.metrics.failure_records(days=time_window_days, agent_name=agent_name, limit=100)
        return {
            "metric": "failure_trends",
            "time_window_days": time_window_days,
            "by_category": df.to_dict(orient="records") if not df.empty else [],
            "recent_failures": records.to_dict(orient="records") if not records.empty else [],
            "agent_filter": agent_name,
        }

    def get_prompt_comparison(self, agent_name: Optional[str] = None) -> dict[str, Any]:
        df = self.metrics.prompt_performance()
        if agent_name and not df.empty and "agent_name" in df.columns:
            df = df[df["agent_name"] == agent_name]
        return {
            "metric": "prompt_comparison",
            "prompts": df.to_dict(orient="records") if not df.empty else [],
            "data_available": not df.empty,
        }

    def get_model_comparison(self, task_type: Optional[str] = None) -> dict[str, Any]:
        df = self.metrics.model_performance()
        if task_type and not df.empty and "task_type" in df.columns:
            df = df[df["task_type"] == task_type]
        return {
            "metric": "model_comparison",
            "models": df.to_dict(orient="records") if not df.empty else [],
            "task_type_filter": task_type,
        }

    def get_run_details(self, run_id: str) -> dict[str, Any]:
        detail = self.metrics.run_detail(run_id)
        if not detail:
            return {"metric": "run_details", "data_available": False, "run_id": run_id}
        return {"metric": "run_details", "data_available": True, **detail}

    def get_recent_incidents(self, severity: Optional[str] = None, limit: int = 50) -> dict[str, Any]:
        if self.reader.table_exists("mart_incident_summary"):
            df = self.reader.safe_query(
                """SELECT * FROM mart_incident_summary
                   WHERE (? IS NULL OR severity = ?)
                   ORDER BY incident_count DESC""",
                [severity, severity], limit=limit,
            )
        else:
            df = self.metrics.failure_records(days=30, severity=severity, limit=limit)
        return {
            "metric": "recent_incidents",
            "incidents": df.to_dict(orient="records") if not df.empty else [],
            "severity_filter": severity,
        }

    def get_cost_latency_summary(self, time_window_days: int = 7) -> dict[str, Any]:
        start = WarehouseReader.default_start_date(time_window_days)
        if self.reader.table_exists("mart_cost_latency"):
            df = self.reader.safe_query(
                "SELECT * FROM mart_cost_latency WHERE run_date >= ? ORDER BY run_date",
                [start.isoformat()],
            )
        else:
            df = self.reader.safe_query(
                """SELECT CAST(started_at AS DATE) AS run_date, agent_name, model_name,
                          AVG(latency_ms) AS avg_latency_ms, AVG(estimated_cost_usd) AS avg_cost_usd,
                          COUNT(*) AS run_count
                   FROM agent_runs WHERE is_duplicate = FALSE AND CAST(started_at AS DATE) >= ?
                   GROUP BY 1, agent_name, model_name""",
                [start.isoformat()],
            )
        return {
            "metric": "cost_latency_summary",
            "time_window_days": time_window_days,
            "rows": df.to_dict(orient="records") if not df.empty else [],
        }

    def get_lineage_for_model(self, model_name: str) -> dict[str, Any]:
        import json
        from pathlib import Path
        lineage_path = self.settings.resolve_path(self.settings.metadata_dir) / "lineage.json"
        if not lineage_path.exists():
            return {
                "metric": "lineage",
                "model_name": model_name,
                "data_available": False,
                "message": "Lineage metadata is not available. Run scripts/refresh_metadata.py",
            }
        with lineage_path.open("r", encoding="utf-8") as handle:
            lineage = json.load(handle)
        edges = [
            e for e in lineage.get("edges", [])
            if e.get("upstream", "").startswith(model_name)
            or e.get("downstream", "").startswith(model_name)
            or model_name in e.get("upstream", "")
            or model_name in e.get("downstream", "")
        ]
        if not edges:
            edges = [e for e in lineage.get("edges", []) if model_name in str(e)]
        return {
            "metric": "lineage",
            "model_name": model_name,
            "data_available": bool(edges),
            "edges": edges[:50],
        }

    def dispatch(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        tools: dict[str, Callable[..., dict[str, Any]]] = {
            "get_overall_reliability": self.get_overall_reliability,
            "get_failure_trends": self.get_failure_trends,
            "get_prompt_comparison": self.get_prompt_comparison,
            "get_model_comparison": self.get_model_comparison,
            "get_run_details": self.get_run_details,
            "get_recent_incidents": self.get_recent_incidents,
            "get_cost_latency_summary": self.get_cost_latency_summary,
            "get_lineage_for_model": self.get_lineage_for_model,
        }
        if tool_name not in tools:
            return {"error": f"Unknown tool: {tool_name}", "data_available": False}
        fn = tools[tool_name]
        allowed = set(inspect.signature(fn).parameters)
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        try:
            return fn(**filtered)
        except Exception as exc:
            return {"error": str(exc), "data_available": False, "metric": tool_name}
