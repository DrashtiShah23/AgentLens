from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.schemas.agent_run import AgentRun, TaskType


def _valid_run(**overrides) -> dict:
    base = {
        "run_id": "run_001",
        "agent_name": "sql_analyst_agent",
        "task_type": "text_to_sql",
        "user_query": "What is revenue?",
        "prompt_version_id": "prompt_v1_baseline",
        "model_name": "gpt_4o_mini_simulated",
        "started_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "completed_at": datetime(2024, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
        "latency_ms": 2000,
        "input_tokens": 100,
        "output_tokens": 50,
        "estimated_cost_usd": 0.0002,
        "final_answer": "125000",
        "success_flag": True,
    }
    base.update(overrides)
    return base


def test_valid_agent_run():
    run = AgentRun.model_validate(_valid_run())
    assert run.task_type == TaskType.TEXT_TO_SQL
    assert run.duration_seconds == 2.0
    assert run.total_tokens == 150


def test_completed_at_before_started_at_rejected():
    with pytest.raises(ValidationError) as exc:
        AgentRun.model_validate(_valid_run(
            completed_at=datetime(2023, 12, 31, tzinfo=timezone.utc),
        ))
    assert "completed_at" in str(exc.value)


def test_negative_latency_rejected():
    with pytest.raises(ValidationError):
        AgentRun.model_validate(_valid_run(latency_ms=-1))


def test_string_latency_coerced():
    run = AgentRun.model_validate(_valid_run(latency_ms="1500"))
    assert run.latency_ms == 1500


def test_invalid_task_type_rejected():
    with pytest.raises(ValidationError):
        AgentRun.model_validate(_valid_run(task_type="invalid_task"))
