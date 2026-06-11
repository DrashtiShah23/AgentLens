"""Run Review Center — default selection and review-priority helpers."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from app.dashboard.components.display_helpers import safe_lower, safe_str
from app.dashboard.components.layout import friendly_failure

QUICK_FILTER_REASONS = {
    "Failed only": "Runtime failed",
    "High severity": "High severity",
    "Prompt regression": "Prompt Regression",
    "SQL generation errors": "SQL Generation Error",
    "Unsupported answers": "Unsupported Answer",
    "Missing context": "Missing Context",
}

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and pd.isna(value):
        return False
    return bool(safe_str(value))


def _score_value(row: dict[str, Any]) -> float:
    score = row.get("overall_score")
    if score is None or (isinstance(score, float) and pd.isna(score)):
        return 1.0
    try:
        return float(score)
    except (TypeError, ValueError):
        return 1.0


def _is_runtime_failed(row: dict[str, Any]) -> bool:
    flag = row.get("success_flag")
    return flag in (False, 0, "false", "False")


def _failure_label(row: dict[str, Any]) -> Optional[str]:
    cat = safe_str(row.get("failure_category"))
    if not cat:
        return None
    if row.get("prompt_version_id") == "prompt_v5_regression_case":
        return "Prompt Regression"
    label = friendly_failure(cat)
    return label or cat


def reason_for_row(row: dict[str, Any], quick_filter: str = "All runs") -> str:
    if quick_filter != "All runs":
        return QUICK_FILTER_REASONS.get(quick_filter, "Matches current filter")

    sev = safe_lower(row.get("severity"))
    if sev == "critical":
        return "Critical severity"
    if sev == "high":
        return "High severity"

    score = _score_value(row)
    if score < 0.50:
        return "Lowest reliability score"
    if score < 0.80:
        return "Low reliability score"

    fail_label = _failure_label(row)
    if fail_label:
        return fail_label

    if _is_runtime_failed(row):
        return "Runtime failed"

    return "No review issue detected"


def select_default_run_id(
    df: pd.DataFrame,
    quick_filter: str = "All runs",
) -> tuple[Optional[str], str]:
    """Pick the default run_id and human-readable selection reason."""
    if df.empty:
        return None, "No review issue detected"

    if quick_filter != "All runs":
        row = df.iloc[0].to_dict()
        return row.get("run_id"), QUICK_FILTER_REASONS.get(quick_filter, "Matches current filter")

    rows = df.to_dict("records")

    critical = [r for r in rows if safe_lower(r.get("severity")) == "critical"]
    if critical:
        best = min(critical, key=_score_value)
        return best.get("run_id"), "Critical severity"

    scored = [r for r in rows if r.get("overall_score") is not None]
    if scored:
        lowest = min(scored, key=_score_value)
        if _score_value(lowest) < 1.0:
            return lowest.get("run_id"), "Lowest reliability score"

    with_failure = [r for r in rows if _has_value(r.get("failure_category"))]
    if with_failure:
        row = with_failure[0]
        return row.get("run_id"), _failure_label(row) or "Failure detected"

    failed = [r for r in rows if _is_runtime_failed(r)]
    if failed:
        return failed[0].get("run_id"), "Runtime failed"

    return rows[0].get("run_id"), "No review issue detected"


def row_for_run_id(df: pd.DataFrame, run_id: str) -> Optional[dict[str, Any]]:
    if df.empty or not run_id:
        return None
    match = df[df["run_id"] == run_id]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def failure_details_success_message() -> str:
    return (
        "This run has no failure details because it passed all applicable reliability checks."
    )


def failure_root_cause_text(failure: dict[str, Any]) -> str:
    cat = friendly_failure(failure.get("primary_category", ""))
    signals = failure.get("secondary_signals")
    if isinstance(signals, str) and signals.strip():
        return f"{cat}: {signals}" if cat else signals
    if isinstance(signals, dict) and signals:
        detail = "; ".join(f"{k}: {v}" for k, v in signals.items())
        return f"{cat} — {detail}" if cat else detail
    if cat:
        return f"Classified as {cat} based on evaluation and classifier signals."
    return "Root cause was not recorded for this run."


def failure_review_why_text(
    failure: dict[str, Any],
    overall_score: Optional[float] = None,
) -> str:
    reasons: list[str] = []
    if failure.get("requires_human_review"):
        reasons.append("The classifier flagged this run for human review.")
    sev = safe_lower(failure.get("severity"))
    if sev == "critical":
        reasons.append("Severity is critical.")
    elif sev == "high":
        reasons.append("Severity is high.")
    score = overall_score
    if score is not None and not (isinstance(score, float) and pd.isna(score)):
        if float(score) < 0.50:
            reasons.append("Reliability score is critically low.")
        elif float(score) < 0.80:
            reasons.append("Reliability score is below the trusted threshold.")
    if not reasons:
        reasons.append("This run has failure signals that should be reviewed.")
    return " ".join(reasons)
