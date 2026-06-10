"""Deterministic latency evaluator."""

from typing import Any, Optional

from observatory.config.settings import Settings, get_settings
from observatory.evaluation.base_evaluator import BaseEvaluator, EvaluatorResult


class LatencyEvaluator(BaseEvaluator):
    name = "latency"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        latency = int(context.get("latency_ms", 0))
        good = self.settings.latency_good_ms
        threshold = self.settings.latency_threshold_ms
        if latency < good:
            score = 1.0
        elif latency <= threshold:
            score = 0.5
        else:
            score = 0.0
        return EvaluatorResult(score=score, notes=f"latency_ms={latency}")
