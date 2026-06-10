from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class EvaluationResult(BaseModel):
    model_config = ConfigDict(strict=False)

    evaluation_id: str
    run_id: str
    correctness_score: Optional[float] = None
    sql_score: Optional[float] = None
    tool_score: Optional[float] = None
    retrieval_score: Optional[float] = None
    format_score: Optional[float] = None
    latency_score: Optional[float] = None
    cost_score: Optional[float] = None
    overall_score: float
    failure_category: Optional[str] = None
    severity: Optional[str] = None
    evaluator_notes: Optional[str] = None
    evaluated_at: datetime

    @field_validator(
        "correctness_score", "sql_score", "tool_score", "retrieval_score",
        "format_score", "latency_score", "cost_score", "overall_score",
        mode="before",
    )
    @classmethod
    def coerce_score(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            return float(stripped)
        return value

    @model_validator(mode="after")
    def validate_score_ranges(self) -> "EvaluationResult":
        for name, score in [
            ("correctness_score", self.correctness_score),
            ("sql_score", self.sql_score),
            ("tool_score", self.tool_score),
            ("retrieval_score", self.retrieval_score),
            ("format_score", self.format_score),
            ("latency_score", self.latency_score),
            ("cost_score", self.cost_score),
            ("overall_score", self.overall_score),
        ]:
            if score is not None and not 0.0 <= score <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        return self
