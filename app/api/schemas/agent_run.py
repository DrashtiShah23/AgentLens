from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, computed_field, field_validator, model_validator


class TaskType(str, Enum):
    TEXT_TO_SQL = "text_to_sql"
    RETRIEVAL_QA = "retrieval_qa"
    TOOL_USE = "tool_use"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"


class AgentRun(BaseModel):
    model_config = ConfigDict(strict=False, str_strip_whitespace=True)

    run_id: str
    agent_name: str
    task_type: TaskType
    user_query: str
    prompt_version_id: str
    model_name: str
    started_at: datetime
    completed_at: datetime
    latency_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    final_answer: str
    success_flag: bool
    error_message: Optional[str] = None
    generated_sql: Optional[str] = None
    expected_answer: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @field_validator("run_id", "agent_name", "user_query", "prompt_version_id", "model_name", "final_answer")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value

    @field_validator("latency_ms", "input_tokens", "output_tokens", mode="before")
    @classmethod
    def coerce_non_negative_int(cls, value: Any) -> int:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("value cannot be empty")
            return int(stripped)
        if isinstance(value, float):
            return int(value)
        return value

    @field_validator("estimated_cost_usd", mode="before")
    @classmethod
    def coerce_cost(cls, value: Any) -> float:
        if isinstance(value, str):
            return float(value.strip())
        return value

    @field_validator("task_type", mode="before")
    @classmethod
    def normalize_task_type(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def validate_timing_and_bounds(self) -> "AgentRun":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")
        if self.input_tokens < 0:
            raise ValueError("input_tokens must be >= 0")
        if self.output_tokens < 0:
            raise ValueError("output_tokens must be >= 0")
        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be >= 0")
        return self

    @computed_field
    @property
    def duration_seconds(self) -> float:
        return (self.completed_at - self.started_at).total_seconds()

    @computed_field
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
