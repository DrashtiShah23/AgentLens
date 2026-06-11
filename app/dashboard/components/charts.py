"""Plotly charts — dark theme, semantic colors, readable margins."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.components.display_helpers import (
    FAILURE_CHART_PALETTE,
    format_bar_value_label,
    format_change_points,
    friendly_prompt_name,
    regression_hover_text,
    risk_color_for_count,
    risk_color_for_failure_rate,
)
from app.dashboard.components.layout import chart_caption, empty_state, friendly_failure, friendly_task
from app.dashboard.components.metrics_validation import normalize_rate, validate_rates_in_df
from app.dashboard.components.styles import CHART_COLORS, PLOTLY_AXIS, PLOTLY_LAYOUT

CHART_MARGIN = dict(l=16, r=96, t=64, b=64)
HBAR_MARGIN = dict(l=180, r=140, t=64, b=56)
CHART_HEIGHT = 440
FAILURE_CHART_HEIGHT = 460


def _layout(fig: go.Figure, title: str, margin: dict | None = None, height: int = CHART_HEIGHT) -> go.Figure:
    cfg = dict(PLOTLY_LAYOUT)
    cfg["title"] = {"text": title, "font": {"size": 15, "color": "#f1f5f9"}, "x": 0}
    cfg["margin"] = margin or CHART_MARGIN
    cfg["height"] = height
    fig.update_layout(**cfg)
    fig.update_xaxes(**PLOTLY_AXIS, automargin=True)
    fig.update_yaxes(**PLOTLY_AXIS, automargin=True)
    return fig


def _bar_text_positions(values: list[float], max_val: float, threshold: float = 0.55):
    """Inside bar for long bars, outside when short."""
    positions, colors = [], []
    for v in values:
        if max_val > 0 and v >= max_val * threshold:
            positions.append("inside")
            colors.append("#f8fafc")
        else:
            positions.append("outside")
            colors.append("#e2e8f0")
    return positions, colors


def _right_margin_for_values(values: list[float], base: int = 140) -> int:
    if not values:
        return base
    longest = max(len(format_bar_value_label(v)) for v in values)
    return max(base, longest * 11 + 72)


def _parse_dates(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return df
    out = df.copy()
    out[col] = pd.to_datetime(out[col], errors="coerce").dt.normalize()
    return out.dropna(subset=[col])


def line_chart(df, x, y, title, color=None, y_pct=False, line_color=None, y_range=None):
    if df.empty or y not in df.columns:
        empty_state("No trend data", f"No data available for: {title}. Try a wider time window.")
        return
    work = _parse_dates(df, x)
    if work.empty:
        empty_state("No trend data", f"No dated records for: {title}.")
        return
    lc = line_color or CHART_COLORS["healthy"]
    if color:
        fig = px.line(work, x=x, y=y, color=color, markers=True,
                      color_discrete_sequence=CHART_COLORS["palette"])
    else:
        fig = px.line(work, x=x, y=y, markers=True)
        fig.update_traces(line_color=lc, marker_color=lc, line_width=2.5)
    if y_pct:
        fig.update_yaxes(tickformat=".0%", range=y_range or [0, 1])
    fig = _layout(fig, title)
    fig.update_xaxes(title="Date", tickformat="%b %d, %Y")
    fig.update_yaxes(title=y.replace("_", " ").title())
    st.plotly_chart(fig, use_container_width=True)


def hbar_chart(
    df, y_col, x_col, title, color_col=None, color_map=None, x_pct=False,
    x_label=None, semantic="neutral", margin=None, friendly_y=None,
):
    if df.empty:
        empty_state("No ranking data", f"No data available for: {title}.")
        return
    work = df.copy()
    if friendly_y and y_col in work.columns:
        work["_display_y"] = work[y_col].apply(friendly_y)
        y_display = "_display_y"
    else:
        y_display = y_col

    if x_pct and x_col in work.columns:
        work[x_col] = work[x_col].apply(normalize_rate)
        work = work.dropna(subset=[x_col])

    colors = None
    if semantic == "failure_rate" and x_col in work.columns:
        colors = [risk_color_for_failure_rate(v) for v in work[x_col]]
    elif semantic == "failure_count" and x_col in work.columns:
        mx = float(work[x_col].max()) if len(work) else 0.0
        colors = [risk_color_for_count(float(v), mx) for v in work[x_col]]
    elif semantic == "reliability" and x_col in work.columns:
        colors = [
            CHART_COLORS["healthy"] if (normalize_rate(v) or 0) >= 0.70
            else CHART_COLORS["warning"] if (normalize_rate(v) or 0) >= 0.50
            else CHART_COLORS["critical"]
            for v in work[x_col]
        ]
    elif semantic == "latency":
        colors = [CHART_COLORS["latency"]] * len(work)
    elif semantic == "cost":
        colors = [CHART_COLORS["cost"]] * len(work)

    values = work[x_col].tolist()
    mx = max(values) if values else 0
    text_labels = [f"{normalize_rate(v) or 0:.0%}" if x_pct else format_bar_value_label(v) for v in values]
    positions, text_colors = _bar_text_positions(values, mx)

    if colors:
        fig = go.Figure(go.Bar(
            x=work[x_col], y=work[y_display], orientation="h",
            marker_color=colors,
            text=text_labels,
            textposition=positions,
            textfont=dict(size=12, color=text_colors),
            hovertemplate=f"%{{y}}<br>{x_label or x_col}: %{{x}}<extra></extra>",
        ))
    elif color_map and y_col in work.columns:
        bar_colors = [color_map.get(str(v), CHART_COLORS["neutral"]) for v in work[y_col]]
        fig = go.Figure(go.Bar(
            x=work[x_col], y=work[y_display], orientation="h",
            marker_color=bar_colors,
            text=text_labels,
            textposition=positions,
            textfont=dict(size=12, color="#e2e8f0"),
        ))
    else:
        fig = px.bar(work, x=x_col, y=y_display, orientation="h",
                     color=color_col, color_discrete_map=color_map,
                     color_discrete_sequence=CHART_COLORS["palette"])
        fig.update_traces(
            text=text_labels,
            textposition="outside", textfont_size=12,
        )

    right = _right_margin_for_values(values) if not x_pct else 96
    margin = margin or {**HBAR_MARGIN, "r": right}
    fig = _layout(fig, title, margin, CHART_HEIGHT)
    if x_pct:
        fig.update_xaxes(title=x_label or x_col.replace("_", " ").title(), tickformat=".0%", range=[0, 1])
    else:
        pad = mx * 1.15 if mx else 1
        fig.update_xaxes(title=x_label or x_col.replace("_", " ").title(), range=[0, pad])
    fig.update_yaxes(title="", tickfont=dict(size=12, color="#e2e8f0"))
    fig.update_layout(showlegend=False, bargap=0.28)
    st.plotly_chart(fig, use_container_width=True)


def failure_ranking_chart(df, category_col, count_col, title, label_col="label", top_n=5):
    """Horizontal failure ranking — red/orange severity colors, readable value labels."""
    if df.empty or count_col not in df.columns:
        empty_state("No failure data", "No failures recorded in this time window.")
        return
    work = df.copy()
    if label_col not in work.columns and category_col in work.columns:
        work[label_col] = work[category_col].map(friendly_failure)
    work = work.sort_values(count_col, ascending=False).head(top_n)
    work = work.sort_values(count_col, ascending=True)

    values = work[count_col].astype(float).tolist()
    mx = max(values) if values else 0.0
    colors = [risk_color_for_count(float(v), mx) for v in values]
    text_labels = [format_bar_value_label(v) for v in values]
    positions, text_colors = _bar_text_positions(values, mx, threshold=0.50)
    hovers = [
        f"{work.iloc[i][label_col]}<br>Incidents: {format_bar_value_label(values[i])}<extra></extra>"
        for i in range(len(work))
    ]

    fig = go.Figure()
    for i in range(len(work)):
        fig.add_trace(go.Bar(
            x=[values[i]], y=[work.iloc[i][label_col]], orientation="h",
            marker_color=[colors[i]],
            text=[text_labels[i]],
            textposition=positions[i],
            textfont=dict(size=13, color=text_colors[i]),
            hovertemplate=hovers[i],
            showlegend=False,
        ))

    right = _right_margin_for_values(values, base=160)
    margin = dict(l=200, r=right, t=64, b=56)
    fig = _layout(fig, title, margin, FAILURE_CHART_HEIGHT)
    pad = mx * 1.18 if mx else 1
    fig.update_xaxes(title="Incident Count", range=[0, pad])
    fig.update_yaxes(title="", tickfont=dict(size=13, color="#e2e8f0"))
    fig.update_layout(showlegend=False, bargap=0.30)
    st.plotly_chart(fig, use_container_width=True)


def failure_trend_chart(df, title="Failures Over Time"):
    if df.empty:
        empty_state("No trend data", "No failures in the selected time window.")
        return
    work = _parse_dates(df, "failure_date")
    if work.empty:
        empty_state("No trend data", "No failures in the selected time window.")
        return
    if "label" not in work.columns and "failure_category" in work.columns:
        work["label"] = work["failure_category"].map(friendly_failure)

    unique_dates = work["failure_date"].nunique()
    if unique_dates == 1:
        day = work.groupby("label", as_index=False)["failure_count"].sum().sort_values("failure_count")
        hbar_chart(day, "label", "failure_count", f"{title} (single day snapshot)",
                   semantic="failure_count", x_label="Incidents")
        return

    pivot = work.groupby(["failure_date", "label"], as_index=False)["failure_count"].sum()
    labels = sorted(pivot["label"].unique())
    color_map = {lab: FAILURE_CHART_PALETTE[i % len(FAILURE_CHART_PALETTE)] for i, lab in enumerate(labels)}
    fig = px.bar(
        pivot, x="failure_date", y="failure_count", color="label",
        title=title, color_discrete_map=color_map,
    )
    fig.update_traces(hovertemplate="Date: %{x|%b %d, %Y}<br>Type: %{fullData.name}<br>Count: %{y:,}<extra></extra>")
    fig = _layout(fig, title, margin=dict(l=16, r=16, t=88, b=64), height=460)
    fig.update_xaxes(title="Date", tickformat="%b %d")
    fig.update_yaxes(title="Incidents")
    fig.update_layout(
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0, font=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)


def stacked_area_chart(df, x, y, color, title):
    failure_trend_chart(df if "failure_date" in df.columns else df.rename(columns={x: "failure_date"}), title)


def scatter_chart(df, x, y, title, color=None, size=None, labels=None, caption=None):
    if df.empty:
        empty_state("No comparison data", f"No data available for: {title}.")
        return
    work = validate_rates_in_df(df, [y] if y.endswith("score") or y == "reliability_score" else [])
    fig = px.scatter(work, x=x, y=y, color=color, size=size, title=title,
                     color_discrete_sequence=CHART_COLORS["palette"],
                     labels=labels or {})
    if y in ("reliability_score",) or str(y).endswith("score"):
        fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig = _layout(fig, title)
    fig.update_traces(marker=dict(size=12, opacity=0.85))
    st.plotly_chart(fig, use_container_width=True)
    if caption:
        chart_caption(caption)


def diverging_bar(
    df,
    y_col,
    x_col,
    title,
    baseline_prompt: str = "prompt_v1_baseline",
    baseline_reliability: float | None = None,
):
    if df.empty:
        empty_state("No delta data", f"No baseline comparison data for: {title}.")
        return
    work = df.copy()
    work["_prompt_id"] = work[y_col].astype(str)
    work["_display"] = work["_prompt_id"].map(friendly_prompt_name)
    work["_delta_pts"] = work[x_col].astype(float) * 100

    if baseline_reliability is None and "reliability_score" in work.columns:
        base_row = work[work["_prompt_id"] == baseline_prompt]
        if not base_row.empty:
            baseline_reliability = float(base_row.iloc[0]["reliability_score"])

    colors, texts, hovers = [], [], []
    for _, row in work.iterrows():
        pid = row["_prompt_id"]
        val = float(row[x_col] or 0)
        if pid == baseline_prompt:
            colors.append(CHART_COLORS["neutral"])
        elif val > 0.0005:
            colors.append(CHART_COLORS["healthy"])
        elif val < -0.0005:
            colors.append(CHART_COLORS["critical"])
        else:
            colors.append(CHART_COLORS["neutral"])
        texts.append(format_change_points(val))
        rel = row.get("reliability_score")
        hovers.append(regression_hover_text(rel, baseline_reliability, val, pid))

    fig = go.Figure()
    for i, row in work.iterrows():
        idx = list(work.index).index(i)
        fig.add_trace(go.Bar(
            x=[row["_delta_pts"]], y=[row["_display"]], orientation="h",
            marker_color=[colors[idx]],
            text=[texts[idx]],
            textposition="outside",
            textfont=dict(size=12, color="#e2e8f0"),
            hovertemplate=hovers[idx] + "<extra></extra>",
            showlegend=False,
        ))

    max_abs = max((abs(v) for v in work["_delta_pts"]), default=5)
    pad = max_abs * 1.35 + 8
    right = _right_margin_for_values([max_abs], base=180)
    margin = dict(l=220, r=right, t=64, b=56)
    fig = _layout(fig, title, margin, CHART_HEIGHT + 40)
    fig.update_xaxes(
        title="Reliability change from baseline (points)",
        range=[-pad, pad],
        tickformat=".0f",
    )
    fig.update_yaxes(title="", tickfont=dict(size=12, color="#e2e8f0"))
    fig.update_layout(showlegend=False, bargap=0.32)
    st.plotly_chart(fig, use_container_width=True)
    chart_caption(
        "A point change compares two percentages directly. "
        "For example, moving from 64% reliability to 44% reliability is a 20 point drop."
    )


def heatmap_chart(df, x, y, z, title, caption=None):
    if df.empty:
        empty_state("No heatmap data", f"No model-by-task data for: {title}.")
        return
    work = validate_rates_in_df(df, [z])
    pivot = work.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
    if x == "task_type":
        pivot.columns = [friendly_task(c) for c in pivot.columns]
    fig = px.imshow(
        pivot, title=title,
        color_continuous_scale=["#ef4444", "#eab308", "#22c55e"],
        aspect="auto", zmin=0, zmax=1,
        labels=dict(color="Reliability"),
    )
    fig = _layout(fig, title, margin=dict(l=110, r=32, t=64, b=96), height=460)
    fig.update_xaxes(title="Task Type", tickfont=dict(size=11))
    fig.update_yaxes(title="Model", tickfont=dict(size=11))
    st.plotly_chart(fig, use_container_width=True)
    if caption:
        chart_caption(caption)
