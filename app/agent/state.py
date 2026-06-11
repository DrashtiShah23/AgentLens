"""Investigation agent state."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class InvestigationState(BaseModel):
    question: str
    time_window_days: int = 7
    selected_tool: Optional[str] = None
    tool_result: Optional[dict[str, Any]] = None
    summary: Optional[str] = None
    assumptions: list[str] = Field(default_factory=list)
    error: Optional[str] = None
