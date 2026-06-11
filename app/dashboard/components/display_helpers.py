"""Dashboard display helpers — rates, colors, labels, formatting."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from app.dashboard.components.metrics_validation import normalize_rate
from app.dashboard.components.styles import CHART_COLORS, FAILURE_COLORS, TASK_LABELS

# Palettes for failure/incident charts — no green
FAILURE_CHART_PALETTE = [
    "#ef4444", "#f97316", "#eab308", "#ec4899", "#a855f7", "#fb923c", "#f59e0b", "#dc2626",
]

SCORE_DISCLAIMER = (
    "These are deterministic evaluation metrics from synthetic demo agent runs. "
    "They demonstrate observability logic and are not production benchmarks of real model providers."
)

V5_REGRESSION_NOTE = (
    "prompt_v5_regression_case is synthetic bad prompt data intentionally generated to test "
    "regression detection. It does not mean a real prompt failed in production."
)

RUN_PERFECT_SCORE_NOTE = (
    "A 100% score means this selected synthetic run passed all applicable checks. "
    "It does not mean the model is always 100% accurate."
)


def safe_lower(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower()


def safe_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def friendly_task_name(task: str) -> str:
    task_s = safe_str(task)
    if not task_s:
        return ""
    return TASK_LABELS.get(task_s, task_s.replace("_", " ").title())


def format_change_points(value: Any) -> str:
    """Plain English reliability change (0–1 scale input)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "No change"
    pts = float(value) * 100
    if abs(pts) < 0.05:
        return "No change"
    if pts > 0:
        return f"{pts:.1f} points higher"
    return f"{abs(pts):.1f} points lower"


def format_percentage_point_delta(value: Any) -> str:
    """Alias for format_change_points — no 'pp' abbreviation."""
    return format_change_points(value)


def format_bar_value_label(value: float) -> str:
    return f"{int(round(float(value))):,}"


def friendly_prompt_name(prompt_id: str) -> str:
    if not prompt_id:
        return ""
    known = {
        "prompt_v5_regression_case": "Prompt v5 regression case",
        "prompt_v1_baseline": "Prompt v1 baseline",
        "prompt_v4_schema_aware": "Prompt v4 schema aware",
    }
    if prompt_id in known:
        return known[prompt_id]
    text = prompt_id.replace("_", " ")
    if text.startswith("prompt v"):
        return text[0].upper() + text[1:]
    return text


def friendly_model_name(model: str) -> str:
    if not model:
        return ""
    parts = model.split("_")
    if parts and parts[0].lower() == "gpt":
        return "GPT " + " ".join(parts[1:])
    return model.replace("_", " ").title()


def regression_hover_text(
    reliability: Optional[float],
    baseline_reliability: Optional[float],
    delta: Optional[float],
    prompt_id: str,
) -> str:
    before = float(baseline_reliability) if baseline_reliability is not None else 0.0
    after = float(reliability) if reliability is not None else before + float(delta or 0)
    pts = abs(float(delta or 0) * 100)
    if float(delta or 0) < -0.0005:
        change = f"a drop of {pts:.1f} points"
    elif float(delta or 0) > 0.0005:
        change = f"a rise of {pts:.1f} points"
    else:
        change = "no change"
    return (
        f"{friendly_prompt_name(prompt_id)}<br>"
        f"Reliability changed from {before:.1%} to {after:.1%}, {change}."
    )


def apply_chart_margins(
    fig,
    *,
    left: int = 160,
    right: int = 120,
    top: int = 64,
    bottom: int = 56,
    height: int = 440,
) -> None:
    fig.update_layout(
        margin=dict(l=left, r=right, t=top, b=bottom),
        height=height,
    )


def risk_color_for_failure_rate(rate: Optional[float]) -> str:
    r = normalize_rate(rate) or 0.0
    if r >= 0.50:
        return CHART_COLORS["critical"]
    if r >= 0.25:
        return CHART_COLORS["warning"]
    if r >= 0.10:
        return "#eab308"
    return CHART_COLORS["neutral"]


def risk_color_for_count(count: float, max_count: float) -> str:
    if max_count <= 0:
        return CHART_COLORS["neutral"]
    ratio = count / max_count
    if ratio >= 0.75:
        return CHART_COLORS["critical"]
    if ratio >= 0.50:
        return CHART_COLORS["warning"]
    if ratio >= 0.25:
        return "#eab308"
    return CHART_COLORS["neutral"]


def compute_weighted_failure_rate(failure_rates: pd.Series, run_counts: pd.Series) -> float:
    """Weighted average failure rate: sum(rate * runs) / sum(runs)."""
    total = float(run_counts.sum())
    if total <= 0:
        return 0.0
    weighted = float((failure_rates.fillna(0) * run_counts).sum())
    return normalize_rate(weighted / total) or 0.0


def palette_has_green(colors: list[str]) -> bool:
    green_tokens = {"#22c55e", "#16a34a", "#86efac", "#bbf7d0", "#14532d", "green"}
    return any(c.lower() in green_tokens or c.lower().startswith("#22c") for c in colors)


TASK_DISPLAY_ORDER = [
    "classification", "retrieval_qa", "text_to_sql", "tool_use", "summarization",
]

TASK_RECOMMENDATIONS = {
    "classification": "Recommended when answer categories must be consistent.",
    "retrieval_qa": "Recommended when context lookup quality matters most.",
    "text_to_sql": "Recommended when SQL correctness matters most.",
    "tool_use": "Recommended when tool routing and completion matter most.",
    "summarization": "Recommended when concise summaries must stay faithful to source.",
}

VALID_TASK_RISK_LABELS = frozenset({"Healthy", "Warning", "Risky"})


def task_risk_label(reliability: Optional[float]) -> tuple[str, str]:
    """Return (label, badge_level) for task-level model reliability."""
    r = float(reliability) if reliability is not None and not pd.isna(reliability) else 0.0
    if r >= 0.80:
        return "Healthy", "healthy"
    if r >= 0.60:
        return "Warning", "warning"
    return "Risky", "critical"


def execution_status_label(success_flag: bool) -> tuple[str, str]:
    if success_flag:
        return "Completed", "model"
    return "Runtime Failed", "critical"


def reliability_status_label(
    score: Optional[float],
    failure_category: Optional[str] = None,
    severity: Optional[str] = None,
) -> tuple[str, str]:
    sev = safe_lower(severity)
    fail_cat = safe_str(failure_category)
    if sev == "critical":
        return "Critical", "critical"
    if score is not None and not pd.isna(score):
        if float(score) < 0.50:
            return "Critical", "critical"
        if float(score) >= 0.80 and not fail_cat:
            return "Reliable", "healthy"
        if float(score) >= 0.50 or fail_cat:
            return "Needs Review", "warning"
    if fail_cat:
        return "Needs Review", "warning"
    return "Needs Review", "warning"


def task_recommendation_text(task_type: str, reliability: Optional[float]) -> str:
    rel = float(reliability) if reliability is not None and not pd.isna(reliability) else 0.0
    if rel < 0.60:
        return (
            "Best available, but risky. "
            "Recommended action: improve prompts, tools, or evaluation coverage before relying on this task."
        )
    return TASK_RECOMMENDATIONS.get(task_type, "Recommended for this task type.")
