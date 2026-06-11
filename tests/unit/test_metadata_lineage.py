import json

from observatory.metadata.catalog_writer import CatalogWriter
from observatory.metadata.dbt_manifest_parser import extract_models
from observatory.metadata.lineage_builder import build_lineage_edges


SAMPLE_MANIFEST = {
    "nodes": {
        "model.ai_failure_observatory.stg_agent_runs": {
            "name": "stg_agent_runs",
            "description": "Staged agent runs",
            "columns": {"run_id": {"description": "PK", "tests": ["unique", "not_null"]}},
            "depends_on": {"nodes": []},
            "created_at": "2024-01-01T00:00:00Z",
        },
        "model.ai_failure_observatory.mart_agent_reliability": {
            "name": "mart_agent_reliability",
            "description": "Agent reliability mart",
            "columns": {"agent_name": {"description": "Agent", "tests": ["not_null"]}},
            "depends_on": {"nodes": ["model.ai_failure_observatory.stg_agent_runs"]},
            "created_at": "2024-01-01T00:00:00Z",
        },
    }
}


def test_extract_models_shape():
    models = extract_models(SAMPLE_MANIFEST)
    assert len(models) == 2
    assert models[0]["model_name"] == "stg_agent_runs"
    assert models[0]["layer"] == "staging"
    assert "run_id" in [c["name"] for c in models[0]["columns"]]


def test_lineage_edges_shape():
    edges = build_lineage_edges(SAMPLE_MANIFEST)
    assert len(edges) == 1
    assert edges[0]["upstream"] == "stg_agent_runs"
    assert edges[0]["downstream"] == "mart_agent_reliability"


def test_catalog_atomic_write(test_settings, tmp_path, monkeypatch):
    manifest_dir = test_settings.project_root() / "dbt_project" / "target"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.json").write_text(json.dumps(SAMPLE_MANIFEST))

    writer = CatalogWriter(test_settings)
    catalog_path, lineage_path = writer.refresh()
    assert catalog_path.exists()
    assert lineage_path.exists()
    catalog = json.loads(catalog_path.read_text())
    lineage = json.loads(lineage_path.read_text())
    assert "models" in catalog
    assert "edges" in lineage
    assert catalog["models"][0]["owner"] == "data_engineering"
