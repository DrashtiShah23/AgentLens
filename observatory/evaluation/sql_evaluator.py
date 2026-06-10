"""Deterministic SQL evaluator using sqlglot."""

import re
from typing import Any, Optional

import sqlglot
from sqlglot import exp

from observatory.config.settings import Settings, get_settings
from observatory.evaluation.base_evaluator import BaseEvaluator, EvaluatorResult


class SqlEvaluator(BaseEvaluator):
    name = "sql"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        sql = context.get("generated_sql")
        if not sql or not str(sql).strip():
            return EvaluatorResult(score=0.0, checks_failed=["sql_not_empty"],
                                   notes="generated_sql is empty")

        sql_str = str(sql).strip()
        checks = ["sql_not_empty"]
        total_checks = 6
        passed = 1

        # Destructive keywords
        lower = sql_str.lower()
        for kw in self.settings.destructive_sql_keywords:
            if re.search(rf"\b{kw}\b", lower):
                return EvaluatorResult(score=0.0, checks_passed=checks,
                                       checks_failed=["no_destructive_sql"],
                                       notes=f"destructive keyword: {kw}")

        # Parse
        try:
            parsed = sqlglot.parse_one(sql_str, read="duckdb")
            checks.append("sql_parses")
            passed += 1
        except Exception as exc:
            return EvaluatorResult(score=0.0, checks_passed=checks,
                                   checks_failed=["sql_parses"], notes=str(exc))

        # Tables
        tables = {t.name.lower() for t in parsed.find_all(exp.Table) if t.name}
        bad_tables = tables - {t.lower() for t in self.settings.allowed_sql_tables}
        if bad_tables:
            return EvaluatorResult(
                score=passed / total_checks, checks_passed=checks,
                checks_failed=["allowed_tables"], notes=f"disallowed tables: {bad_tables}",
            )
        checks.append("allowed_tables")
        passed += 1

        # Columns
        for col in parsed.find_all(exp.Column):
            col_name = col.name
            table_name = col.table or (next(iter(tables)) if len(tables) == 1 else None)
            if table_name and table_name.lower() in self.settings.allowed_sql_columns:
                allowed = self.settings.allowed_sql_columns[table_name.lower()]
                if col_name and col_name.lower() not in {c.lower() for c in allowed}:
                    return EvaluatorResult(
                        score=passed / total_checks, checks_passed=checks,
                        checks_failed=["allowed_columns"],
                        notes=f"column {col_name} not in {table_name}",
                    )
        checks.append("allowed_columns")
        passed += 1

        checks.append("no_destructive_sql")
        passed += 1

        # Result match
        expected = context.get("expected_answer")
        if expected is not None:
            answer = context.get("final_answer", "")
            if str(expected).strip() in str(answer) or str(answer).strip() == str(expected).strip():
                checks.append("result_match")
                passed += 1
            else:
                return EvaluatorResult(score=passed / total_checks, checks_passed=checks,
                                       checks_failed=["result_match"])
        else:
            passed += 1
            checks.append("result_match_skipped")

        return EvaluatorResult(score=1.0, checks_passed=checks)
