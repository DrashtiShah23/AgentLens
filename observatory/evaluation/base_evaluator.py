"""Base evaluator interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EvaluatorResult:
    score: Optional[float]
    notes: str = ""
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    error: Optional[str] = None


class BaseEvaluator(ABC):
    name: str = "base"

    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        """Evaluate a run context and return a score between 0.0 and 1.0, or None if N/A."""
