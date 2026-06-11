"""FastAPI request and response models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.api.schemas.agent_run import AgentRun


class HealthResponse(BaseModel):
    status: str
    warehouse_available: bool
    raw_log_dir_available: bool
    message: str


class OverviewMetricsResponse(BaseModel):
    time_window_days: int
    total_runs: int
    reliability_score: Optional[float] = None
    failure_rate: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    total_cost_usd: Optional[float] = None
    top_failure_category: Optional[str] = None
    top_affected_agent: Optional[str] = None
    top_affected_prompt: Optional[str] = None


class InvestigationRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)


class InvestigationResponse(BaseModel):
    question: str
    metric_name: Optional[str] = None
    time_window_days: Optional[int] = None
    assumptions: list[str] = Field(default_factory=list)
    summary: str
    metric_data: Optional[dict[str, Any]] = None
    recommended_action: Optional[str] = None
    llm_used: bool = False
    error: Optional[str] = None


class RunListResponse(BaseModel):
    runs: list[dict[str, Any]]
    count: int


class RunDetailResponse(BaseModel):
    run_id: str
    run: Optional[dict[str, Any]] = None
    evaluation: Optional[dict[str, Any]] = None
    failure: Optional[dict[str, Any]] = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_events: list[dict[str, Any]] = Field(default_factory=list)


class EvaluationListResponse(BaseModel):
    evaluations: list[dict[str, Any]]
    count: int


class TriggerEvaluationRequest(BaseModel):
    run_ids: list[str] = Field(default_factory=list)
    limit: Optional[int] = None


class TriggerEvaluationResponse(BaseModel):
    evaluated_count: int
    message: str


class IngestRunResponse(BaseModel):
    run_id: str
    message: str
    run: AgentRun
