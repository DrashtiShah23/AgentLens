"""Legacy metric helpers — delegates to ui.py."""

from app.dashboard.components.ui import empty_state_card as empty_state
from app.dashboard.components.ui import kpi_tile as metric_card

__all__ = ["metric_card", "empty_state"]
