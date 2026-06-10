from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class RetrievalEvent(BaseModel):
    model_config = ConfigDict(strict=False)

    retrieval_id: str
    run_id: str
    query_text: str
    document_id: str
    chunk_text: str
    rank_position: int
    relevance_score: float
    was_used_in_answer: bool

    @field_validator("rank_position", mode="before")
    @classmethod
    def coerce_rank(cls, value: Any) -> int:
        if isinstance(value, str):
            return int(value.strip())
        return value

    @field_validator("relevance_score", mode="before")
    @classmethod
    def coerce_score(cls, value: Any) -> float:
        if isinstance(value, str):
            return float(value.strip())
        return value

    @field_validator("was_used_in_answer", mode="before")
    @classmethod
    def coerce_bool(cls, value: Any) -> bool:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
            raise ValueError(f"cannot coerce '{value}' to bool")
        return value

    @model_validator(mode="after")
    def validate_bounds(self) -> "RetrievalEvent":
        if self.rank_position <= 0:
            raise ValueError("rank_position must be > 0")
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        return self
