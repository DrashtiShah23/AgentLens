"""Weighted overall reliability score with null exclusion."""

from typing import Any, Optional

from app.api.schemas.agent_run import TaskType

DEFAULT_WEIGHTS = {
    "correctness": 0.35,
    "sql": 0.20,
    "tool": 0.15,
    "retrieval": 0.15,
    "format": 0.10,
    "latency": 0.03,
    "cost": 0.02,
}

TASK_WEIGHT_BOOSTS = {
    TaskType.TEXT_TO_SQL.value: {"sql": 0.10, "correctness": -0.05},
    TaskType.TOOL_USE.value: {"tool": 0.10, "correctness": -0.05},
    TaskType.RETRIEVAL_QA.value: {"retrieval": 0.10, "correctness": -0.05},
}


class OverallScoreCalculator:
    """Compute task-aware weighted average excluding null component scores."""

    def compute(self, task_type: str, component_scores: dict[str, Optional[float]]) -> float:
        weights = self._task_weights(task_type)
        active: list[tuple[str, float, float]] = []
        for name, weight in weights.items():
            score = component_scores.get(name)
            if score is not None:
                active.append((name, weight, score))

        if not active:
            return 0.0

        total_weight = sum(w for _, w, _ in active)
        weighted_sum = sum(w * s for _, w, s in active)
        return round(weighted_sum / total_weight, 4)

    def _task_weights(self, task_type: str) -> dict[str, float]:
        weights = dict(DEFAULT_WEIGHTS)
        boosts = TASK_WEIGHT_BOOSTS.get(task_type, {})
        for key, delta in boosts.items():
            weights[key] = weights.get(key, 0) + delta
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}
