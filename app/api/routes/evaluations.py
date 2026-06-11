from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_app_settings
from app.api.schemas.api_responses import (
    EvaluationListResponse,
    TriggerEvaluationRequest,
    TriggerEvaluationResponse,
)
from app.services.warehouse_reader import WarehouseReader, WarehouseUnavailableError
from observatory.evaluation.engine import EvaluationEngine

router = APIRouter(tags=["evaluations"])


@router.get("/evaluations", response_model=EvaluationListResponse)
def list_evaluations(
    limit: int = Query(500, ge=1, le=1000),
) -> EvaluationListResponse:
    reader = WarehouseReader(get_app_settings())
    try:
        reader.ensure_available()
        df = reader.safe_query(
            "SELECT * FROM evaluation_results ORDER BY evaluated_at DESC",
            limit=limit,
        )
    except WarehouseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    records = df.to_dict(orient="records") if not df.empty else []
    return EvaluationListResponse(evaluations=records, count=len(records))


@router.post("/evaluations/run", response_model=TriggerEvaluationResponse)
def trigger_evaluations(body: TriggerEvaluationRequest) -> TriggerEvaluationResponse:
    try:
        engine = EvaluationEngine(get_app_settings())
        count = engine.run(limit=body.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TriggerEvaluationResponse(
        evaluated_count=count,
        message=f"Evaluated {count} unevaluated runs.",
    )
