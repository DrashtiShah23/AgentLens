"""FastAPI dependency injection."""

from functools import lru_cache

from app.agent.graph import create_investigation_agent
from app.services.log_writer import LogWriter
from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader
from observatory.config.settings import Settings, get_settings


@lru_cache
def get_app_settings() -> Settings:
    return get_settings()


def get_warehouse_reader() -> WarehouseReader:
    return WarehouseReader(get_app_settings())


def get_metric_service() -> MetricService:
    return MetricService(get_warehouse_reader(), get_app_settings())


def get_log_writer() -> LogWriter:
    return LogWriter(get_app_settings())


def get_investigation_agent():
    return create_investigation_agent(get_app_settings())
