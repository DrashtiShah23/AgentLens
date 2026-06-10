"""Deterministic correctness evaluator."""

import re
from typing import Any, Optional

from observatory.evaluation.base_evaluator import BaseEvaluator, EvaluatorResult

NUMERIC_TOLERANCE = 0.01


class CorrectnessEvaluator(BaseEvaluator):
    name = "correctness"

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        final_answer = context.get("final_answer", "")
        expected = context.get("expected_answer")
        if expected is None or (isinstance(expected, str) and not expected.strip()):
            return EvaluatorResult(score=None, notes="expected_answer missing; excluded from overall")

        expected_str = str(expected).strip()
        answer_str = str(final_answer).strip()

        if self._is_numeric(expected_str) and self._is_numeric(answer_str):
            exp_val, ans_val = float(expected_str), float(answer_str)
            if abs(exp_val - ans_val) <= NUMERIC_TOLERANCE:
                return EvaluatorResult(score=1.0, checks_passed=["numeric_match"])
            diff = abs(exp_val - ans_val) / max(abs(exp_val), 1.0)
            score = max(0.0, 1.0 - min(diff, 1.0))
            return EvaluatorResult(score=score, checks_failed=["numeric_mismatch"],
                                   notes=f"expected {exp_val}, got {ans_val}")

        score = self._keyword_overlap(answer_str, expected_str)
        passed = ["keyword_overlap"] if score >= 0.5 else []
        failed = [] if score >= 0.5 else ["keyword_overlap"]
        return EvaluatorResult(score=score, checks_passed=passed, checks_failed=failed)

    def _is_numeric(self, value: str) -> bool:
        try:
            float(value.replace(",", ""))
            return True
        except ValueError:
            return False

    def _keyword_overlap(self, answer: str, expected: str) -> float:
        def tokens(text: str) -> set[str]:
            return {t.lower() for t in re.findall(r"\w+", text) if len(t) > 2}

        exp_tokens = tokens(expected)
        if not exp_tokens:
            return 1.0 if answer.lower() == expected.lower() else 0.0
        ans_tokens = tokens(answer)
        overlap = len(exp_tokens & ans_tokens)
        return overlap / len(exp_tokens)
