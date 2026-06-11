from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_log_writer, get_metric_service
from app.api.schemas.api_responses import IngestRunResponse, RunDetailResponse, RunListResponse
from app.services.log_writer import LogWriter
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseUnavailableError

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=IngestRunResponse, status_code=201)
def ingest_run(payload: dict[str, Any], writer: LogWriter = Depends(get_log_writer)) -> IngestRunResponse:
    try:
        run = writer.write_run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestRunResponse(run_id=run.run_id, message="Run validated and written to raw logs.", run=run)


@router.get("", response_model=RunListResponse)
def list_runs(
    days: int = Query(30, ge=1, le=365),
    agent_name: Optional[str] = None,
    model_name: Optional[str] = None,
    prompt_version_id: Optional[str] = None,
    task_type: Optional[str] = None,
    success_flag: Optional[bool] = None,
    failure_category: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(500, ge=1, le=1000),
    metrics: MetricService = Depends(get_metric_service),
) -> RunListResponse:
    try:
        df = metrics.search_runs(
            days=days, agent_name=agent_name, model_name=model_name,
            prompt_version_id=prompt_version_id, task_type=task_type,
            success_flag=success_flag, failure_category=failure_category,
            severity=severity, limit=limit,
        )
    except WarehouseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    records = df.to_dict(orient="records") if not df.empty else []
    return RunListResponse(runs=records, count=len(records))


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str, metrics: MetricService = Depends(get_metric_service)) -> RunDetailResponse:
    try:
        detail = metrics.run_detail(run_id)
    except WarehouseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not detail:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
    return RunDetailResponse(
        run_id=run_id,
        run=detail.get("run"),
        evaluation=detail.get("evaluation"),
        failure=detail.get("failure"),
        tool_calls=detail.get("tool_calls", []),
        retrieval_events=detail.get("retrieval_events", []),
    )
