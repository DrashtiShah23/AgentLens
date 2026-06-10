"""Evaluation orchestrator — deterministic, no LLM."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from app.api.schemas.evaluation_result import EvaluationResult
from observatory.config.settings import Settings, get_settings
from observatory.evaluation.cost_evaluator import CostEvaluator
from observatory.evaluation.correctness_evaluator import CorrectnessEvaluator
from observatory.evaluation.format_evaluator import FormatEvaluator
from observatory.evaluation.latency_evaluator import LatencyEvaluator
from observatory.evaluation.overall_score import OverallScoreCalculator
from observatory.evaluation.retrieval_evaluator import RetrievalEvaluator
from observatory.evaluation.sql_evaluator import SqlEvaluator
from observatory.evaluation.tool_call_evaluator import ToolCallEvaluator
from observatory.utils.id_utils import generate_uuid
from observatory.warehouse.duckdb_connection import connection_context


class EvaluationEngine:
    """Run all deterministic evaluators and persist results."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.correctness = CorrectnessEvaluator()
        self.sql = SqlEvaluator(self.settings)
        self.tool = ToolCallEvaluator(self.settings)
        self.retrieval = RetrievalEvaluator(self.settings)
        self.format_eval = FormatEvaluator()
        self.latency = LatencyEvaluator(self.settings)
        self.cost = CostEvaluator(self.settings)
        self.overall = OverallScoreCalculator()

    def run(self, limit: Optional[int] = None) -> int:
        contexts = self._fetch_unevaluated_contexts(limit)
        count = 0
        for ctx in contexts:
            result = self._evaluate_context(ctx)
            self._persist(result)
            count += 1
        return count

    def _fetch_unevaluated_contexts(self, limit: Optional[int]) -> list[dict[str, Any]]:
        sql = """
            SELECT r.* FROM agent_runs r
            LEFT JOIN evaluation_results e ON r.run_id = e.run_id
            WHERE e.run_id IS NULL AND r.is_duplicate = FALSE
        """
        if limit:
            sql += f" LIMIT {int(limit)}"
        with connection_context(self.settings) as conn:
            runs = conn.execute(sql).fetchdf().to_dict(orient="records")
            if not runs:
                return []
            run_ids = [r["run_id"] for r in runs]
            placeholders = ",".join(["?"] * len(run_ids))
            tools = conn.execute(
                f"SELECT * FROM tool_calls WHERE run_id IN ({placeholders})", run_ids
            ).fetchdf().to_dict(orient="records")
            rets = conn.execute(
                f"SELECT * FROM retrieval_events WHERE run_id IN ({placeholders})", run_ids
            ).fetchdf().to_dict(orient="records")

        tools_by_run: dict[str, list] = {}
        rets_by_run: dict[str, list] = {}
        for t in tools:
            tools_by_run.setdefault(t["run_id"], []).append(t)
        for r in rets:
            rets_by_run.setdefault(r["run_id"], []).append(r)

        contexts = []
        for run in runs:
            rid = run["run_id"]
            contexts.append({**run, "tool_calls": tools_by_run.get(rid, []),
                             "retrieval_events": rets_by_run.get(rid, [])})
        return contexts

    def _evaluate_context(self, ctx: dict[str, Any]) -> EvaluationResult:
        task = ctx.get("task_type", "")
        notes: list[str] = []

        corr = self.correctness.evaluate(ctx)
        sql_r = self.sql.evaluate(ctx) if task == "text_to_sql" else type(corr)(score=None, notes="N/A")
        tool_r = self.tool.evaluate(ctx)
        ret_r = self.retrieval.evaluate(ctx)
        fmt_r = self.format_eval.evaluate(ctx)
        lat_r = self.latency.evaluate(ctx)
        cost_r = self.cost.evaluate(ctx)

        components = {
            "correctness": corr.score,
            "sql": sql_r.score if task == "text_to_sql" else None,
            "tool": tool_r.score,
            "retrieval": ret_r.score,
            "format": fmt_r.score,
            "latency": lat_r.score,
            "cost": cost_r.score,
        }
        overall = self.overall.compute(task, components)
        for r in [corr, sql_r, tool_r, ret_r, fmt_r, lat_r, cost_r]:
            if r.notes:
                notes.append(f"{r.notes}")

        return EvaluationResult(
            evaluation_id=generate_uuid(),
            run_id=ctx["run_id"],
            correctness_score=components["correctness"],
            sql_score=components["sql"],
            tool_score=components["tool"],
            retrieval_score=components["retrieval"],
            format_score=components["format"],
            latency_score=components["latency"],
            cost_score=components["cost"],
            overall_score=overall,
            evaluator_notes="; ".join(notes) if notes else None,
            evaluated_at=datetime.now(timezone.utc),
        )

    def _persist(self, result: EvaluationResult) -> None:
        row = result.model_dump(mode="json")
        with connection_context(self.settings) as conn:
            df = pd.DataFrame([row])
            conn.register("_eval_df", df)
            conn.execute("""
                INSERT OR REPLACE INTO evaluation_results
                SELECT evaluation_id, run_id, correctness_score, sql_score, tool_score,
                       retrieval_score, format_score, latency_score, cost_score, overall_score,
                       failure_category, severity, evaluator_notes, evaluated_at, CURRENT_TIMESTAMP
                FROM _eval_df
            """)
