"""Deterministic cost evaluator."""

from typing import Any, Optional

from observatory.config.settings import Settings, get_settings
from observatory.evaluation.base_evaluator import BaseEvaluator, EvaluatorResult


class CostEvaluator(BaseEvaluator):
    name = "cost"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        cost = float(context.get("estimated_cost_usd", 0))
        good = self.settings.cost_good_usd
        threshold = self.settings.cost_threshold_usd
        if cost < good:
            score = 1.0
        elif cost <= threshold:
            score = 0.5
        else:
            score = 0.0
        return EvaluatorResult(score=score, notes=f"cost_usd={cost}")
