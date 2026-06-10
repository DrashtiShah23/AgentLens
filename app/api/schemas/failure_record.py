from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class FailureCategory(str):
    HALLUCINATION = "hallucination"
    RETRIEVAL_FAILURE = "retrieval_failure"
    TOOL_FAILURE = "tool_failure"
    SQL_FAILURE = "sql_failure"
    PROMPT_REGRESSION = "prompt_regression"
    REASONING_FAILURE = "reasoning_failure"
    FORMAT_FAILURE = "format_failure"
    LATENCY_FAILURE = "latency_failure"
    COST_FAILURE = "cost_failure"
    PIPELINE_FAILURE = "pipeline_failure"
    UNKNOWN = "unknown"


VALID_CATEGORIES = {
    "hallucination", "retrieval_failure", "tool_failure", "sql_failure",
    "prompt_regression", "reasoning_failure", "format_failure", "latency_failure",
    "cost_failure", "pipeline_failure", "unknown",
}

VALID_SEVERITIES = {"critical", "high", "medium", "low"}


class FailureRecord(BaseModel):
    model_config = ConfigDict(strict=False)

    failure_id: str
    run_id: str
    primary_category: str
    secondary_signals: Optional[list[str]] = None
    confidence_score: float
    severity: str
    recommendation: Optional[str] = None
    requires_human_review: bool = False
    classified_at: datetime

    @field_validator("primary_category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in VALID_CATEGORIES:
            raise ValueError(f"invalid failure category: {value}")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in VALID_SEVERITIES:
            raise ValueError(f"invalid severity: {value}")
        return value

    @model_validator(mode="after")
    def validate_confidence(self) -> "FailureRecord":
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return self
