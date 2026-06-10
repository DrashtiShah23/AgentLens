from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ToolStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ToolCall(BaseModel):
    model_config = ConfigDict(strict=False)

    tool_call_id: str
    run_id: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Optional[dict[str, Any]] = None
    tool_status: ToolStatus
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    latency_ms: int

    @field_validator("latency_ms", mode="before")
    @classmethod
    def coerce_latency(cls, value: Any) -> int:
        if isinstance(value, str):
            return int(value.strip())
        return value

    @field_validator("tool_status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def validate_timing(self) -> "ToolCall":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")
        return self
