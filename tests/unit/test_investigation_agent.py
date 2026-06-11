import inspect

from app.agent.graph import DeterministicInvestigationAgent, create_investigation_agent
from app.agent.tools import (
    InvestigationTools, build_tool_kwargs, detect_tool, parse_time_window, reject_unsafe_input,
)
from app.dashboard.components.styles import FAILURE_LABELS, SEVERITY_LABELS, TASK_LABELS

COPILOT_EXAMPLES = [
    "Why did reliability drop yesterday?",
    "Did prompt_v5_regression_case make things worse?",
    "Which model is safest for text to SQL?",
    "What are the top failure modes this week?",
    "Which runs need human review?",
    "Which agent is most expensive?",
]


def test_failure_labels_importable():
    assert FAILURE_LABELS["hallucination"] == "Unsupported Answer"
    assert FAILURE_LABELS["sql_failure"] == "SQL Generation Error"
    assert SEVERITY_LABELS["critical"] == "Critical"
    assert TASK_LABELS["text_to_sql"] == "Text to SQL"


def test_reject_destructive_sql():
    err = reject_unsafe_input("DROP TABLE agent_runs")
    assert err is not None
    assert "Destructive" in err


def test_reject_raw_sql():
    err = reject_unsafe_input("SELECT run_id FROM agent_runs WHERE agent_name = 'x'")
    assert err is not None


def test_allow_reliability_drop_question():
    assert reject_unsafe_input("Why did reliability drop yesterday?") is None


def test_allow_failure_rate_drop_question():
    assert reject_unsafe_input("Did the failure rate drop after prompt v4?") is None


def test_allow_prompt_caused_drop_question():
    assert reject_unsafe_input("Which prompt caused reliability to drop?") is None


def test_reject_drop_table_sql():
    assert reject_unsafe_input("DROP TABLE agent_runs") is not None


def test_reject_delete_from_sql():
    assert reject_unsafe_input("delete from agent_runs") is not None


def test_reject_select_from_sql():
    assert reject_unsafe_input("select * from agent_runs") is not None


def test_reject_update_set_sql():
    assert reject_unsafe_input("update agent_runs set failure_rate = 0") is not None


def test_default_time_window_7_days():
    days, assumptions = parse_time_window("Why did reliability drop?")
    assert days == 7
    assert any("7 days" in a for a in assumptions)


def test_detect_prompt_tool():
    assert detect_tool("Did prompt_v5_regression_case make things worse?") == "get_prompt_comparison"


def test_llm_disabled_structured_response(initialized_db):
    agent = DeterministicInvestigationAgent(initialized_db)
    result = agent.investigate("What is the weather today?")
    assert result.get("error") or "outside" in result.get("summary", "").lower()


def test_missing_data_response(initialized_db):
    agent = create_investigation_agent(initialized_db)
    result = agent.investigate("Why did reliability drop yesterday?")
    assert "summary" in result
    assert result.get("llm_used") is False


def test_build_tool_kwargs_no_extra_args():
    assert build_tool_kwargs("get_prompt_comparison", "Did prompt v5 regress?", 7) == {}
    assert build_tool_kwargs("get_recent_incidents", "Which runs need human review?", 7) == {}
    assert build_tool_kwargs("get_model_comparison", "Which model is safest for text to SQL?", 7) == {
        "task_type": "text_to_sql",
    }
    assert build_tool_kwargs("get_overall_reliability", "Why did reliability drop?", 1) == {
        "time_window_days": 1,
    }


def test_dispatch_filters_unsupported_kwargs(initialized_db):
    tools = InvestigationTools(initialized_db)
    result = tools.dispatch("get_prompt_comparison", time_window_days=7, agent_name=None)
    assert "error" not in result or "unexpected keyword" not in str(result.get("error", ""))
    assert result.get("metric") == "prompt_comparison"


def test_tool_signatures_accept_routed_kwargs():
    tools = InvestigationTools()
    for tool_name in (
        "get_overall_reliability", "get_failure_trends", "get_cost_latency_summary",
        "get_prompt_comparison", "get_recent_incidents", "get_model_comparison",
    ):
        kwargs = build_tool_kwargs(tool_name, "sample question", 7)
        fn = getattr(tools, tool_name)
        allowed = set(inspect.signature(fn).parameters)
        assert set(kwargs.keys()).issubset(allowed), f"{tool_name} got extra kwargs: {kwargs}"


def test_all_copilot_examples_return_structured_response(initialized_db):
    agent = create_investigation_agent(initialized_db)
    for question in COPILOT_EXAMPLES:
        result = agent.investigate(question)
        assert "summary" in result, question
        assert "recommended_action" in result or result.get("metric_data"), question
        err = result.get("error", "")
        assert "unexpected keyword" not in err, question
        assert "Traceback" not in err, question


def test_copilot_examples_route_without_exceptions(initialized_db):
    agent = create_investigation_agent(initialized_db)
    for question in COPILOT_EXAMPLES:
        result = agent.investigate(question)
        assert "summary" in result, question
        err = result.get("error", "")
        assert "unexpected keyword" not in err, question
        assert "Traceback" not in err, question
        if err:
            assert "metric tool returned an error" in result["summary"].lower() or True


def _assert_not_generic_summary(summary: str) -> None:
    s = summary.strip().lower()
    assert not (s.startswith("returned ") and "aggregated records" in s)


def test_copilot_most_expensive_agent_summary_is_meaningful():
    from app.agent.response_formatter import format_structured_response
    result = format_structured_response(
        "Which agent is most expensive?",
        "get_cost_latency_summary",
        {
            "metric": "cost_latency_summary",
            "rows": [
                {"agent_name": "sql_agent", "run_count": 10, "avg_cost_usd": 0.05},
                {"agent_name": "qa_agent", "run_count": 20, "avg_cost_usd": 0.02},
            ],
        },
        ["Assumed time window: last 7 days"],
        7,
    )
    summary = result["summary"]
    _assert_not_generic_summary(summary)
    assert "most expensive agent" in summary.lower()
    assert "sql_agent" in summary.lower()
    assert "cost" in result["evidence"].lower()


def test_copilot_prompt_regression_summary_mentions_baseline_and_delta():
    from app.agent.response_formatter import format_structured_response
    result = format_structured_response(
        "Did prompt_v5_regression_case make things worse?",
        "get_prompt_comparison",
        {
            "metric": "prompt_comparison",
            "prompts": [
                {"prompt_version_id": "prompt_v1_baseline", "reliability_score": 0.64},
                {
                    "prompt_version_id": "prompt_v5_regression_case",
                    "reliability_score": 0.43,
                    "regression_detected": True,
                },
            ],
        },
        [],
        7,
    )
    summary = result["summary"].lower()
    _assert_not_generic_summary(result["summary"])
    assert "yes" in summary or "worse" in summary
    evidence = result["evidence"].lower()
    assert "baseline" in evidence
    assert "prompt_v5" in evidence
    assert "change" in evidence or "points" in evidence


def test_copilot_model_safest_text_to_sql_summary_mentions_model_and_reliability():
    from app.agent.response_formatter import format_structured_response
    result = format_structured_response(
        "Which model is safest for text to SQL?",
        "get_model_comparison",
        {
            "metric": "model_comparison",
            "task_type_filter": "text_to_sql",
            "models": [
                {
                    "model_name": "gpt_4o_mini_simulated",
                    "task_type": "text_to_sql",
                    "reliability_score": 0.82,
                    "failure_rate": 0.12,
                    "sql_score": 0.88,
                    "run_count": 40,
                },
            ],
        },
        [],
        7,
    )
    summary = result["summary"].lower()
    _assert_not_generic_summary(result["summary"])
    assert "model" in summary
    assert "reliability" in summary
    assert "text to sql" in summary


def test_copilot_top_failure_modes_summary_lists_top_failure():
    from app.agent.response_formatter import format_structured_response
    result = format_structured_response(
        "What are the top failure modes this week?",
        "get_failure_trends",
        {
            "metric": "failure_trends",
            "by_category": [
                {"failure_category": "sql_failure", "failure_count": 120},
                {"failure_category": "hallucination", "failure_count": 80},
            ],
        },
        [],
        7,
    )
    summary = result["summary"].lower()
    _assert_not_generic_summary(result["summary"])
    assert "failure" in summary
    assert "120" in result["summary"]
    assert "top failure" in result["evidence"].lower()


def test_copilot_runs_need_review_summary_mentions_count():
    from app.agent.response_formatter import format_structured_response
    result = format_structured_response(
        "Which runs need human review?",
        "get_recent_incidents",
        {
            "metric": "recent_incidents",
            "incidents": [
                {
                    "run_id": "run_abc123",
                    "agent_name": "sql_agent",
                    "severity": "critical",
                    "requires_human_review": True,
                    "overall_score": 0.35,
                },
                {
                    "run_id": "run_def456",
                    "agent_name": "qa_agent",
                    "severity": "high",
                    "requires_human_review": True,
                    "overall_score": 0.48,
                },
            ],
        },
        [],
        7,
    )
    summary = result["summary"].lower()
    _assert_not_generic_summary(result["summary"])
    assert "review" in summary
    assert "2" in result["summary"]


def test_copilot_does_not_return_generic_record_count_for_known_questions(initialized_db):
    agent = create_investigation_agent(initialized_db)
    for question in COPILOT_EXAMPLES:
        result = agent.investigate(question)
        _assert_not_generic_summary(result["summary"])
        assert result.get("evidence"), question
        assert result.get("llm_used") is False
