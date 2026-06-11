"""Global score definitions for non-technical dashboard users."""

from __future__ import annotations

import streamlit as st

SCORE_DEFINITIONS = {
    "Reliability Score": (
        "Weighted deterministic score across applicable checks for a run, prompt, model, or agent."
    ),
    "Answer Quality": "How closely the final answer matched the expected answer.",
    "SQL Quality": "Whether generated SQL was valid, safe, and structurally correct.",
    "Tool Quality": "Whether the right tool was called and completed successfully.",
    "Context Lookup Quality": "Whether the agent found relevant supporting context.",
    "Speed Score": "Whether latency stayed under threshold.",
    "Cost Score": "Whether cost stayed under threshold.",
}

from app.dashboard.components.display_helpers import RUN_PERFECT_SCORE_NOTE, SCORE_DISCLAIMER

DEMO_NOTE = SCORE_DISCLAIMER


def score_explainer(*, compact: bool = False) -> None:
    """Show expandable score definitions and demo data disclaimer."""
    if compact:
        st.caption(DEMO_NOTE)
        return
    with st.expander("What do these scores mean?"):
        for title, body in SCORE_DEFINITIONS.items():
            st.markdown(f"**{title}:** {body}")
        st.markdown(f"*{DEMO_NOTE}*")


def score_disclaimer() -> None:
    st.caption(SCORE_DISCLAIMER)


def run_scores_note() -> None:
    st.markdown(
        '<div class="obs-insight"><strong>Selected run scores</strong><br>'
        f"{RUN_PERFECT_SCORE_NOTE}</div>",
        unsafe_allow_html=True,
    )
