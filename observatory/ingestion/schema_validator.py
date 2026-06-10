"""Pydantic validation with structured error reporting."""

from dataclasses import dataclass
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


@dataclass
class ValidationOutcome:
    valid: bool
    model: BaseModel | None
    errors: list[dict[str, Any]]
    rejection_reason: str | None


def format_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]


def rejection_reason_from_errors(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "unknown validation error"
    parts = [f"{e['field']}: {e['message']}" for e in errors[:3]]
    return "; ".join(parts)


def validate_record(data: dict[str, Any], model_cls: Type[T]) -> ValidationOutcome:
    try:
        model = model_cls.model_validate(data)
        return ValidationOutcome(valid=True, model=model, errors=[], rejection_reason=None)
    except ValidationError as exc:
        errors = format_validation_errors(exc)
        return ValidationOutcome(
            valid=False, model=None, errors=errors,
            rejection_reason=rejection_reason_from_errors(errors),
        )
