"""Deterministic retrieval evaluator."""

from typing import Any, Optional

from observatory.config.settings import Settings, get_settings
from observatory.evaluation.base_evaluator import BaseEvaluator, EvaluatorResult


class RetrievalEvaluator(BaseEvaluator):
    name = "retrieval"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        events = context.get("retrieval_events", [])
        task = context.get("task_type", "")
        if task not in {"retrieval_qa", "summarization"} and not events:
            return EvaluatorResult(score=None, notes="no retrieval data for task")

        total = 4
        passed = 0
        checks: list[str] = []

        if not events:
            return EvaluatorResult(score=0.0, checks_failed=["has_events"])
        checks.append("has_events")
        passed += 1

        top = min(events, key=lambda e: e.get("rank_position", 999))
        threshold = self.settings.retrieval_relevance_threshold
        if top.get("relevance_score", 0) >= threshold:
            checks.append("top_relevance")
            passed += 1
        else:
            return EvaluatorResult(score=passed / total, checks_passed=checks,
                                   checks_failed=["top_relevance"])

        if any(e.get("was_used_in_answer") for e in events):
            checks.append("chunk_used")
            passed += 1
        else:
            return EvaluatorResult(score=passed / total, checks_passed=checks,
                                   checks_failed=["chunk_used"])

        if any(e.get("chunk_text", "").strip() for e in events):
            checks.append("non_empty")
            passed += 1
        else:
            return EvaluatorResult(score=passed / total, checks_passed=checks,
                                   checks_failed=["non_empty"])

        return EvaluatorResult(score=1.0, checks_passed=checks)
