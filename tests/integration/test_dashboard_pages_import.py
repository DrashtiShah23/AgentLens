"""Smoke imports for dashboard page modules — no Streamlit launch required."""

import importlib

import pytest

from app.dashboard.components.layout import sidebar_nav
from app.dashboard.components.styles import FAILURE_LABELS, SEVERITY_LABELS, TASK_LABELS

PAGE_MODULES = [
    "app.dashboard.views.view_overview",
    "app.dashboard.views.view_failures",
    "app.dashboard.views.view_prompts",
    "app.dashboard.views.view_models",
    "app.dashboard.views.view_runs",
    "app.dashboard.views.view_investigation",
]


@pytest.mark.parametrize("module_path", PAGE_MODULES)
def test_dashboard_page_module_imports(module_path):
    mod = importlib.import_module(module_path)
    assert hasattr(mod, "render")


def test_sidebar_nav_importable():
    assert callable(sidebar_nav)


def test_failure_label_mappings_available():
    assert FAILURE_LABELS["retrieval_failure"] == "Missing Context"
    assert FAILURE_LABELS["sql_failure"] == "SQL Generation Error"
    assert SEVERITY_LABELS["high"] == "High"
    assert TASK_LABELS["tool_use"] == "Tool Use"


def test_model_leaderboard_helpers_importable():
    from app.dashboard.components.layout import demo_note, friendly_task
    from app.dashboard.data_helpers import ranked_models

    assert callable(demo_note)
    assert callable(friendly_task)
    assert callable(ranked_models)
