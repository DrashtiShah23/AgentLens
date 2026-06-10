from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.schemas.evaluation_result import EvaluationResult
from app.api.schemas.failure_record import FailureRecord
from app.api.schemas.tool_call import ToolCall, ToolStatus
from observatory.ingestion.schema_validator import validate_record


def test_tool_status_enum_validation():
    tc = ToolCall.model_validate({
        "tool_call_id": "tc1", "run_id": "r1", "tool_name": "create_ticket",
        "tool_input": {"x": 1}, "tool_status": "success",
        "started_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "completed_at": datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc),
        "latency_ms": 100,
    })
    assert tc.tool_status == ToolStatus.SUCCESS


def test_evaluation_score_range():
    with pytest.raises(ValidationError):
        EvaluationResult.model_validate({
            "evaluation_id": "e1", "run_id": "r1", "overall_score": 1.5,
            "evaluated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        })


def test_structured_validation_errors():
    outcome = validate_record({"run_id": ""}, __import__(
        "app.api.schemas.agent_run", fromlist=["AgentRun"]).AgentRun)
    assert not outcome.valid
    assert outcome.rejection_reason
    assert len(outcome.errors) > 0


def test_failure_record_category_validation():
    with pytest.raises(ValidationError):
        FailureRecord.model_validate({
            "failure_id": "f1", "run_id": "r1", "primary_category": "bad_category",
            "confidence_score": 0.8, "severity": "high",
            "classified_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        })
