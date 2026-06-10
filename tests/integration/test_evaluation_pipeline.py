import json

from observatory.classification.engine import ClassificationEngine
from observatory.data_generation.synthetic_run_generator import SyntheticRunGenerator
from observatory.evaluation.engine import EvaluationEngine
from observatory.ingestion.pipeline import IngestionPipeline
from observatory.warehouse.duckdb_connection import connection_context
from observatory.warehouse.queries import count_table


def test_full_eval_and_classify(initialized_db):
    settings = initialized_db
    raw = settings.resolve_path(settings.raw_log_dir)
    batch = SyntheticRunGenerator(seed=11).generate_batch(200)
    with (raw / "runs.json").open("w") as f:
        json.dump({"records": batch.agent_runs}, f)
    with (raw / "tools.json").open("w") as f:
        json.dump({"records": batch.tool_calls}, f)
    with (raw / "retrieval.json").open("w") as f:
        json.dump({"records": batch.retrieval_events}, f)

    IngestionPipeline(settings).run()
    eval_count = EvaluationEngine(settings).run()
    assert eval_count > 0
    assert count_table("evaluation_results", settings) == eval_count

    class_count = ClassificationEngine(settings).run()
    assert class_count > 0

    with connection_context(settings) as conn:
        v5 = conn.execute("""
            SELECT avg(e.overall_score) FROM agent_runs r
            JOIN evaluation_results e ON r.run_id = e.run_id
            WHERE r.prompt_version_id = 'prompt_v5_regression_case'
        """).fetchone()[0]
        v1 = conn.execute("""
            SELECT avg(e.overall_score) FROM agent_runs r
            JOIN evaluation_results e ON r.run_id = e.run_id
            WHERE r.prompt_version_id = 'prompt_v1_baseline'
        """).fetchone()[0]
    if v5 is not None and v1 is not None:
        assert v5 < v1
