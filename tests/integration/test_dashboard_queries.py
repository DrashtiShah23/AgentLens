import json

from app.services.metric_service import MetricService
from app.services.warehouse_reader import WarehouseReader, WarehouseUnavailableError
from observatory.data_generation.synthetic_run_generator import SyntheticRunGenerator
from observatory.evaluation.engine import EvaluationEngine
from observatory.ingestion.pipeline import IngestionPipeline


def test_overview_metrics_empty_db(test_settings):
    reader = WarehouseReader(test_settings)
    metrics = MetricService(reader, test_settings)
    overview = metrics.overview_metrics()
    assert overview["total_runs"] == 0


def test_overview_with_data(initialized_db):
    settings = initialized_db
    raw = settings.resolve_path(settings.raw_log_dir)
    batch = SyntheticRunGenerator(seed=8).generate_batch(100)
    with (raw / "runs.json").open("w") as f:
        json.dump({"records": batch.agent_runs}, f)
    IngestionPipeline(settings).run()
    EvaluationEngine(settings).run()

    metrics = MetricService(WarehouseReader(settings), settings)
    overview = metrics.overview_metrics(days=30)
    assert overview["total_runs"] > 0

    trend = metrics.reliability_over_time(30)
    assert trend is not None

    prompts = metrics.prompt_performance()
    assert prompts is not None


def test_warehouse_unavailable_raises(test_settings):
    reader = WarehouseReader(test_settings)
    try:
        reader.ensure_available()
        assert False
    except WarehouseUnavailableError:
        pass
