"""Dashboard display accuracy and formatting tests."""

import inspect
import pandas as pd
import pytest

from app.dashboard.components.display_helpers import (
    FAILURE_CHART_PALETTE,
    SCORE_DISCLAIMER,
    V5_REGRESSION_NOTE,
    compute_weighted_failure_rate,
    format_change_points,
    format_percentage_point_delta,
    friendly_model_name,
    friendly_prompt_name,
    friendly_task_name,
    palette_has_green,
    regression_hover_text,
    risk_color_for_failure_rate,
)
from app.dashboard.components.layout import format_not_applicable, format_run_list, format_score
from app.dashboard.components.metrics_validation import normalize_rate, validate_rates_in_df
from app.dashboard.components.styles import TASK_LABELS
from app.dashboard.data_helpers import failure_trends_stacked, model_failure_rates_by_model, ranked_models
from app.dashboard.views.view_runs import RUN_SCORE_LABELS


def test_model_failure_rate_uses_failed_runs_over_total_runs(initialized_db):
    from app.services.warehouse_reader import WarehouseReader

    reader = WarehouseReader(initialized_db)
    mfr = model_failure_rates_by_model(reader)
    if mfr.empty:
        pytest.skip("no model data")
    assert "failed_run_count" in mfr.columns or "run_count" in mfr.columns
    for _, row in mfr.iterrows():
        if row.get("run_count", 0) > 0:
            expected = row.get("failed_run_count", row["failure_rate"] * row["run_count"]) / row["run_count"]
            assert abs(normalize_rate(row["failure_rate"]) - normalize_rate(expected)) < 0.001


def test_model_failure_rate_never_exceeds_one(initialized_db):
    from app.services.warehouse_reader import WarehouseReader

    reader = WarehouseReader(initialized_db)
    mfr = model_failure_rates_by_model(reader)
    if mfr.empty:
        pytest.skip("no model data")
    assert mfr["failure_rate"].max() <= 1.0
    for val in mfr["failure_rate"].dropna():
        assert 0 <= normalize_rate(val) <= 1


def test_failure_charts_do_not_use_green_palette():
    assert not palette_has_green(FAILURE_CHART_PALETTE)
    assert risk_color_for_failure_rate(0.05) != "#22c55e"
    assert risk_color_for_failure_rate(0.60) == "#ef4444"


def test_format_change_points_plain_english():
    assert format_change_points(0.008) == "0.8 points higher"
    assert format_change_points(-0.004) == "0.4 points lower"
    assert format_change_points(-0.206) == "20.6 points lower"
    assert format_change_points(0.0) == "No change"
    assert format_change_points(None) == "No change"


def test_regression_chart_does_not_use_pp_abbreviation():
    assert "pp" not in format_change_points(0.008).lower()
    assert "pp" not in format_percentage_point_delta(-0.206).lower()
    import app.dashboard.components.charts as charts

    src = inspect.getsource(charts.diverging_bar)
    assert " pp" not in src
    assert "format_change_points" in src


def test_no_standalone_plus_or_p_labels():
    for val in (0.008, -0.206, 0.0, -0.004):
        label = format_change_points(val)
        assert label != "+"
        assert label != "p"
        assert not label.startswith("+")


def test_friendly_prompt_names_used():
    assert friendly_prompt_name("prompt_v5_regression_case") == "Prompt v5 regression case"
    assert friendly_prompt_name("gpt_4o_mini_simulated") != "gpt_4o_mini_simulated"
    assert friendly_model_name("gpt_4o_mini_simulated") == "GPT 4o mini simulated"
    import app.dashboard.views.view_prompts as vp

    assert "friendly_prompt_name" in inspect.getsource(vp.render)


def test_top_failure_chart_has_right_margin():
    import app.dashboard.components.charts as charts

    src = inspect.getsource(charts.failure_ranking_chart)
    assert "_right_margin_for_values" in src or "r=right" in src
    assert "range=[0, pad]" in src or "1.18" in src


def test_regression_hover_text_plain_english():
    hover = regression_hover_text(0.432, 0.638, -0.206, "prompt_v5_regression_case")
    assert "63.8%" in hover
    assert "43.2%" in hover
    assert "drop of 20.6 points" in hover
    assert "pp" not in hover


def test_prompt_v5_regression_explanation_present():
    import app.dashboard.views.view_prompts as vp

    src = inspect.getsource(vp.render)
    assert "V5_REGRESSION_NOTE" in src or "synthetic bad prompt" in src
    assert "production" in V5_REGRESSION_NOTE.lower()


def test_task_labels_use_context_qa_not_retrieval_qa():
    assert TASK_LABELS["retrieval_qa"] == "Context QA"
    assert friendly_task_name("retrieval_qa") == "Context QA"
    assert "Retrieval QA" not in TASK_LABELS["retrieval_qa"]


def test_score_disclaimer_present_on_key_pages():
    import app.dashboard.views.view_models as vm
    import app.dashboard.views.view_overview as vo
    import app.dashboard.views.view_prompts as vp

    for mod in (vo, vm, vp):
        assert "score_disclaimer" in inspect.getsource(mod.render)
    assert "synthetic demo agent runs" in SCORE_DISCLAIMER
    assert "production benchmarks" in SCORE_DISCLAIMER


def test_best_model_by_task_section_exists():
    import app.dashboard.views.view_models as vm
    src = inspect.getsource(vm.render)
    assert "Best Model by Task" in src
    assert "best_model_by_task" in src


def test_best_model_by_task_uses_friendly_task_labels():
    from app.dashboard.data_helpers import best_model_by_task
    from app.dashboard.components.display_helpers import friendly_task_name, VALID_TASK_RISK_LABELS

    assert friendly_task_name("retrieval_qa") == "Context QA"
    assert "Healthy" in VALID_TASK_RISK_LABELS


def test_best_model_by_task_risk_labels_are_valid():
    from app.dashboard.components.display_helpers import task_risk_label, VALID_TASK_RISK_LABELS
    assert task_risk_label(0.85)[0] == "Healthy"
    assert task_risk_label(0.70)[0] == "Warning"
    assert task_risk_label(0.40)[0] == "Risky"
    for label, _ in [task_risk_label(0.9), task_risk_label(0.7), task_risk_label(0.5)]:
        assert label in VALID_TASK_RISK_LABELS


def test_heatmap_is_advanced_not_primary_recommendation():
    import app.dashboard.views.view_models as vm
    src = inspect.getsource(vm.render)
    assert "Advanced: Model by task heatmap" in src
    assert src.index("Best Model by Task") < src.index("Advanced: Model by task heatmap")


def test_default_run_selection_prioritizes_critical():
    from app.dashboard.components.run_selection import select_default_run_id
    df = pd.DataFrame([
        {"run_id": "run_healthy", "overall_score": 1.0, "severity": None, "failure_category": None, "success_flag": True},
        {"run_id": "run_critical", "overall_score": 0.42, "severity": "critical", "failure_category": "sql_failure", "success_flag": True},
        {"run_id": "run_low", "overall_score": 0.55, "severity": "medium", "failure_category": None, "success_flag": True},
    ])
    run_id, reason = select_default_run_id(df, "All runs")
    assert run_id == "run_critical"
    assert reason == "Critical severity"


def test_filter_updates_selected_run():
    from app.dashboard.components.run_selection import select_default_run_id
    failed = pd.DataFrame([
        {"run_id": "run_fail_1", "overall_score": 0.0, "severity": "high", "failure_category": "tool_failure", "success_flag": False},
        {"run_id": "run_fail_2", "overall_score": 0.2, "severity": "critical", "failure_category": "sql_failure", "success_flag": False},
    ])
    run_id, reason = select_default_run_id(failed, "Failed only")
    assert run_id == "run_fail_1"
    assert reason == "Runtime failed"

    sql = pd.DataFrame([
        {"run_id": "run_sql", "overall_score": 0.4, "severity": "high", "failure_category": "sql_failure", "success_flag": True},
    ])
    run_id, reason = select_default_run_id(sql, "SQL generation errors")
    assert run_id == "run_sql"
    assert reason == "SQL Generation Error"


def test_failure_details_success_state_for_healthy_run():
    from app.dashboard.components.run_selection import failure_details_success_message
    msg = failure_details_success_message()
    assert "passed all applicable reliability checks" in msg


def test_failure_details_shows_failure_fields_for_failed_run():
    from app.dashboard.components.run_selection import (
        failure_review_why_text, failure_root_cause_text,
    )
    fail = {
        "primary_category": "sql_failure",
        "severity": "critical",
        "recommendation": "Add SQL linting before execution.",
        "confidence_score": 0.91,
        "requires_human_review": True,
        "secondary_signals": {"syntax_error": True},
    }
    assert "SQL Generation Error" in failure_root_cause_text(fail)
    why = failure_review_why_text(fail, 0.35)
    assert "human review" in why.lower()
    assert "critical" in why.lower()


def test_selected_reason_is_present():
    from app.dashboard.components.run_selection import reason_for_row
    import app.dashboard.views.view_runs as vr
    row = {
        "run_id": "run_x",
        "overall_score": 0.41,
        "severity": "critical",
        "failure_category": "hallucination",
        "success_flag": True,
        "prompt_version_id": "prompt_v1_baseline",
    }
    assert reason_for_row(row, "All runs") == "Critical severity"
    assert "Selected because" in inspect.getsource(vr.render)


def test_run_review_disclaimer_not_duplicated():
    import app.dashboard.views.view_runs as vr
    src = inspect.getsource(vr.render)
    assert "score_disclaimer" not in src
    assert src.count("synthetic demo agent runs") == 0


def test_execution_status_and_reliability_status_are_separate():
    from app.dashboard.components.display_helpers import execution_status_label, reliability_status_label
    assert execution_status_label(True)[0] == "Completed"
    assert execution_status_label(False)[0] == "Runtime Failed"
    assert reliability_status_label(0.85, None, None)[0] == "Reliable"
    assert reliability_status_label(0.65, "sql_failure", "medium")[0] == "Needs Review"


def test_reliability_status_handles_nan_severity():
    from app.dashboard.components.display_helpers import reliability_status_label
    import math
    label, _ = reliability_status_label(0.85, None, float("nan"))
    assert label == "Reliable"


def test_reliability_status_handles_float_severity():
    from app.dashboard.components.display_helpers import reliability_status_label
    label, _ = reliability_status_label(0.85, None, 1.5)
    assert label == "Reliable"
    label2, _ = reliability_status_label(0.40, None, float("nan"))
    assert label2 == "Critical"


def test_run_review_page_does_not_crash_with_missing_severity():
    from app.dashboard.components.badges import reliability_status_badge, severity_badge
    df = pd.DataFrame({
        "run_id": ["run_a", "run_b"],
        "agent_name": ["agent1", "agent2"],
        "overall_score": [0.72, float("nan")],
        "success_flag": [True, True],
        "failure_category": [None, "sql_failure"],
        "severity": [None, 2.0],
    })
    out = format_run_list(df)
    assert len(out) == 2
    reliability_status_badge(0.72, None, None)
    reliability_status_badge(0.72, None, float("nan"))
    reliability_status_badge(0.72, None, 2.0)
    severity_badge(None)
    severity_badge(float("nan"))
    severity_badge(2.0)


def test_missing_severity_displays_not_applicable():
    from app.dashboard.components.layout import friendly_severity
    from app.dashboard.components.badges import severity_badge
    assert friendly_severity(None) == "Not applicable"
    assert friendly_severity(float("nan")) == "Not applicable"
    assert "Not Applicable" in severity_badge(None)
    df = pd.DataFrame({
        "run_id": ["run_x"],
        "agent_name": ["a"],
        "overall_score": [0.80],
        "success_flag": [True],
        "failure_category": [None],
        "severity": [None],
    })
    out = format_run_list(df)
    assert out.iloc[0]["Severity"] == "Not applicable"


def test_low_reliability_completed_run_shows_needs_review_or_critical():
    from app.dashboard.components.display_helpers import reliability_status_label
    label, _ = reliability_status_label(0.45, None, None)
    assert label == "Critical"
    label2, _ = reliability_status_label(0.55, None, None)
    assert label2 == "Needs Review"
    df = pd.DataFrame({
        "run_id": ["run_x"],
        "agent_name": ["a"],
        "overall_score": [0.55],
        "success_flag": [True],
        "failure_category": [None],
        "severity": [None],
    })
    out = format_run_list(df)
    assert out.iloc[0]["Execution Status"] == "Completed"
    assert out.iloc[0]["Reliability Status"] in ("Needs Review", "Critical")


def test_model_page_has_aggregate_score_explanation():
    import app.dashboard.views.view_models as vm
    src = inspect.getsource(vm.render)
    assert "Aggregate model scores" in src or "aggregate scores across many synthetic" in src


def test_run_page_has_selected_run_explanation():
    import app.dashboard.views.view_runs as vr
    src = inspect.getsource(vr.render)
    assert "individual agent runs" in src.lower()
    assert "Model Trust Leaderboard" in src


def test_failure_rates_between_zero_and_one_for_dashboard(initialized_db):
    from app.services.metric_service import MetricService
    from app.services.warehouse_reader import WarehouseReader

    reader = WarehouseReader(initialized_db)
    metrics = MetricService(reader, initialized_db)
    overview = metrics.overview_metrics(30)
    fr = normalize_rate(overview.get("failure_rate"))
    assert fr is None or 0 <= fr <= 1

    models = ranked_models(reader)
    if not models.empty:
        for val in models["failure_rate"].dropna():
            assert 0 <= normalize_rate(val) <= 1


def test_compute_weighted_failure_rate():
    rates = pd.Series([0.2, 0.4])
    counts = pd.Series([10, 30])
    assert abs(compute_weighted_failure_rate(rates, counts) - 0.35) < 0.001


def test_failure_trend_handles_single_day_data(initialized_db):
    from app.services.warehouse_reader import WarehouseReader

    reader = WarehouseReader(initialized_db)
    df = failure_trends_stacked(reader, 90)
    if df.empty:
        pytest.skip("no failure trend data")
    assert "failure_date" in df.columns
    dates = pd.to_datetime(df["failure_date"], errors="coerce").dropna()
    assert len(dates) >= 1
    assert dates.dt.hour.max() == 0


def test_score_display_labels_are_human_readable():
    assert RUN_SCORE_LABELS["retrieval_score"] == "This Run Context Lookup Score"
    assert RUN_SCORE_LABELS["overall_score"] == "This Run Reliability Score"
    assert "Context Lookup" in RUN_SCORE_LABELS["retrieval_score"]


def test_not_applicable_display_not_truncated():
    assert format_score(None) == "Not applicable"
    assert format_not_applicable(None) == "Not applicable"
    assert "Unav" not in format_score(None)


def test_format_run_list_uses_passed_failed():
    df = pd.DataFrame({
        "run_id": ["run_abc123"],
        "agent_name": ["agent_a"],
        "overall_score": [0.85],
        "success_flag": [True],
        "failure_category": ["hallucination"],
        "severity": ["high"],
    })
    out = format_run_list(df)
    assert out.iloc[0]["Execution Status"] == "Completed"
    assert out.iloc[0]["Reliability Status"] == "Needs Review"
    assert "Unsupported Answer" in str(out.iloc[0]["Failure Type"])


def test_validate_rates_clips_display_values():
    df = pd.DataFrame({"failure_rate": [1.5, 0.2, 50.0, 150.0]})
    out = validate_rates_in_df(df, ["failure_rate"])
    assert out.iloc[0]["failure_rate"] == 1.0
    assert out.iloc[1]["failure_rate"] == 0.2
    assert out.iloc[2]["failure_rate"] == 0.5
    assert out.iloc[3]["failure_rate"] == 1.0
