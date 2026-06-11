#!/usr/bin/env python3
"""Import dashboard modules and run copilot example questions (LLM disabled)."""

from __future__ import annotations

import importlib
import sys

MODULES = [
    "app.dashboard.views.view_overview",
    "app.dashboard.views.view_failures",
    "app.dashboard.views.view_prompts",
    "app.dashboard.views.view_models",
    "app.dashboard.views.view_runs",
    "app.dashboard.views.view_investigation",
]

EXAMPLES = [
    "Why did reliability drop yesterday?",
    "Did prompt_v5_regression_case make things worse?",
    "Which model is safest for text to SQL?",
    "What are the top failure modes this week?",
    "Which runs need human review?",
    "Which agent is most expensive?",
]


def main() -> int:
    try:
        from app.agent.graph import create_investigation_agent
        from app.services.metric_service import MetricService
        from app.services.warehouse_reader import WarehouseReader
        from observatory.config.settings import get_settings

        for path in MODULES:
            mod = importlib.import_module(path)
            assert hasattr(mod, "render"), f"{path} missing render()"

        settings = get_settings()
        reader = WarehouseReader(settings)
        MetricService(reader, settings)

        agent = create_investigation_agent(settings)
        for q in EXAMPLES:
            result = agent.investigate(q)
            if "summary" not in result:
                print(f"FAIL: missing summary for: {q}")
                return 1
            err = result.get("error", "")
            if err and ("unexpected keyword" in err or "Traceback" in err):
                print(f"FAIL: tool error for '{q}': {err}")
                return 1
        print("PASS")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
