import streamlit as st

from app.dashboard.components.badges import reliability_badge, task_risk_badge
from app.dashboard.components.charts import hbar_chart, heatmap_chart, scatter_chart
from app.dashboard.components.display_helpers import (
    friendly_task_name, task_recommendation_text, task_risk_label,
)
from app.dashboard.components.layout import (
    MODEL_COLS, demo_note, format_cost, format_latency, format_percent, format_score,
    insight_card, page_header, rename_for_display, section_header, warehouse_missing,
)
from app.dashboard.components.metrics_validation import normalize_rate, validate_rates_in_df
from app.dashboard.components.score_explainer import SCORE_DEFINITIONS, score_disclaimer
from app.dashboard.data_helpers import (
    best_model_by_task, extended_overview_kpis, model_failure_rates_by_model, ranked_models,
)
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader

_BORDER = {"healthy": "#22c55e", "warning": "#f97316", "critical": "#ef4444", "model": "#3b82f6"}


def _task_card(row) -> str:
    task = friendly_task_name(row.get("task_type", ""))
    rel = row.get("reliability_score")
    rel_pct = format_score(rel)
    risk, level = task_risk_label(rel)
    border = _BORDER.get(level, "#64748b")
    rec = task_recommendation_text(row.get("task_type", ""), rel)
    return (
        f'<div class="obs-card" style="border-left:4px solid {border};min-height:168px;">'
        f'<div class="obs-card-title">{task}</div>'
        f'<div class="obs-card-body">'
        f'<strong>Best model:</strong> {row.get("model_name", "—")}<br>'
        f'<strong>Reliability:</strong> {rel_pct}<br>'
        f'{task_risk_badge(rel)}<br><br>{rec}</div></div>'
    )


def render(metrics: MetricService, reader: WarehouseReader) -> None:
    page_header(
        "Model Trust Leaderboard",
        "Which model should we trust for each task?",
        "This page helps decide which model to use for each type of agent task.",
    )
    insight_card(
        "Aggregate model scores",
        "Model scores are aggregate scores across many synthetic agent runs. "
        "Use this page to compare model reliability, latency, cost, and task fit.",
    )
    insight_card(
        "Task-specific fit",
        "A model can be strong for one task and risky for another. "
        "Use Best Model by Task for task-specific decisions.",
    )
    score_disclaimer()
    with st.expander("What do these scores mean?"):
        for title, body in SCORE_DEFINITIONS.items():
            st.markdown(f"**{title}:** {body}")

    if not reader.db_path_exists:
        warehouse_missing()
        return
    demo_note(extended_overview_kpis(reader, 30).get("has_data", False))

    df = validate_rates_in_df(ranked_models(reader), ["reliability_score", "failure_rate"])
    model_fr = model_failure_rates_by_model(reader)
    if df.empty:
        warehouse_missing()
        return

    best = df.iloc[0]
    sql_df = df[df["task_type"] == "text_to_sql"] if "task_type" in df.columns else df.iloc[0:0]
    best_sql = sql_df.iloc[0] if not sql_df.empty else best

    section_header("Model Highlights")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            f'<div class="obs-scorecard"><div class="obs-scorecard-rank">1</div>'
            f'<div class="obs-scorecard-name">Best Overall Model</div>'
            f'<div class="obs-scorecard-stat">{best["model_name"]}<br>'
            f'{format_score(best.get("reliability_score"))} {reliability_badge(best.get("reliability_score"))}</div>'
            f'<div class="obs-card-body">Highest average reliability across all tasks in the demo dataset.</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="obs-scorecard"><div class="obs-scorecard-rank">SQL</div>'
            f'<div class="obs-scorecard-name">Best Text to SQL Model</div>'
            f'<div class="obs-scorecard-stat">{best_sql["model_name"]}<br>'
            f'{format_score(best_sql.get("reliability_score"))}</div>'
            f'<div class="obs-card-body">Top reliability for Text to SQL tasks specifically.</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        if "avg_latency_ms" in df.columns:
            fast = df.loc[df["avg_latency_ms"].idxmin()]
            st.markdown(
                f'<div class="obs-scorecard"><div class="obs-scorecard-rank">Fast</div>'
                f'<div class="obs-scorecard-name">Fastest Model</div>'
                f'<div class="obs-scorecard-stat">{fast["model_name"]}<br>'
                f'{format_latency(fast.get("avg_latency_ms"))}</div>'
                f'<div class="obs-card-body">Lowest average response time — speed may trade off with accuracy.</div></div>',
                unsafe_allow_html=True,
            )
    with c4:
        if "avg_cost_usd" in df.columns:
            cheap = df.loc[df["avg_cost_usd"].idxmin()]
            st.markdown(
                f'<div class="obs-scorecard"><div class="obs-scorecard-rank">$</div>'
                f'<div class="obs-scorecard-name">Lowest Cost Model</div>'
                f'<div class="obs-scorecard-stat">{cheap["model_name"]}<br>'
                f'{format_cost(cheap.get("avg_cost_usd"))}/run</div>'
                f'<div class="obs-card-body">Cheapest per run — verify reliability before switching.</div></div>',
                unsafe_allow_html=True,
            )
    with c5:
        if not model_fr.empty and "failure_rate" in model_fr.columns:
            risky = model_fr.loc[model_fr["failure_rate"].idxmax()]
            fr = normalize_rate(risky.get("failure_rate")) or 0
            st.markdown(
                f'<div class="obs-scorecard"><div class="obs-scorecard-rank">!</div>'
                f'<div class="obs-scorecard-name">Riskiest Model</div>'
                f'<div class="obs-scorecard-stat">{risky["model_name"]}<br>'
                f'{fr:.0%} failure rate</div>'
                f'<div class="obs-card-body">Highest share of runs below the reliability threshold.</div></div>',
                unsafe_allow_html=True,
            )

    section_header("Best Model by Task")
    st.markdown(
        "This section recommends the most reliable model for each agent task using deterministic scores "
        "from synthetic demo runs. Higher reliability means the model passed more checks for that task."
    )
    by_task = best_model_by_task(reader)
    if not by_task.empty:
        n = len(by_task)
        cols = st.columns(min(n, 3))
        for i, (_, row) in enumerate(by_task.iterrows()):
            with cols[i % len(cols)]:
                st.markdown(_task_card(row), unsafe_allow_html=True)
    else:
        st.info("No task-level model data available.")

    insight_card(
        "Overall takeaway",
        "Use the strongest model for each task rather than picking one model for everything. "
        "Some tasks may still be risky even for the best model.",
    )

    section_header("Model Reliability Leaderboard")
    chart_df = df.copy()
    chart_df["label"] = chart_df.apply(
        lambda r: f"{r['model_name']} ({friendly_task_name(r.get('task_type', ''))})", axis=1,
    )
    ranked = chart_df.sort_values("reliability_score", ascending=True)
    hbar_chart(ranked, "label", "reliability_score", "Model Reliability Ranking",
               semantic="reliability", x_pct=True, x_label="Reliability Score")

    c1, c2 = st.columns(2)
    with c1:
        if "avg_cost_usd" in df.columns:
            scatter_chart(
                df, "avg_cost_usd", "reliability_score", "Cost vs Reliability",
                color="model_name",
                labels={"avg_cost_usd": "Avg Cost ($)", "reliability_score": "Reliability"},
                caption="Cost vs reliability shows which models are cheap but risky or expensive but reliable.",
            )
    with c2:
        if "avg_latency_ms" in df.columns:
            scatter_chart(
                df, "avg_latency_ms", "reliability_score", "Latency vs Reliability",
                color="model_name",
                labels={"avg_latency_ms": "Latency (ms)", "reliability_score": "Reliability"},
                caption="Latency vs reliability shows which models are fast but less reliable or slower but safer.",
            )

    if not model_fr.empty:
        fr = model_fr.sort_values("failure_rate", ascending=True).copy()
        fr["label"] = fr["model_name"]
        hbar_chart(fr, "label", "failure_rate", "Failure Rate by Model",
                   semantic="failure_rate", x_pct=True, x_label="Failure Rate (0%–100%)")

    with st.expander("Advanced: Model by task heatmap"):
        heatmap_chart(
            df, "task_type", "model_name", "reliability_score", "Model vs Task Reliability",
            caption=(
                "Green means higher reliability. Orange or red means riskier performance. "
                "This is a technical view; use the cards above for recommendations."
            ),
        )

    section_header("Detailed Model Metrics")
    show = rename_for_display(df, MODEL_COLS)
    if "Failure Rate" in show.columns:
        show["Failure Rate"] = show["Failure Rate"].apply(format_percent)
    if "Reliability" in show.columns:
        show["Reliability"] = show["Reliability"].apply(format_score)
    st.dataframe(show, use_container_width=True, hide_index=True)
