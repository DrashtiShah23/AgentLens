"""Classification orchestrator — deterministic, no LLM."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from app.api.schemas.failure_record import FailureRecord
from observatory.classification.failure_classifier import FailureClassifier
from observatory.classification.recommendation_engine import RecommendationEngine
from observatory.classification.severity_classifier import SeverityClassifier
from observatory.config.settings import Settings, get_settings
from observatory.utils.id_utils import generate_uuid
from observatory.warehouse.duckdb_connection import connection_context


class ClassificationEngine:
    def __init__(self, settings: Optional[Settings] = None,
                 score_threshold: float = 0.70) -> None:
        self.settings = settings or get_settings()
        self.score_threshold = score_threshold
        self.classifier = FailureClassifier()
        self.severity = SeverityClassifier()
        self.recommendations = RecommendationEngine()

    def run(self, limit: Optional[int] = None) -> int:
        contexts = self._fetch_candidates(limit)
        count = 0
        for ctx in contexts:
            record = self._classify(ctx)
            self._persist(record)
            self._update_evaluation(ctx["run_id"], record)
            count += 1
        return count

    def _fetch_candidates(self, limit: Optional[int]) -> list[dict[str, Any]]:
        sql = """
            SELECT r.*, e.correctness_score, e.sql_score, e.tool_score, e.retrieval_score,
                   e.format_score, e.latency_score, e.cost_score, e.overall_score
            FROM agent_runs r
            JOIN evaluation_results e ON r.run_id = e.run_id
            LEFT JOIN failure_modes f ON r.run_id = f.run_id
            WHERE f.run_id IS NULL
              AND (e.overall_score < ? OR r.is_duplicate = TRUE)
        """
        params: list[Any] = [self.score_threshold]
        if limit:
            sql += f" LIMIT {int(limit)}"
        with connection_context(self.settings) as conn:
            rows = conn.execute(sql, params).fetchdf().to_dict(orient="records")
            if not rows:
                return []
            run_ids = [r["run_id"] for r in rows]
            ph = ",".join(["?"] * len(run_ids))
            tools = conn.execute(f"SELECT * FROM tool_calls WHERE run_id IN ({ph})", run_ids
                                 ).fetchdf().to_dict(orient="records")
            rets = conn.execute(f"SELECT * FROM retrieval_events WHERE run_id IN ({ph})", run_ids
                                ).fetchdf().to_dict(orient="records")
        tb: dict[str, list] = {}
        rb: dict[str, list] = {}
        for t in tools:
            tb.setdefault(t["run_id"], []).append(t)
        for r in rets:
            rb.setdefault(r["run_id"], []).append(r)
        for row in rows:
            row["tool_calls"] = tb.get(row["run_id"], [])
            row["retrieval_events"] = rb.get(row["run_id"], [])
            row["_confidence_threshold"] = self.settings.classification_confidence_threshold
        return rows

    def _classify(self, ctx: dict[str, Any]) -> FailureRecord:
        result = self.classifier.classify(ctx)
        severity = self.severity.assign(ctx, result.primary_category, result.confidence_score)
        rec = self.recommendations.recommend(result.primary_category)
        return FailureRecord(
            failure_id=generate_uuid(),
            run_id=ctx["run_id"],
            primary_category=result.primary_category,
            secondary_signals=result.secondary_signals,
            confidence_score=result.confidence_score,
            severity=severity,
            recommendation=rec,
            requires_human_review=result.requires_human_review,
            classified_at=datetime.now(timezone.utc),
        )

    def _persist(self, record: FailureRecord) -> None:
        row = record.model_dump(mode="json")
        row["secondary_signals"] = json.dumps(row["secondary_signals"])
        with connection_context(self.settings) as conn:
            df = pd.DataFrame([row])
            conn.register("_fail_df", df)
            conn.execute("""
                INSERT OR REPLACE INTO failure_modes
                SELECT failure_id, run_id, primary_category, secondary_signals,
                       confidence_score, severity, recommendation, requires_human_review,
                       classified_at, CURRENT_TIMESTAMP FROM _fail_df
            """)

    def _update_evaluation(self, run_id: str, record: FailureRecord) -> None:
        with connection_context(self.settings) as conn:
            conn.execute(
                "UPDATE evaluation_results SET failure_category=?, severity=? WHERE run_id=?",
                [record.primary_category, record.severity, run_id],
            )
