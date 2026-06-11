import streamlit as st

from app.dashboard.components.badges import (
    execution_status_badge, reliability_status_badge, severity_badge,
)
from app.dashboard.components.filters import date_window_filter, optional_select
from app.dashboard.components.layout import (
    format_cost, format_latency, format_score, friendly_failure, friendly_severity, friendly_task,
    format_run_list, insight_card, page_header, section_header, warehouse_missing,
)
from app.dashboard.components.run_selection import (
    failure_details_success_message,
    failure_review_why_text,
    failure_root_cause_text,
    reason_for_row,
    row_for_run_id,
    select_default_run_id,
)
from app.dashboard.components.score_explainer import SCORE_DEFINITIONS, run_scores_note
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader

QUICK = {
    "All runs": {},
    "Failed only": {"success_flag": False},
    "High severity": {"severity": "high"},
    "Prompt regression": {"prompt_version_id": "prompt_v5_regression_case"},
    "SQL generation errors": {"failure_category": "sql_failure"},
    "Unsupported answers": {"failure_category": "hallucination"},
    "Missing context": {"failure_category": "retrieval_failure"},
}

RUN_SCORE_LABELS = {
    "overall_score": "This Run Reliability Score",
    "correctness_score": "This Run Answer Score",
    "sql_score": "This Run SQL Score",
    "retrieval_score": "This Run Context Lookup Score",
    "tool_score": "This Run Tool Score",
    "format_score": "This Run Format Score",
    "latency_score": "This Run Speed Score",
    "cost_score": "This Run Cost Score",
}


def _search(metrics, days, qf, agent=None, model=None, limit=200):
    return metrics.search_runs(
        days=days, limit=limit,
        success_flag=qf.get("success_flag"),
        severity=qf.get("severity"),
        prompt_version_id=qf.get("prompt_version_id"),
        failure_category=qf.get("failure_category"),
        agent_name=agent, model_name=model,
    )


def _format_run_score(value):
    if value is None:
        return "Not applicable"
    return format_score(value)


def _selection_context_key(quick: str, agent, model, days: int) -> str:
    return f"{quick}|{agent}|{model}|{days}"


def _sync_default_selection(df, quick: str, ctx_key: str) -> tuple[str, str]:
    """Reset or initialize selected run when filters change."""
    default_id, default_reason = select_default_run_id(df, quick)
    run_ids = df["run_id"].tolist()

    if st.session_state.get("run_review_ctx") != ctx_key:
        st.session_state.run_review_ctx = ctx_key
        st.session_state.run_pick = default_id
        st.session_state.run_selection_reason = default_reason
    elif st.session_state.get("run_pick") not in run_ids:
        st.session_state.run_pick = default_id
        st.session_state.run_selection_reason = default_reason

    return st.session_state.run_pick, st.session_state.get("run_selection_reason", default_reason)


def render(metrics: MetricService, reader: WarehouseReader) -> None:
    page_header(
        "Run Review Center",
        "Which individual agent runs need human review?",
        "Filter failed or risky runs, then inspect the full story for each one.",
    )
    insight_card(
        "Individual run review",
        "This page reviews individual agent runs. A single run can score 100% if it passed all "
        "applicable checks, even if the model is not always reliable overall.",
    )
    insight_card(
        "Aggregate comparison",
        "Use Model Trust Leaderboard for aggregate model performance.",
    )
    with st.expander("What do these scores mean?"):
        for title, body in SCORE_DEFINITIONS.items():
            st.markdown(f"**{title}:** {body}")

    if not reader.db_path_exists:
        warehouse_missing()
        return

    days = date_window_filter(30)
    quick = st.radio("Quick filter", list(QUICK.keys()), horizontal=True)
    qf = QUICK[quick]

    preview = _search(metrics, days, {})
    agents = preview["agent_name"].dropna().unique().tolist() if not preview.empty else []
    models = preview["model_name"].dropna().unique().tolist() if not preview.empty else []

    left, right = st.columns([1, 1])
    with left:
        section_header("Run List")
        agent = optional_select("Agent", agents) if agents else None
        model = optional_select("Model", models) if models else None
        df = _search(metrics, days, qf, agent, model)
        if df.empty:
            st.info("No runs match your filters.")
            return

        ctx_key = _selection_context_key(quick, agent, model, days)
        default_selected, _ = _sync_default_selection(df, quick, ctx_key)
        run_ids = df["run_id"].tolist()
        pick_index = run_ids.index(default_selected) if default_selected in run_ids else 0

        cols_show = [c for c in ["run_id", "agent_name", "overall_score", "success_flag",
                                  "failure_category", "severity"] if c in df.columns]
        display = format_run_list(df[cols_show])
        st.dataframe(display, use_container_width=True, hide_index=True, height=320)

        selected = st.selectbox(
            "Select run to inspect",
            run_ids,
            index=pick_index,
            key="run_pick",
        )
        selected_row = row_for_run_id(df, selected) or {}
        selection_reason = reason_for_row(selected_row, quick)
        st.session_state.run_selection_reason = selection_reason
        st.markdown(f"**Inspecting selected run:** `{selected}`")

    with right:
        section_header("Run Detail")
        detail = metrics.run_detail(selected)
        if not detail:
            st.info("Run details not found.")
            return
        run = detail.get("run", {})
        fail = detail.get("failure") or {}
        ev = detail.get("evaluation") or {}
        score = ev.get("overall_score") if ev else None
        fail_cat = fail.get("primary_category") if fail else selected_row.get("failure_category")
        sev = fail.get("severity") if fail else selected_row.get("severity")
        fail_type_label = friendly_failure(fail_cat) if fail_cat else None

        card_lines = [
            execution_status_badge(bool(run.get("success_flag"))),
            reliability_status_badge(score, fail_cat, sev),
        ]
        if fail_type_label:
            card_lines.append(f'<span class="obs-badge obs-badge-warning">{fail_type_label}</span>')
        card_lines.append(severity_badge(sev))

        st.markdown(
            f'<div class="obs-card" style="border:2px solid #6366f1;">'
            f'<div class="obs-card-title" style="font-size:1.05rem;">Selected Run</div>'
            f'<div class="obs-card-body" style="font-size:0.95rem;line-height:2.2;">'
            f'{" ".join(card_lines)}</div>'
            f'<div class="obs-card-body" style="font-size:0.88rem;color:#94a3b8;margin-top:0.5rem;">'
            f'Selected because: <strong>{selection_reason}</strong></div></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Execution status tells whether the agent run completed. "
            "Reliability status tells whether the output should be trusted."
        )
        run_scores_note()

        tabs = st.tabs([
            "Summary", "Input and Output", "SQL", "Tools", "Context Lookup",
            "Scores", "Failure Details", "Technical Details",
        ])
        with tabs[0]:
            st.markdown(f"**Agent:** {run.get('agent_name','—')}")
            st.markdown(f"**Model:** {run.get('model_name','—')}")
            st.markdown(f"**Prompt:** {run.get('prompt_version_id','—')}")
            st.markdown(f"**Task:** {friendly_task(run.get('task_type','')) or 'Not applicable'}")
            st.markdown(f"**Reliability:** {_format_run_score(score)}")
            st.markdown(f"**Latency:** {format_latency(run.get('latency_ms'))}")
            st.markdown(f"**Cost:** {format_cost(run.get('estimated_cost_usd'))}")
        with tabs[1]:
            st.markdown("**User Question**")
            st.code(run.get("user_query", "—"))
            st.markdown("**Agent Answer**")
            st.code(run.get("final_answer", "—"))
            st.markdown("**Expected Answer**")
            st.code(run.get("expected_answer") or "Not provided")
        with tabs[2]:
            st.code(run.get("generated_sql") or "No SQL for this run", language="sql")
        with tabs[3]:
            t = detail.get("tool_calls", [])
            st.dataframe(t, use_container_width=True) if t else st.caption("No tool calls.")
        with tabs[4]:
            r = detail.get("retrieval_events", [])
            st.dataframe(r, use_container_width=True) if r else st.caption("No context lookup events.")
        with tabs[5]:
            if ev:
                sc = {k: v for k, v in ev.items() if str(k).endswith("_score")}
                if sc:
                    for k, v in sc.items():
                        label = RUN_SCORE_LABELS.get(k, k.replace("_", " ").title())
                        st.markdown(f"**{label}:** {_format_run_score(v)}")
                else:
                    st.caption("No evaluation scores.")
            else:
                st.caption("No evaluation scores.")
        with tabs[6]:
            if fail:
                fail_type = friendly_failure(fail.get("primary_category"))
                st.markdown(f"**Failure Type:** {fail_type or 'Not applicable'}")
                st.markdown(f"**Severity:** {friendly_severity(fail.get('severity'))}")
                st.markdown(f"**Root Cause:** {failure_root_cause_text(fail)}")
                st.markdown(f"**Recommended Fix:** {fail.get('recommendation') or 'Not applicable'}")
                confidence = fail.get("confidence_score")
                if confidence is not None:
                    st.markdown(f"**Confidence:** {float(confidence) * 100:.0f}%")
                st.markdown(f"**Why this needs review:** {failure_review_why_text(fail, score)}")
            else:
                st.success(failure_details_success_message())
        with tabs[7]:
            st.json({"run": run, "evaluation": ev, "failure": fail,
                     "tool_calls": detail.get("tool_calls", []),
                     "retrieval_events": detail.get("retrieval_events", [])})
