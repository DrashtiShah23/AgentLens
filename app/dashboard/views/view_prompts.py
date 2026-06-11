import streamlit as st

from app.dashboard.components.badges import regression_badge, reliability_badge
from app.dashboard.components.charts import diverging_bar, hbar_chart, scatter_chart
from app.dashboard.components.layout import (
    PROMPT_COLS, action_card, demo_note, format_cost, format_percent, format_score,
    insight_card, page_header, rename_for_display, section_header, warehouse_missing,
)
from app.dashboard.components.metrics_validation import normalize_rate, validate_rates_in_df
from app.dashboard.components.display_helpers import (
    V5_REGRESSION_NOTE, format_change_points, friendly_prompt_name,
)
from app.dashboard.components.score_explainer import score_disclaimer, score_explainer
from app.dashboard.data_helpers import extended_overview_kpis, prompt_baseline_delta
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader


def render(metrics: MetricService, reader: WarehouseReader) -> None:
    page_header(
        "Prompt Regression Center",
        "Did a prompt change make the system worse?",
        "Compare prompt versions and catch quality drops before users do.",
    )
    insight_card(
        "What this means",
        "Each prompt version is scored on reliability, cost, and latency. "
        "Regressions are detected when a newer prompt underperforms the baseline.",
    )
    score_disclaimer()
    score_explainer(compact=True)

    if not reader.db_path_exists:
        warehouse_missing()
        return
    extra = extended_overview_kpis(reader, 30)
    demo_note(extra.get("has_data", False), extra.get("v5_regression", False))

    df = metrics.prompt_performance()
    delta = prompt_baseline_delta(reader)
    if df.empty and delta.empty:
        warehouse_missing()
        return

    agg = validate_rates_in_df(
        df.groupby("prompt_version_id").agg({
            "reliability_score": "mean", "failure_rate": "mean",
            "avg_latency_ms": "mean", "avg_cost_usd": "mean", "run_count": "sum",
        }).reset_index() if not df.empty else delta,
        ["reliability_score", "failure_rate"],
    )

    baseline_row = agg[agg["prompt_version_id"] == "prompt_v1_baseline"]
    baseline_rel = baseline_row.iloc[0]["reliability_score"] if not baseline_row.empty else None

    v5 = agg[agg["prompt_version_id"] == "prompt_v5_regression_case"] if "prompt_version_id" in agg.columns else agg.iloc[0:0]
    if not v5.empty:
        row = v5.iloc[0]
        v5_rel = normalize_rate(row.get("reliability_score"))
        v5_fail = normalize_rate(row.get("failure_rate")) or 0
        delta_val = (v5_rel - normalize_rate(baseline_rel)) if baseline_rel is not None and v5_rel is not None else None
        delta_txt = format_change_points(delta_val) if delta_val is not None else "Not applicable"
        st.markdown(
            f'<div class="obs-alert"><strong>Worst Regression: Prompt v5</strong> {regression_badge(True)}<br>'
            f'{V5_REGRESSION_NOTE}<br>'
            f'Baseline reliability: <strong>{format_score(baseline_rel)}</strong> · '
            f'Regression reliability: <strong>{format_score(v5_rel)}</strong> · '
            f'Change: <strong>{delta_txt}</strong> · '
            f'Failure rate: <strong>{v5_fail:.0%}</strong></div>',
            unsafe_allow_html=True,
        )
        action_card("Roll back this prompt version or inspect prompt changes before wider rollout.")

    section_header("Prompt Reliability Ranking")
    ranked = agg.sort_values("reliability_score", ascending=True) if "reliability_score" in agg.columns else agg
    if not ranked.empty:
        hbar_chart(ranked, "prompt_version_id", "reliability_score",
                   "Prompt Reliability (Best to Worst)", semantic="reliability",
                   x_pct=True, x_label="Reliability Score",
                   friendly_y=friendly_prompt_name)

    if not delta.empty and "reliability_delta" in delta.columns:
        d = delta.sort_values("reliability_delta")
        diverging_bar(
            d, "prompt_version_id", "reliability_delta",
            "Reliability Change from Baseline",
            baseline_reliability=normalize_rate(baseline_rel),
        )

    if not agg.empty and "avg_cost_usd" in agg.columns and "reliability_score" in agg.columns:
        scatter_chart(agg, "avg_cost_usd", "reliability_score",
                      "Cost vs Reliability Tradeoff", color="prompt_version_id",
                      labels={"avg_cost_usd": "Avg Cost ($)", "reliability_score": "Reliability"})

    section_header("Regression Cards")
    if "regression_detected" in df.columns:
        regs = df[df["regression_detected"] == True]
        for _, row in regs.head(4).iterrows():
            st.markdown(
                f'<div class="obs-card" style="border-left:3px solid #a855f7;">'
                f'<div class="obs-card-title">{row.get("prompt_version_id","")} {regression_badge(True)}</div>'
                f'<div class="obs-card-body">Agent: {row.get("agent_name","")} · '
                f'Reliability: {format_score(row.get("reliability_score"))} · '
                f'Cost: {format_cost(row.get("avg_cost_usd"))}</div></div>',
                unsafe_allow_html=True,
            )

    section_header("Detailed Prompt Metrics")
    show = rename_for_display(agg if not delta.empty else df, PROMPT_COLS)
    for col in ["Reliability", "Failure Rate"]:
        if col in show.columns:
            show[col] = show[col].apply(format_percent if col == "Failure Rate" else format_score)
    st.dataframe(show, use_container_width=True, hide_index=True)
