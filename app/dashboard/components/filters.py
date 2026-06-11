"""Shared filter widgets."""

from typing import Optional

import streamlit as st


def date_window_filter(default_days: int = 7) -> int:
    return st.sidebar.selectbox(
        "Time window",
        options=[7, 14, 30, 90],
        index=[7, 14, 30, 90].index(default_days) if default_days in [7, 14, 30, 90] else 0,
    )


def optional_select(label: str, options: list[str]) -> Optional[str]:
    choices = ["All"] + sorted(set(o for o in options if o))
    selected = st.selectbox(label, choices)
    return None if selected == "All" else selected
