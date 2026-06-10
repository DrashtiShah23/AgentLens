"""Rule-based deterministic failure classifier."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ClassificationResult:
    primary_category: str
    secondary_signals: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    requires_human_review: bool = False


class FailureClassifier:
    """Assign failure category from evaluation signals — no LLM."""

    PROMPT_V5 = "prompt_v5_regression_case"

    def classify(self, context: dict[str, Any]) -> ClassificationResult:
        if context.get("is_duplicate"):
            return ClassificationResult("pipeline_failure", ["duplicate_run_id"], 0.95)

        scores = {
            "correctness": context.get("correctness_score"),
            "sql": context.get("sql_score"),
            "tool": context.get("tool_score"),
            "retrieval": context.get("retrieval_score"),
            "format": context.get("format_score"),
            "latency": context.get("latency_score"),
            "cost": context.get("cost_score"),
        }
        task = context.get("task_type", "")
        overall = context.get("overall_score", 1.0)
        prompt = context.get("prompt_version_id", "")
        tool_calls = context.get("tool_calls", [])
        retrieval_events = context.get("retrieval_events", [])
        metadata = context.get("metadata") or {}
        scenario = metadata.get("scenario", "") if isinstance(metadata, dict) else ""

        signals: list[tuple[str, float, str]] = []

        if task == "text_to_sql" and scores["sql"] is not None and scores["sql"] < 0.5:
            signals.append(("sql_failure", 0.9, "low_sql_score"))
        if scores["tool"] is not None and scores["tool"] < 0.5:
            signals.append(("tool_failure", 0.85, "low_tool_score"))
        if any(tc.get("tool_status") in {"failed", "skipped"} for tc in tool_calls):
            signals.append(("tool_failure", 0.9, "tool_status_failed"))
        if scores["retrieval"] is not None and scores["retrieval"] < 0.5:
            signals.append(("retrieval_failure", 0.85, "low_retrieval_score"))
        if (scores["correctness"] is not None and scores["correctness"] < 0.4
                and retrieval_events):
            signals.append(("hallucination", 0.8, "correctness_fail_with_retrieval"))
        if scores["format"] is not None and scores["format"] < 0.5:
            signals.append(("format_failure", 0.75, "low_format_score"))
        if scores["latency"] is not None and scores["latency"] == 0.0:
            signals.append(("latency_failure", 0.8, "latency_score_zero"))
        if scores["cost"] is not None and scores["cost"] == 0.0:
            signals.append(("cost_failure", 0.8, "cost_score_zero"))
        if prompt == self.PROMPT_V5 and overall < 0.7:
            signals.append(("prompt_regression", 0.85, "prompt_v5_low_score"))
        if scenario == "prompt_regression":
            signals.append(("prompt_regression", 0.9, "scenario_tag"))
        if (scores["retrieval"] is not None and scores["retrieval"] >= 0.5
                and (scores["sql"] is None or scores["sql"] >= 0.5)
                and (scores["tool"] is None or scores["tool"] >= 0.5)
                and scores["correctness"] is not None and scores["correctness"] < 0.4):
            signals.append(("reasoning_failure", 0.7, "good_components_wrong_answer"))

        if not signals:
            if overall >= 0.7:
                return ClassificationResult("unknown", [], 0.3, True)
            return ClassificationResult("unknown", ["ambiguous_signals"], 0.4, True)

        signals.sort(key=lambda x: x[1], reverse=True)
        primary, confidence, top_signal = signals[0]
        secondary = [s[2] for s in signals[1:]]
        if top_signal not in secondary:
            secondary = [top_signal] + secondary

        threshold = context.get("_confidence_threshold", 0.6)
        return ClassificationResult(
            primary_category=primary,
            secondary_signals=secondary[:5],
            confidence_score=confidence,
            requires_human_review=confidence < threshold,
        )
