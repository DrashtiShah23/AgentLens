"""Backward-compatible re-exports — prefer layout.py and badges.py."""

from app.dashboard.components.layout import (
    action_card,
    demo_note,
    empty_state,
    inject_css,
    insight_card,
    metric_card,
    page_header,
    section_header,
    warehouse_missing,
)
from app.dashboard.components.layout import empty_state as empty_state_card
from app.dashboard.components.layout import metric_card as kpi_tile
from app.dashboard.components.badges import severity_badge

def hero_header(**kwargs):
    page_header(kwargs.get("title", "AI Failure Observatory"),
                kwargs.get("subtitle", ""), kwargs.get("description", ""))

def warehouse_missing_state():
    warehouse_missing()

def sidebar_branding():
    from app.dashboard.components.layout import sidebar_nav
    sidebar_nav()

def product_explanation():
    insight_card("Why deterministic evaluation?",
                 "Every run is scored with rule-based evaluators. LLMs are only used for human investigation questions.")

def response_card(**kwargs):
    from app.dashboard.components.layout import copilot_response
    copilot_response(
        summary=kwargs.get("summary", ""),
        evidence=kwargs.get("metrics") or kwargs.get("evidence"),
        action=kwargs.get("recommended_action", ""),
        llm_used=kwargs.get("llm_used", False),
        time_window=kwargs.get("time_window"),
        assumptions=kwargs.get("assumptions"),
    )
