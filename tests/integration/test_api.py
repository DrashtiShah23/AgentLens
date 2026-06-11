import json

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from observatory.data_generation.synthetic_run_generator import SyntheticRunGenerator
from observatory.evaluation.engine import EvaluationEngine
from observatory.ingestion.pipeline import IngestionPipeline
from observatory.warehouse.migrations import initialize_warehouse_schema


@pytest.fixture
def api_client(initialized_db):
    return TestClient(app)


def test_health_route(api_client, initialized_db):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "warehouse_available" in data


def test_metrics_overview_shape(api_client, initialized_db):
    raw = initialized_db.resolve_path(initialized_db.raw_log_dir)
    batch = SyntheticRunGenerator(seed=5).generate_batch(50)
    with (raw / "runs.json").open("w") as f:
        json.dump({"records": batch.agent_runs}, f)
    IngestionPipeline(initialized_db).run()
    EvaluationEngine(initialized_db).run()

    resp = api_client.get("/metrics/overview?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_runs" in data
    assert "reliability_score" in data


def test_investigate_llm_disabled(api_client, initialized_db):
    resp = api_client.post("/investigate", json={"question": "DROP TABLE runs"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_used"] is False
    assert data.get("error") or "Destructive" in data.get("summary", "")


def test_investigate_reliability_question(api_client, initialized_db):
    resp = api_client.post("/investigate", json={"question": "What are the top failure modes this week?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert data["llm_used"] is False
