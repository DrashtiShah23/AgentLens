"""Deterministic tool call evaluator."""

from typing import Any, Optional

from observatory.config.settings import Settings, get_settings
from observatory.evaluation.base_evaluator import BaseEvaluator, EvaluatorResult

EXPECTED_TOOLS = {
    "tool_use": "create_ticket",
    "tool_router_agent": "create_ticket",
}


class ToolCallEvaluator(BaseEvaluator):
    name = "tool"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        task_type = context.get("task_type", "")
        tool_calls = context.get("tool_calls", [])
        if task_type != "tool_use" and not tool_calls:
            return EvaluatorResult(score=None, notes="not a tool_use run")

        checks = []
        total = 5
        passed = 0

        if not tool_calls:
            return EvaluatorResult(score=0.0, checks_failed=["tool_called"],
                                   notes="no tool calls found")

        checks.append("tool_called")
        passed += 1
        tc = tool_calls[0]
        expected_tool = EXPECTED_TOOLS.get("tool_use", "create_ticket")
        if tc.get("tool_name") == expected_tool:
            checks.append("correct_tool")
            passed += 1
        else:
            return EvaluatorResult(score=passed / total, checks_passed=checks,
                                   checks_failed=["correct_tool"])

        tool_input = tc.get("tool_input", {})
        if isinstance(tool_input, dict) and tool_input:
            checks.append("input_schema")
            passed += 1
        else:
            return EvaluatorResult(score=passed / total, checks_passed=checks,
                                   checks_failed=["input_schema"])

        if tc.get("tool_status") == "success":
            checks.append("status_success")
            passed += 1
        else:
            return EvaluatorResult(score=passed / total, checks_passed=checks,
                                   checks_failed=["status_success"])

        if tc.get("tool_output"):
            checks.append("output_nonempty")
            passed += 1
        else:
            return EvaluatorResult(score=passed / total, checks_passed=checks,
                                   checks_failed=["output_nonempty"])

        return EvaluatorResult(score=1.0, checks_passed=checks)
