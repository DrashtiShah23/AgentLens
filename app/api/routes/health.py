from fastapi import APIRouter

from app.api.dependencies import get_app_settings
from app.api.schemas.api_responses import HealthResponse
from app.services.warehouse_reader import WarehouseReader

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_app_settings()
    reader = WarehouseReader(settings)
    raw_ok = settings.resolve_path(settings.raw_log_dir).exists()
    wh_ok = reader.db_path_exists
    if wh_ok and raw_ok:
        msg = "Warehouse and log directory are available."
        status = "healthy"
    elif wh_ok:
        msg = "Warehouse available. Raw log directory missing."
        status = "degraded"
    else:
        msg = "Warehouse not found. Run: python scripts/run_local_pipeline.py"
        status = "degraded"
    return HealthResponse(
        status=status,
        warehouse_available=wh_ok,
        raw_log_dir_available=raw_ok,
        message=msg,
    )
