"""Layout helpers, formatting, and executive-friendly display."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import streamlit as st

from app.dashboard.components.badges import reliability_badge, severity_badge, status_badge
from app.dashboard.components.styles import CUSTOM_CSS, FAILURE_LABELS, SEVERITY_LABELS, TASK_LABELS
from observatory.config.settings import Settings, get_settings


# ── Formatters ──────────────────────────────────────────────────────────────

def format_not_applicable(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Not applicable"
    return str(value)


def format_percent(value: Any, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Not applicable"
    from app.dashboard.components.metrics_validation import normalize_rate
    v = normalize_rate(value)
    if v is None:
        return "Not applicable"
    return f"{v * 100:.{decimals}f}%"


def format_score(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Not applicable"
    return format_percent(value, 1)


def format_cost(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Unavailable"
    v = float(value)
    if v < 0.01:
        return f"${v:.6f}"
    return f"${v:.4f}"


def format_latency(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Unavailable"
    ms = float(value)
    return f"{ms:,.0f} ms" if ms < 10_000 else f"{ms / 1000:.1f}s"


def format_count(value: Any) -> str:
    if value is None:
        return "Unavailable"
    return f"{int(value):,}"


def status_from_score(score: Optional[float], threshold: float = 0.70) -> str:
    if score is None:
        return "neutral"
    if score >= threshold:
        return "healthy"
    if score >= 0.50:
        return "warning"
    return "critical"


def friendly_failure(category: object) -> str:
    from app.dashboard.components.display_helpers import safe_str
    cat = safe_str(category)
    if not cat:
        return ""
    return FAILURE_LABELS.get(cat, cat.replace("_", " ").title())


def friendly_severity(severity: object) -> str:
    from app.dashboard.components.display_helpers import safe_lower, safe_str
    sev = safe_str(severity)
    if not sev or safe_lower(sev) in ("not applicable", "n/a"):
        return "Not applicable"
    return SEVERITY_LABELS.get(safe_lower(sev), sev.replace("_", " ").title())


def friendly_task(task: str) -> str:
    if not task:
        return ""
    return TASK_LABELS.get(task, task.replace("_", " ").title())


# ── Column rename maps ────────────────────────────────────────────────────────

FAILURE_COLS = {
    "failure_category": "Failure Type",
    "primary_category": "Failure Type",
    "severity": "Severity",
    "agent_name": "Agent",
    "prompt_version_id": "Prompt Version",
    "recommendation": "Recommended Fix",
    "confidence_score": "Confidence",
    "classified_at": "Detected At",
    "user_query": "User Question",
}

PROMPT_COLS = {
    "prompt_version_id": "Prompt Version",
    "reliability_score": "Reliability",
    "failure_rate": "Failure Rate",
    "avg_latency_ms": "Avg Latency",
    "avg_cost_usd": "Avg Cost",
    "run_count": "Runs",
    "regression_detected": "Regression",
    "reliability_delta": "Reliability Change",
    "cost_delta": "Cost Change",
    "latency_delta": "Latency Change",
    "change_reason": "Change Reason",
}

MODEL_COLS = {
    "model_name": "Model",
    "task_type": "Task Type",
    "reliability_score": "Reliability",
    "failure_rate": "Failure Rate",
    "avg_latency_ms": "Avg Latency",
    "avg_cost_usd": "Avg Cost",
    "run_count": "Runs",
    "sql_score": "SQL Quality",
    "retrieval_score": "Context Lookup Quality",
    "tool_score": "Tool Quality",
    "correctness_score": "Answer Quality",
}

RUN_COLS = {
    "run_id": "Run ID",
    "agent_name": "Agent",
    "model_name": "Model",
    "prompt_version_id": "Prompt Version",
    "task_type": "Task Type",
    "overall_score": "Reliability",
    "execution_status": "Execution Status",
    "reliability_status": "Reliability Status",
    "severity": "Severity",
    "failure_category": "Failure Type",
    "latency_ms": "Latency",
    "estimated_cost_usd": "Cost",
}


def chart_caption(text: str) -> None:
    st.markdown(f'<p style="color:#94a3b8;font-size:0.82rem;margin:-0.5rem 0 1rem 0;">{text}</p>',
                unsafe_allow_html=True)


def format_run_list(df: pd.DataFrame) -> pd.DataFrame:
    """User-friendly run list with separate execution and reliability status."""
    if df.empty:
        return df
    out = df.copy()
    from app.dashboard.components.display_helpers import (
        execution_status_label, reliability_status_label,
    )
    if "success_flag" in out.columns:
        out["execution_status"] = out["success_flag"].apply(
            lambda v: execution_status_label(v in (True, 1, "true", "True"))[0]
        )
    if "overall_score" in out.columns:
        out["reliability_status"] = out.apply(
            lambda r: reliability_status_label(
                r.get("overall_score"),
                r.get("failure_category"),
                r.get("severity"),
            )[0],
            axis=1,
        )
        out["overall_score"] = out["overall_score"].apply(format_score)
    if "failure_category" in out.columns:
        out["failure_category"] = out["failure_category"].apply(
            lambda x: friendly_failure(x) if friendly_failure(x) else "No failure detected"
        )
    if "severity" in out.columns:
        out["severity"] = out["severity"].apply(friendly_severity)
    out = out.drop(columns=["success_flag"], errors="ignore")
    cols = [c for c in [
        "run_id", "agent_name", "overall_score", "execution_status",
        "reliability_status", "failure_category", "severity",
    ] if c in out.columns]
    return rename_for_display(out[cols], RUN_COLS)


def rename_for_display(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "failure_category" in out.columns:
        out["failure_category"] = out["failure_category"].apply(
            lambda x: friendly_failure(x) if isinstance(x, str) else x
        )
    if "primary_category" in out.columns:
        out["primary_category"] = out["primary_category"].apply(
            lambda x: friendly_failure(x) if isinstance(x, str) else x
        )
    if "severity" in out.columns:
        out["severity"] = out["severity"].apply(friendly_severity)
    if "task_type" in out.columns:
        out["task_type"] = out["task_type"].apply(
            lambda x: friendly_task(x) if isinstance(x, str) else x
        )
    rename = {k: v for k, v in mapping.items() if k in out.columns}
    return out.rename(columns=rename)


# ── UI blocks ─────────────────────────────────────────────────────────────────

def inject_css() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, purpose: str = "") -> None:
    purpose_html = f'<p class="purpose">{purpose}</p>' if purpose else ""
    st.markdown(
        f"""<div class="obs-hero">
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
            {purpose_html}
        </div>""",
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    st.markdown(f'<div class="obs-section">{title}</div>', unsafe_allow_html=True)


def metric_card(
    icon: str,
    label: str,
    value: str,
    interpretation: str,
    status: str = "neutral",
    badge_html: str = "",
) -> None:
    st.markdown(
        f"""<div class="obs-metric {status}">
            <div class="obs-metric-icon">{icon}</div>
            <div class="obs-metric-label">{label}</div>
            <div class="obs-metric-value">{value} {badge_html}</div>
            <div class="obs-metric-interp">{interpretation}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def insight_card(title: str, body: str) -> None:
    st.markdown(f'<div class="obs-insight"><strong>{title}</strong><br>{body}</div>', unsafe_allow_html=True)


def action_card(action: str) -> None:
    st.markdown(f'<div class="obs-action"><strong>Recommended next action</strong><br>{action}</div>', unsafe_allow_html=True)


def alert_card(body: str) -> None:
    st.markdown(f'<div class="obs-alert">{body}</div>', unsafe_allow_html=True)


def empty_state(title: str, message: str, commands: str = "") -> None:
    cmd = f'<pre style="text-align:left;background:#1e293b;color:#94a3b8;padding:0.75rem;border-radius:6px;font-size:0.78rem;">{commands}</pre>' if commands else ""
    st.markdown(f'<div class="obs-empty"><div class="obs-empty-title">{title}</div><div>{message}</div>{cmd}</div>', unsafe_allow_html=True)


def warehouse_missing() -> None:
    empty_state("Data Not Ready", "Load the demo dataset to explore the reliability command center.",
                "python scripts/run_local_pipeline.py")


def demo_note(has_data: bool, v5: bool = False) -> None:
    if not has_data:
        return
    msg = "Demo dataset loaded from synthetic AI agent runs."
    if v5:
        msg += " Prompt v5 regression scenario is active."
    st.markdown(f'<div class="obs-demo">{msg}</div>', unsafe_allow_html=True)


def sidebar_nav(pages: list[str] | None = None) -> str | None:
    st.sidebar.markdown("### 🔭 AI Failure Observatory")
    st.sidebar.markdown("*AI reliability command center*")
    st.sidebar.markdown("---")
    settings = get_settings()
    if settings.resolve_path(settings.warehouse_path).exists():
        st.sidebar.markdown("🟢 **Warehouse:** Connected")
    else:
        st.sidebar.markdown("🔴 **Warehouse:** Offline")
    extra = _demo_status(settings)
    if extra:
        st.sidebar.markdown(f"📊 **Demo data:** {extra}")
    llm = "Enabled" if settings.use_llm else "Disabled (default)"
    st.sidebar.markdown(f"💬 **Cost mode:** LLM {llm}")
    st.sidebar.markdown("---")
    if pages:
        st.sidebar.markdown("**Navigation**")
        return st.sidebar.radio("Navigation", pages, label_visibility="collapsed")
    return None


def _demo_status(settings: Settings) -> str:
    path = settings.resolve_path(settings.warehouse_path)
    if not path.exists():
        return ""
    try:
        import duckdb
        conn = duckdb.connect(str(path), read_only=True)
        n = conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0]
        conn.close()
        return f"{n:,} runs loaded" if n else "Empty"
    except Exception:
        return "Available"


def health_banner(status: str, message: str) -> None:
    st.markdown(
        f'<div class="obs-health-banner {status}">{message}</div>',
        unsafe_allow_html=True,
    )


def risk_card(title: str, body: str) -> None:
    st.markdown(f'<div class="obs-risk-card"><strong>{title}</strong><br>{body}</div>', unsafe_allow_html=True)


def copilot_response(
    summary: str,
    evidence: Any,
    action: str,
    llm_used: bool,
    time_window: Optional[int],
    confidence: Optional[float] = None,
    assumptions: list[str] | None = None,
    technical_error: Optional[str] = None,
    metric_data: Any = None,
) -> None:
    llm_text = (
        "LLM enabled — natural language summary"
        if llm_used
        else "LLM disabled. Returning deterministic metric summary from DuckDB."
    )
    window = f"Last {time_window} days" if time_window else "Default window"
    evidence_text = evidence if isinstance(evidence, str) and evidence else (
        "Based on pre-aggregated reliability metrics from the warehouse."
    )
    st.markdown(
        f"""<div class="obs-response">
            <div class="obs-response-label">Summary</div>
            <div class="obs-response-text">{summary}</div>
            <div class="obs-response-label">Evidence</div>
            <div class="obs-response-text">{evidence_text}</div>
            <div class="obs-response-label">Recommended Action</div>
            <div class="obs-response-text">{action or "Review the cited metrics in the relevant dashboard page."}</div>
            <div class="obs-response-label">Time Window</div>
            <div class="obs-response-text">{window}</div>
            <div class="obs-response-label">LLM Used</div>
            <div class="obs-response-text">{llm_text}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    with st.expander("Technical Details"):
        if assumptions:
            st.markdown("**Assumptions:** " + "; ".join(assumptions))
        if technical_error:
            st.markdown(f"**Error:** {technical_error}")
        payload = metric_data if metric_data is not None else (
            evidence if isinstance(evidence, dict) else None
        )
        if payload:
            st.json(payload)
        elif not technical_error:
            st.caption("No additional technical payload.")
