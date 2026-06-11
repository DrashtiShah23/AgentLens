#!/usr/bin/env python3
"""Dashboard quality checks — imports, rates, colors, copilot examples."""

from __future__ import annotations

import importlib
import inspect
import sys

import pandas as pd

VIEWS = [
    "app.dashboard.views.view_overview",
    "app.dashboard.views.view_failures",
    "app.dashboard.views.view_prompts",
    "app.dashboard.views.view_models",
    "app.dashboard.views.view_runs",
    "app.dashboard.views.view_investigation",
]

COMPONENTS = [
    "app.dashboard.components.charts",
    "app.dashboard.components.layout",
    "app.dashboard.components.display_helpers",
    "app.dashboard.components.score_explainer",
    "app.dashboard.components.metrics_validation",
]

COPILOT_EXAMPLES = [
    "Why did reliability drop yesterday?",
    "Did prompt_v5_regression_case make things worse?",
    "Which model is safest for text to SQL?",
    "What are the top failure modes this week?",
    "Which runs need human review?",
    "Which agent is most expensive?",
]


def main() -> int:
    try:
        for path in VIEWS + COMPONENTS:
            mod = importlib.import_module(path)
            if path in VIEWS:
                assert hasattr(mod, "render"), f"{path} missing render()"

        from app.dashboard.components.display_helpers import (
            FAILURE_CHART_PALETTE,
            SCORE_DISCLAIMER,
            V5_REGRESSION_NOTE,
            format_change_points,
            friendly_prompt_name,
            friendly_task_name,
            palette_has_green,
        )
        from app.dashboard.components import charts as charts_mod
        from app.dashboard.components.metrics_validation import normalize_rate
        from app.dashboard.components.styles import TASK_LABELS
        from app.dashboard.data_helpers import model_failure_rates_by_model, ranked_models
        from app.agent.graph import create_investigation_agent
        from app.services.metric_service import MetricService
        from app.services.warehouse_reader import WarehouseReader
        from observatory.config.settings import get_settings

        if palette_has_green(FAILURE_CHART_PALETTE):
            print("FAIL: failure chart palette contains green")
            return 1

        if TASK_LABELS.get("retrieval_qa") != "Context QA":
            print("FAIL: retrieval_qa should map to Context QA")
            return 1

        if "pp" in format_change_points(0.008).lower():
            print("FAIL: regression delta still uses pp abbreviation")
            return 1
        if format_change_points(0.008) != "0.8 points higher":
            print("FAIL: format_change_points plain English incorrect")
            return 1
        if friendly_prompt_name("prompt_v5_regression_case") != "Prompt v5 regression case":
            print("FAIL: friendly_prompt_name mapping incorrect")
            return 1
        div_src = inspect.getsource(charts_mod.diverging_bar)
        if " pp" in div_src or "tickformat=\".1%\"" in div_src:
            print("FAIL: diverging_bar still uses pp or percent tickformat")
            return 1
        if "format_change_points" not in div_src:
            print("FAIL: diverging_bar should use format_change_points")
            return 1
        fail_src = inspect.getsource(charts_mod.failure_ranking_chart)
        if fail_src.count("r=right") < 1 and "_right_margin_for_values" not in fail_src:
            print("FAIL: failure ranking chart missing right margin logic")
            return 1

        if "synthetic" not in V5_REGRESSION_NOTE.lower():
            print("FAIL: missing v5 regression explanation")
            return 1

        for path in ("view_overview", "view_models", "view_prompts"):
            mod = importlib.import_module(f"app.dashboard.views.{path}")
            if "score_disclaimer" not in inspect.getsource(mod.render):
                print(f"FAIL: score_disclaimer missing on {path}")
                return 1
        vm = importlib.import_module("app.dashboard.views.view_models")
        vm_src = inspect.getsource(vm.render)
        if "Best Model by Task" not in vm_src:
            print("FAIL: Best Model by Task section missing")
            return 1
        if vm_src.index("Best Model by Task") > vm_src.index("Advanced: Model by task heatmap"):
            print("FAIL: heatmap should be advanced, not primary")
            return 1
        vr = importlib.import_module("app.dashboard.views.view_runs")
        vr_src = inspect.getsource(vr.render)
        if "score_disclaimer" in vr_src:
            print("FAIL: Run Review duplicates synthetic disclaimer")
            return 1
        if "execution_status" not in inspect.getsource(__import__("app.dashboard.components.layout", fromlist=["layout"]).format_run_list):
            print("FAIL: Run Review missing execution status separation")
            return 1
        from app.dashboard.components.run_selection import select_default_run_id
        import pandas as pd
        sample = pd.DataFrame([
            {"run_id": "run_ok", "overall_score": 1.0, "severity": None, "failure_category": None, "success_flag": True},
            {"run_id": "run_bad", "overall_score": 0.3, "severity": "critical", "failure_category": "sql_failure", "success_flag": True},
        ])
        picked, reason = select_default_run_id(sample, "All runs")
        if picked != "run_bad" or reason != "Critical severity":
            print("FAIL: Run Review default selection should prioritize critical runs")
            return 1
        vr_src = inspect.getsource(vr.render)
        if "run_selection" not in vr_src or "Selected because" not in vr_src:
            print("FAIL: Run Review missing prioritized selection behavior")
            return 1
        from app.dashboard.components.display_helpers import VALID_TASK_RISK_LABELS, task_risk_label
        if task_risk_label(0.5)[0] not in VALID_TASK_RISK_LABELS:
            print("FAIL: invalid task risk label")
            return 1
        if "production benchmarks" not in SCORE_DISCLAIMER:
            print("FAIL: score disclaimer text incomplete")
            return 1

        settings = get_settings()
        reader = WarehouseReader(settings)
        MetricService(reader, settings)

        mfr = model_failure_rates_by_model(reader)
        if not mfr.empty:
            mx = mfr["failure_rate"].max()
            if pd.notna(mx) and normalize_rate(mx) > 1:
                print(f"FAIL: model failure_rate exceeds 100%: {mx}")
                return 1

        overview = MetricService(reader, settings).overview_metrics(30)
        fr = normalize_rate(overview.get("failure_rate"))
        if fr is not None and not (0 <= fr <= 1):
            print(f"FAIL: overview failure_rate out of range: {fr}")
            return 1

        agent = create_investigation_agent(settings)
        for q in COPILOT_EXAMPLES:
            result = agent.investigate(q)
            if "summary" not in result:
                print(f"FAIL: no summary for: {q}")
                return 1
            summary = str(result.get("summary", "")).strip().lower()
            if summary.startswith("returned ") and "aggregated records" in summary:
                print(f"FAIL: generic copilot summary for: {q}")
                return 1
            if not result.get("evidence"):
                print(f"FAIL: copilot missing evidence for: {q}")
                return 1
            err = str(result.get("error", ""))
            if "unexpected keyword" in err or "Traceback" in err:
                print(f"FAIL: copilot error for '{q}': {err}")
                return 1

        from app.dashboard.components.display_helpers import reliability_status_label, safe_lower
        reliability_status_label(0.8, None, float("nan"))
        reliability_status_label(0.8, None, 2.0)
        if safe_lower(2.0) != "2.0":
            print("FAIL: safe_lower should stringify numeric severity")
            return 1

        print("PASS")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
