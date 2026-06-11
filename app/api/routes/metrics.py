from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_metric_service
from app.api.schemas.api_responses import OverviewMetricsResponse
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseUnavailableError

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=OverviewMetricsResponse)
def metrics_overview(
    days: int = Query(7, ge=1, le=365),
    metrics: MetricService = Depends(get_metric_service),
) -> OverviewMetricsResponse:
    try:
        data = metrics.overview_metrics(days)
    except WarehouseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return OverviewMetricsResponse(**data)


@router.get("/failures")
def metrics_failures(
    days: int = Query(30, ge=1, le=365),
    agent_name: Optional[str] = None,
    metrics: MetricService = Depends(get_metric_service),
) -> dict[str, Any]:
    try:
        by_cat = metrics.failures_by_category(days)
        records = metrics.failure_records(days=days, agent_name=agent_name, limit=500)
    except WarehouseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "time_window_days": days,
        "by_category": by_cat.to_dict(orient="records") if not by_cat.empty else [],
        "failure_records": records.to_dict(orient="records") if not records.empty else [],
    }


@router.get("/prompts")
def metrics_prompts(metrics: MetricService = Depends(get_metric_service)) -> dict[str, Any]:
    try:
        df = metrics.prompt_performance()
    except WarehouseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"prompts": df.to_dict(orient="records") if not df.empty else []}


@router.get("/models")
def metrics_models(metrics: MetricService = Depends(get_metric_service)) -> dict[str, Any]:
    try:
        df = metrics.model_performance()
    except WarehouseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"models": df.to_dict(orient="records") if not df.empty else []}
