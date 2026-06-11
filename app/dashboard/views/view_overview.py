import streamlit as st

from app.dashboard.components.badges import regression_badge, reliability_badge
from app.dashboard.components.charts import failure_ranking_chart, hbar_chart, line_chart
from app.dashboard.components.layout import (
    action_card, demo_note, format_cost, format_count, format_latency, format_percent,
    format_score, friendly_failure, health_banner, insight_card, metric_card,
    page_header, risk_card, section_header, status_from_score, warehouse_missing,
)
from app.dashboard.components.metrics_validation import normalize_rate
from app.dashboard.components.score_explainer import score_disclaimer, score_explainer
from app.dashboard.components.styles import CHART_COLORS, FAILURE_LABELS
from app.dashboard.components.filters import date_window_filter
from app.dashboard.data_helpers import extended_overview_kpis, ranked_models, top_failing_agents
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader


def _interp_reliability(s):
    if s is None:
        return "Not enough data to assess reliability."
    if s >= 0.85:
        return "Agents are performing well — users can trust most responses."
    if s >= 0.70:
        return "Acceptable but watch for emerging failure patterns."
    if s >= 0.50:
        return "The average run is partially reliable — failure patterns need review."
    return "Reliability is critically low — immediate investigation recommended."


def _health_message(rel, fail):
    if rel is None:
        return "warning", "Overall health unknown — load demo data to assess agent reliability."
    fr = normalize_rate(fail) or 0
    if rel >= 0.85 and fr < 0.15:
        return "healthy", f"Overall health is strong at {format_score(rel)}. Agents are reliable today."
    if rel >= 0.70:
        return "warning", f"Overall health is acceptable at {format_score(rel)}, but failure patterns need review."
    return "critical", f"Overall health is at risk — reliability is only {format_score(rel)}. Immediate review recommended."


def render(metrics: MetricService, reader: WarehouseReader) -> None:
    page_header(
        "AI Failure Observatory",
        "Reliability intelligence for AI agent systems",
        "Are our AI agents healthy? What is the biggest risk? What should we fix next?",
    )
    insight_card(
        "What this means",
        "This dashboard monitors synthetic AI agent runs and shows where reliability breaks down before users lose trust.",
    )
    score_disclaimer()
    score_explainer(compact=True)

    if not reader.db_path_exists:
        warehouse_missing()
        return

    days = date_window_filter(7)
    o = metrics.overview_metrics(days)
    x = extended_overview_kpis(reader, days)
    if o.get("total_runs", 0) == 0:
        warehouse_missing()
        return
    demo_note(x.get("has_data", False), x.get("v5_regression", False))

    rel, fail = o.get("reliability_score"), normalize_rate(o.get("failure_rate"))
    status, msg = _health_message(rel, fail)
    health_banner(status, msg)

    top_cat = o.get("top_failure_category")
    if top_cat:
        risk_card(
            "Biggest Risk",
            f"{friendly_failure(top_cat)} is the top failure type affecting "
            f"{o.get('top_affected_agent', 'agents')} — prioritize this in Failure Observatory.",
        )

    section_header("Key Health Indicators")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        metric_card("Runs", "Total Runs", format_count(o.get("total_runs")),
                    "Agent executions analyzed in this window.", "neutral")
    with r2:
        metric_card("Rel", "Overall Reliability", format_score(rel), _interp_reliability(rel),
                    status_from_score(rel), reliability_badge(rel))
    with r3:
        metric_card("Fail", "Failure Rate", format_percent(fail),
                    "Share of runs scoring below the reliability threshold.",
                    status_from_score(1 - (fail or 0)))
    with r4:
        metric_card("Ans", "Unsupported Answer Rate", format_percent(x.get("hallucination_rate")),
                    "Runs where the agent gave unsupported answers.",
                    status_from_score(1 - (normalize_rate(x.get("hallucination_rate")) or 0)))

    r5, r6, r7, r8 = st.columns(4)
    with r5:
        metric_card("SQL", "SQL Success Rate", format_score(x.get("sql_success_rate")),
                    "How often generated SQL passes quality checks.", status_from_score(x.get("sql_success_rate")), "model")
    with r6:
        metric_card("Time", "Avg Latency", format_latency(o.get("avg_latency_ms")),
                    "Typical response time per agent run.", "cost")
    with r7:
        metric_card("Cost", "Estimated Cost", format_cost(o.get("total_cost_usd")),
                    "Total spend across analyzed runs.", "cost")
    with r8:
        n = x.get("prompt_regressions", 0)
        metric_card("Reg", "Prompt Regressions", str(n),
                    "Prompt versions flagged as worse than baseline.",
                    "critical" if n else "healthy", regression_badge(n > 0) if n else "")

    section_header("Trends & Rankings")
    c1, c2 = st.columns(2)
    with c1:
        trend = metrics.reliability_over_time(days)
        if not trend.empty:
            line_chart(trend, "run_date", "reliability_score", "Reliability Trend Over Time",
                       y_pct=True, line_color=CHART_COLORS["healthy"])
    with c2:
        cats = metrics.failures_by_category(days)
        if not cats.empty:
            failure_ranking_chart(cats, "failure_category", "failure_count", "Top Failure Types")

    agents = top_failing_agents(reader, days)
    if not agents.empty:
        hbar_chart(agents, "agent_name", "failure_count", "Agents With Most Failures",
                   semantic="failure_count", x_label="Incident Count")

    models = ranked_models(reader)
    if not models.empty:
        section_header("Model Trust Snapshot")
        for _, row in models.head(3).iterrows():
            fr = normalize_rate(row.get("failure_rate")) or 0
            st.markdown(
                f'<div class="obs-card"><div class="obs-card-title">{row["model_name"]} '
                f'{reliability_badge(row.get("reliability_score"))}</div>'
                f'<div class="obs-card-body">Reliability {format_score(row.get("reliability_score"))} · '
                f'Failure rate {fr:.0%}</div></div>',
                unsafe_allow_html=True,
            )

    if x.get("v5_regression"):
        section_header("Prompt Regression Alert")
        st.markdown(
            f'<div class="obs-alert"><strong>Prompt v5 regression scenario detected.</strong> '
            f'{regression_badge(True)} This synthetic prompt is intentionally worse to demonstrate regression detection.</div>',
            unsafe_allow_html=True,
        )

    action = "Review the Failure Observatory page to prioritize fixes by severity."
    if top_cat:
        action = (
            f"Investigate {FAILURE_LABELS.get(top_cat, friendly_failure(top_cat))} failures "
            f"on {o.get('top_affected_agent', 'the affected agent')}."
        )
    action_card(action)
