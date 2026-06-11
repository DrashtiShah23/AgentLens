"""AI Failure Observatory — executive reliability command center."""

import streamlit as st

from app.dashboard.components.layout import inject_css, sidebar_nav
from app.dashboard.views import view_failures, view_investigation, view_models
from app.dashboard.views import view_overview, view_prompts, view_runs
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader
from observatory.config.settings import get_settings

st.set_page_config(
    page_title="AI Failure Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom navigation only — views/ folder avoids Streamlit auto-multipage sidebar
NAV = {
    "Executive Overview": view_overview,
    "Failure Observatory": view_failures,
    "Prompt Regression Center": view_prompts,
    "Model Trust Leaderboard": view_models,
    "Run Review Center": view_runs,
    "Root Cause Copilot": None,
}


@st.cache_resource
def _reader() -> WarehouseReader:
    return WarehouseReader(get_settings())


@st.cache_resource
def _metrics() -> MetricService:
    return MetricService(_reader(), get_settings())


def main() -> None:
    inject_css()
    choice = sidebar_nav(list(NAV.keys()))
    st.sidebar.caption("Reads DuckDB marts directly — no Airflow or API required.")

    if choice == "Root Cause Copilot":
        view_investigation.render()
    else:
        NAV[choice].render(_metrics(), _reader())


if __name__ == "__main__":
    main()
