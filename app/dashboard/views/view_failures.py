import streamlit as st

from app.dashboard.components.badges import severity_badge
from app.dashboard.components.charts import failure_ranking_chart, failure_trend_chart, hbar_chart
from app.dashboard.components.filters import date_window_filter, optional_select
from app.dashboard.components.layout import (
    FAILURE_COLS, action_card, demo_note, friendly_failure, insight_card,
    page_header, rename_for_display, section_header, warehouse_missing,
)
from app.dashboard.data_helpers import extended_overview_kpis, failure_trends_stacked
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader


def render(metrics: MetricService, reader: WarehouseReader) -> None:
    page_header(
        "Failure Observatory",
        "What is breaking and how serious is it?",
        "Failures are grouped by root cause so teams can prioritize fixes instead of reading thousands of logs.",
    )
    insight_card(
        "What this means",
        "Each failure is classified by type — Unsupported Answer, SQL Generation Error, Missing Context, and more.",
    )

    if not reader.db_path_exists:
        warehouse_missing()
        return
    demo_note(extended_overview_kpis(reader, 30).get("has_data", False))

    days = date_window_filter(30)
    base = metrics.failure_records(days=days, limit=1000)

    if not base.empty and "severity" in base.columns:
        section_header("Severity Summary")
        sev = base.groupby("severity").size().reset_index(name="count")
        cols = st.columns(4)
        for i, row in sev.iterrows():
            with cols[i % 4]:
                st.markdown(
                    f'<div class="obs-card" style="text-align:center;">{severity_badge(row["severity"])}'
                    f'<div style="font-size:1.6rem;font-weight:700;color:#f8fafc;margin-top:0.4rem;">{row["count"]}</div>'
                    f'<div style="font-size:0.8rem;color:#94a3b8;">incidents</div></div>',
                    unsafe_allow_html=True,
                )

    cats = metrics.failures_by_category(days)
    if not cats.empty:
        section_header("Top Failure Types")
        failure_ranking_chart(cats, "failure_category", "failure_count", "Most Common Failure Types")

    section_header("Failure Trend Over Time")
    stacked = failure_trends_stacked(reader, days)
    if not stacked.empty:
        stacked = stacked.copy()
        stacked["label"] = stacked["failure_category"].map(friendly_failure)
        failure_trend_chart(stacked, "Failures Over Time")
    else:
        st.info("No failures recorded in this time window. Try widening the time window.")

    if not base.empty and "failure_category" in base.columns:
        root = base.groupby("failure_category").size().reset_index(name="count")
        root["label"] = root["failure_category"].map(friendly_failure)
        root = root.sort_values("count", ascending=True).tail(8)
        hbar_chart(root, "label", "count", "Top Root Causes by Volume", semantic="failure_count", x_label="Incidents")

    section_header("High-Priority Incidents")
    high = (
        base[base["severity"].isin(["critical", "high"])]
        if not base.empty and "severity" in base.columns else base.head(6)
    )
    if not high.empty:
        for _, row in high.head(5).iterrows():
            cat = friendly_failure(row.get("failure_category", ""))
            st.markdown(
                f'<div class="obs-card"><div class="obs-card-title">{severity_badge(row.get("severity",""))} {cat}</div>'
                f'<div class="obs-card-body"><strong>{row.get("agent_name","")}</strong> · Prompt {row.get("prompt_version_id","")}<br>'
                f'Recommended fix: {row.get("recommendation", "Review run details in Run Review Center")}</div></div>',
                unsafe_allow_html=True,
            )
        top = high.iloc[0]
        action_card(
            f"Start with {friendly_failure(top.get('failure_category', ''))} on agent "
            f"{top.get('agent_name', 'unknown')} — highest priority incident in this window."
        )
    else:
        action_card("No high-severity incidents in this window. Review medium-severity patterns below.")

    section_header("Filters")
    severities = base["severity"].dropna().unique().tolist() if not base.empty and "severity" in base.columns else []
    agents = base["agent_name"].dropna().unique().tolist() if not base.empty else []
    prompts = base["prompt_version_id"].dropna().unique().tolist() if not base.empty else []
    categories = base["failure_category"].dropna().unique().tolist() if not base.empty and "failure_category" in base.columns else []
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        severity = optional_select("Severity", severities)
    with f2:
        agent = optional_select("Agent", agents)
    with f3:
        prompt = optional_select("Prompt Version", prompts)
    with f4:
        category = optional_select("Failure Type", categories)

    df = metrics.failure_records(
        days=days, severity=severity, agent_name=agent,
        prompt_version_id=prompt, failure_category=category, limit=200,
    )
    section_header("Detailed Failure Log")
    if df.empty:
        st.info("No failures match your filters.")
    else:
        show = rename_for_display(df, FAILURE_COLS)
        if "Confidence" in show.columns:
            show["Confidence"] = show["Confidence"].apply(
                lambda v: f"{float(v)*100:.0f}%" if v is not None else "Not applicable"
            )
        st.dataframe(show, use_container_width=True, hide_index=True)
