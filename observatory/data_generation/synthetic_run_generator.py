"""Synthetic agent run generator with configurable failure injection."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from app.api.schemas.agent_run import AgentRun, TaskType
from app.api.schemas.retrieval_event import RetrievalEvent
from app.api.schemas.tool_call import ToolCall, ToolStatus
from observatory.data_generation.prompt_version_generator import PROMPT_VERSION_SPECS, SYNTHETIC_AGENTS
from observatory.utils.id_utils import generate_run_id, generate_uuid

SYNTHETIC_MODELS = [
    "gpt_4o_mini_simulated", "claude_sonnet_simulated",
    "gemini_flash_simulated", "llama_local_simulated",
]


class FailureScenario(str, Enum):
    SUCCESS = "success"
    SQL_SYNTAX = "sql_syntax_failure"
    SQL_SEMANTIC = "sql_semantic_failure"
    RETRIEVAL_MISS = "retrieval_miss"
    HALLUCINATION = "hallucination"
    WRONG_TOOL = "wrong_tool_call"
    PROMPT_REGRESSION = "prompt_regression"
    LATENCY_SPIKE = "latency_spike"
    COST_SPIKE = "cost_spike"
    FORMAT_VIOLATION = "format_violation"
    MALFORMED = "malformed_record"
    DUPLICATE = "duplicate_run_id"


@dataclass
class FailureRates:
    success: float = 0.60
    sql_syntax: float = 0.05
    sql_semantic: float = 0.05
    retrieval_miss: float = 0.07
    hallucination: float = 0.06
    wrong_tool: float = 0.04
    prompt_regression: float = 0.08
    latency_spike: float = 0.03
    cost_spike: float = 0.02
    format_violation: float = 0.03
    malformed: float = 0.02
    duplicate: float = 0.01

    def choices(self) -> list[tuple[FailureScenario, float]]:
        return [
            (FailureScenario.SUCCESS, self.success),
            (FailureScenario.SQL_SYNTAX, self.sql_syntax),
            (FailureScenario.SQL_SEMANTIC, self.sql_semantic),
            (FailureScenario.RETRIEVAL_MISS, self.retrieval_miss),
            (FailureScenario.HALLUCINATION, self.hallucination),
            (FailureScenario.WRONG_TOOL, self.wrong_tool),
            (FailureScenario.PROMPT_REGRESSION, self.prompt_regression),
            (FailureScenario.LATENCY_SPIKE, self.latency_spike),
            (FailureScenario.COST_SPIKE, self.cost_spike),
            (FailureScenario.FORMAT_VIOLATION, self.format_violation),
            (FailureScenario.MALFORMED, self.malformed),
            (FailureScenario.DUPLICATE, self.duplicate),
        ]

    def normalize(self) -> "FailureRates":
        """Normalize rates to sum to 1.0 while preserving proportions."""
        total = sum(w for _, w in self.choices())
        if total == 0:
            raise ValueError("failure rates cannot all be zero")
        if abs(total - 1.0) < 0.001:
            return self
        factor = 1.0 / total
        return FailureRates(
            success=self.success * factor,
            sql_syntax=self.sql_syntax * factor,
            sql_semantic=self.sql_semantic * factor,
            retrieval_miss=self.retrieval_miss * factor,
            hallucination=self.hallucination * factor,
            wrong_tool=self.wrong_tool * factor,
            prompt_regression=self.prompt_regression * factor,
            latency_spike=self.latency_spike * factor,
            cost_spike=self.cost_spike * factor,
            format_violation=self.format_violation * factor,
            malformed=self.malformed * factor,
            duplicate=self.duplicate * factor,
        )

    def validate_sum(self, tolerance: float = 0.02) -> None:
        total = sum(w for _, w in self.choices())
        if abs(total - 1.0) > tolerance:
            raise ValueError(f"rates must sum to 1.0, got {total:.4f}")


@dataclass
class SyntheticRunBatch:
    agent_runs: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    retrieval_events: list[dict[str, Any]] = field(default_factory=list)
    malformed_records: list[dict[str, Any]] = field(default_factory=list)
    scenario_counts: dict[str, int] = field(default_factory=dict)


class SyntheticRunGenerator:
    QUERIES = {
        TaskType.TEXT_TO_SQL: ["What was total revenue last month?", "Top 10 customers by orders?"],
        TaskType.RETRIEVAL_QA: ["What is our refund policy?", "How do I reset my API key?"],
        TaskType.TOOL_USE: ["Create a support ticket.", "Look up customer 12345."],
        TaskType.SUMMARIZATION: ["Summarize Q3 earnings."],
        TaskType.CLASSIFICATION: ["Classify as billing or technical."],
    }

    def __init__(self, seed: int = 42, failure_rates: Optional[FailureRates] = None,
                 reference_time: Optional[datetime] = None) -> None:
        self.rng = random.Random(seed)
        self.failure_rates = (failure_rates or FailureRates()).normalize()
        self.reference_time = reference_time or datetime.now(timezone.utc)

    def generate_batch(self, count: int) -> SyntheticRunBatch:
        batch = SyntheticRunBatch()
        duplicate_id: Optional[str] = None
        for i in range(count):
            scenario = self._pick()
            batch.scenario_counts[scenario.value] = batch.scenario_counts.get(scenario.value, 0) + 1
            if scenario == FailureScenario.MALFORMED:
                batch.malformed_records.append(self._malformed(i))
                continue
            run_id = generate_run_id()
            if scenario == FailureScenario.DUPLICATE:
                duplicate_id = duplicate_id or run_id
                run_id = duplicate_id
            run, tools, rets = self._bundle(run_id, scenario, i)
            batch.agent_runs.append(run.model_dump(mode="json"))
            batch.tool_calls.extend(t.model_dump(mode="json") for t in tools)
            batch.retrieval_events.extend(e.model_dump(mode="json") for e in rets)
        return batch

    def _pick(self) -> FailureScenario:
        choices, weights = zip(*self.failure_rates.choices())
        return self.rng.choices(list(choices), weights=list(weights), k=1)[0]

    def _bundle(self, run_id: str, scenario: FailureScenario, index: int
                ) -> tuple[AgentRun, list[ToolCall], list[RetrievalEvent]]:
        agent = self.rng.choice(SYNTHETIC_AGENTS)
        task = self._task(agent)
        prompt = "prompt_v5_regression_case" if scenario == FailureScenario.PROMPT_REGRESSION else self._prompt()
        model = self.rng.choice(SYNTHETIC_MODELS)
        query = self.rng.choice(self.QUERIES[task])
        started = self.reference_time - timedelta(days=self.rng.randint(0, 30), hours=self.rng.randint(0, 12))
        latency = self.rng.randint(400, 1800)
        inp, out = self.rng.randint(200, 800), self.rng.randint(50, 400)
        cost = round(inp * 1.5e-7 + out * 6e-7, 6)
        sql: Optional[str] = None
        expected: Optional[str] = None
        answer = "Operation completed successfully."
        ok, err = True, None

        if task == TaskType.TEXT_TO_SQL:
            sql = "SELECT SUM(revenue) FROM revenue_daily WHERE date >= CURRENT_DATE - INTERVAL '1 month'"
            expected = "125000"
            answer = expected
        elif task == TaskType.RETRIEVAL_QA:
            expected = "30-day refund policy applies to unused subscriptions"
            answer = expected
        elif task == TaskType.CLASSIFICATION:
            answer = '{"label": "billing", "confidence": 0.92}'

        if scenario == FailureScenario.SQL_SYNTAX:
            sql, ok, err, answer = "SELECT SUM(revenue) FORM revenue_daily", False, "syntax error", "failed"
        elif scenario == FailureScenario.SQL_SEMANTIC:
            sql, ok, err, answer = "SELECT bad_col FROM revenue_daily", False, "bad column", "failed"
        elif scenario == FailureScenario.RETRIEVAL_MISS:
            ok, err, answer = False, "no relevant chunks", "could not find docs"
        elif scenario == FailureScenario.HALLUCINATION:
            ok, err, answer = False, "unsupported claim", "90-day no-restriction refund policy"
        elif scenario == FailureScenario.WRONG_TOOL:
            ok, err = False, "wrong tool selected"
        elif scenario == FailureScenario.PROMPT_REGRESSION:
            ok, err, answer = False, "prompt regression", "quick unverified answer"
        elif scenario == FailureScenario.LATENCY_SPIKE:
            latency = self.rng.randint(6000, 12000)
        elif scenario == FailureScenario.COST_SPIKE:
            inp, out = self.rng.randint(8000, 15000), self.rng.randint(4000, 8000)
            cost = round(inp * 2e-6 + out * 8e-6, 6)
        elif scenario == FailureScenario.FORMAT_VIOLATION:
            if task == TaskType.CLASSIFICATION:
                answer = "billing maybe"
            ok, err = False, "format violation"

        completed = started + timedelta(milliseconds=latency)
        run = AgentRun(
            run_id=run_id, agent_name=agent, task_type=task, user_query=query,
            prompt_version_id=prompt, model_name=model, started_at=started,
            completed_at=completed, latency_ms=latency, input_tokens=inp,
            output_tokens=out, estimated_cost_usd=cost, final_answer=answer,
            success_flag=ok, error_message=err, generated_sql=sql,
            expected_answer=expected, metadata={"scenario": scenario.value, "index": index},
        )
        return run, self._tools(run, scenario), self._retrievals(run, scenario)

    def _task(self, agent: str) -> TaskType:
        return {
            "sql_analyst_agent": TaskType.TEXT_TO_SQL,
            "research_assistant_agent": TaskType.RETRIEVAL_QA,
            "support_triage_agent": TaskType.CLASSIFICATION,
            "data_ops_agent": TaskType.TEXT_TO_SQL,
            "tool_router_agent": TaskType.TOOL_USE,
        }[agent]

    def _prompt(self) -> str:
        ids = [s["prompt_version_id"] for s in PROMPT_VERSION_SPECS]
        return self.rng.choices(ids, weights=[0.28, 0.28, 0.22, 0.22, 0.0], k=1)[0]

    def _tools(self, run: AgentRun, scenario: FailureScenario) -> list[ToolCall]:
        if run.task_type != TaskType.TOOL_USE and scenario != FailureScenario.WRONG_TOOL:
            return []
        name, status, out, err = "create_ticket", ToolStatus.SUCCESS, {"ticket_id": "T1"}, None
        if scenario == FailureScenario.WRONG_TOOL:
            name, status, out, err = "weather_lookup", ToolStatus.FAILED, None, "wrong tool"
        s = run.started_at + timedelta(milliseconds=50)
        lat = self.rng.randint(100, 500)
        return [ToolCall(
            tool_call_id=generate_uuid(), run_id=run.run_id, tool_name=name,
            tool_input={"subject": run.user_query}, tool_output=out,
            tool_status=status, error_message=err, started_at=s,
            completed_at=s + timedelta(milliseconds=lat), latency_ms=lat,
        )]

    def _retrievals(self, run: AgentRun, scenario: FailureScenario) -> list[RetrievalEvent]:
        if run.task_type not in {TaskType.RETRIEVAL_QA, TaskType.SUMMARIZATION} and scenario not in {
            FailureScenario.HALLUCINATION, FailureScenario.RETRIEVAL_MISS}:
            return []
        if scenario == FailureScenario.RETRIEVAL_MISS:
            return [RetrievalEvent(
                retrieval_id=generate_uuid(), run_id=run.run_id, query_text=run.user_query,
                document_id="d1", chunk_text="irrelevant", rank_position=1,
                relevance_score=0.12, was_used_in_answer=False,
            )]
        return [
            RetrievalEvent(retrieval_id=generate_uuid(), run_id=run.run_id, query_text=run.user_query,
                           document_id="d1", chunk_text="30-day refund policy.",
                           rank_position=1, relevance_score=0.85,
                           was_used_in_answer=scenario != FailureScenario.HALLUCINATION),
        ]

    def _malformed(self, index: int) -> dict[str, Any]:
        kind = self.rng.choice(["missing_field", "negative_latency", "bad_timing", "bad_task", "empty_id"])
        rec: dict[str, Any] = {
            "run_id": generate_run_id(), "agent_name": self.rng.choice(SYNTHETIC_AGENTS),
            "task_type": "text_to_sql", "user_query": "test", "prompt_version_id": "prompt_v1_baseline",
            "model_name": self.rng.choice(SYNTHETIC_MODELS),
            "started_at": self.reference_time.isoformat(),
            "completed_at": (self.reference_time + timedelta(seconds=1)).isoformat(),
            "latency_ms": 500, "input_tokens": 100, "output_tokens": 50,
            "estimated_cost_usd": 0.0001, "final_answer": "x", "success_flag": True,
            "malform_type": kind, "index": index,
        }
        if kind == "missing_field":
            del rec["user_query"]
        elif kind == "negative_latency":
            rec["latency_ms"] = -50
        elif kind == "bad_timing":
            rec["completed_at"] = (self.reference_time - timedelta(hours=2)).isoformat()
        elif kind == "bad_task":
            rec["task_type"] = "invalid"
        elif kind == "empty_id":
            rec["run_id"] = ""
        return rec
