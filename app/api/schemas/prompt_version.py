from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class PromptVersion(BaseModel):
    model_config = ConfigDict(strict=False)

    prompt_version_id: str
    agent_name: str
    prompt_name: str
    prompt_text: str
    created_at: datetime
    active_flag: bool
    change_reason: str

    @field_validator("active_flag", mode="before")
    @classmethod
    def coerce_active_flag(cls, value: Any) -> bool:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
            raise ValueError(f"cannot coerce '{value}' to bool")
        return value

    @model_validator(mode="after")
    def validate_non_empty_text(self) -> "PromptVersion":
        if not self.prompt_text.strip():
            raise ValueError("prompt_text must not be empty")
        if not self.change_reason.strip():
            raise ValueError("change_reason must not be empty")
        return self
