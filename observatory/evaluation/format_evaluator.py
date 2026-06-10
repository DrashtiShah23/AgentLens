"""Deterministic format evaluator."""

import json
from typing import Any

from observatory.evaluation.base_evaluator import BaseEvaluator, EvaluatorResult


class FormatEvaluator(BaseEvaluator):
    name = "format"

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        answer = context.get("final_answer", "")
        task = context.get("task_type", "")
        checks: list[str] = []
        total = 3
        passed = 0

        if not str(answer).strip():
            return EvaluatorResult(score=0.0, checks_failed=["non_empty_answer"])
        checks.append("non_empty_answer")
        passed += 1

        if task == "classification":
            try:
                parsed = json.loads(answer)
                checks.append("valid_json")
                passed += 1
                if isinstance(parsed, dict) and "label" in parsed:
                    checks.append("required_fields")
                    passed += 1
                else:
                    return EvaluatorResult(score=passed / total, checks_passed=checks,
                                           checks_failed=["required_fields"])
            except json.JSONDecodeError:
                return EvaluatorResult(score=passed / total, checks_passed=checks,
                                       checks_failed=["valid_json"])
        else:
            passed += 2
            checks.extend(["valid_json_skipped", "required_fields_skipped"])

        return EvaluatorResult(score=1.0, checks_passed=checks)
