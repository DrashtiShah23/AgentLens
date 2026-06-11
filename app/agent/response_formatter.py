"""Format investigation responses for API and dashboard."""

from __future__ import annotations

from typing import Any, Optional

from app.dashboard.components.display_helpers import format_change_points
from app.dashboard.components.layout import friendly_failure, friendly_task


def format_structured_response(
    question: str,
    tool_name: str,
    tool_result: dict[str, Any],
    assumptions: list[str],
    time_window_days: int,
) -> dict[str, Any]:
    """Build structured response without LLM."""
    summary = _build_summary(question, tool_name, tool_result, time_window_days)
    evidence = _build_evidence(question, tool_name, tool_result, time_window_days)
    recommendation = _build_recommendation(question, tool_name, tool_result)
    return {
        "question": question,
        "metric_name": tool_result.get("metric", tool_name),
        "time_window_days": time_window_days,
        "assumptions": assumptions,
        "summary": summary,
        "evidence": evidence,
        "metric_data": tool_result,
        "recommended_action": recommendation,
        "llm_used": False,
    }


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "unavailable"
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "unavailable"


def _fmt_cost(value: Any) -> str:
    if value is None:
        return "$0.00"
    try:
        v = float(value)
        return f"${v:,.2f}" if v >= 0.01 else f"${v:.4f}"
    except (TypeError, ValueError):
        return "$0.00"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _question_lower(question: str) -> str:
    return (question or "").lower()


def _build_summary(
    question: str,
    tool_name: str,
    result: dict[str, Any],
    days: int,
) -> str:
    if result.get("error"):
        return str(result["error"])
    if not result.get("data_available", True) and result.get("message"):
        return result["message"]

    q = _question_lower(question)

    if tool_name == "get_cost_latency_summary" or "expensive" in q:
        return _summary_most_expensive_agent(result, days)
    if tool_name == "get_prompt_comparison":
        return _summary_prompt_regression(result)
    if tool_name == "get_model_comparison":
        return _summary_safest_model(result)
    if tool_name == "get_failure_trends":
        return _summary_top_failure_modes(result, days)
    if tool_name == "get_recent_incidents":
        return _summary_runs_need_review(result)
    if tool_name == "get_overall_reliability":
        return _summary_reliability_change(result, days, q)

    return _generic_summary(tool_name, result, days)


def _build_evidence(
    question: str,
    tool_name: str,
    result: dict[str, Any],
    days: int,
) -> str:
    if result.get("error"):
        return "The metric tool returned an error. See Technical Details for details."

    q = _question_lower(question)

    if tool_name == "get_cost_latency_summary" or "expensive" in q:
        return _evidence_most_expensive_agent(result, days)
    if tool_name == "get_prompt_comparison":
        return _evidence_prompt_regression(result)
    if tool_name == "get_model_comparison":
        return _evidence_safest_model(result)
    if tool_name == "get_failure_trends":
        return _evidence_top_failure_modes(result, days)
    if tool_name == "get_recent_incidents":
        return _evidence_runs_need_review(result)
    if tool_name == "get_overall_reliability":
        return _evidence_reliability_change(result, days)

    return _missing_fields_message(tool_name, result)


def _summary_most_expensive_agent(result: dict[str, Any], days: int) -> str:
    top_name, stats = _top_agent_by_cost(result.get("rows") or [])
    if not top_name:
        return f"No cost data found for the last {days} days."
    return (
        f"The most expensive agent is {top_name}, with an estimated total cost of "
        f"{_fmt_cost(stats['total'])} over the last {days} days."
    )


def _evidence_most_expensive_agent(result: dict[str, Any], days: int) -> str:
    top_name, stats = _top_agent_by_cost(result.get("rows") or [])
    if not top_name:
        return f"No cost rows available for the last {days} days."
    avg = stats["total"] / stats["runs"] if stats["runs"] else 0.0
    return (
        f"Agent: {top_name} · Total cost: {_fmt_cost(stats['total'])} · "
        f"Avg cost per run: {_fmt_cost(avg)} · Run count: {stats['runs']:,} · "
        f"Time window: last {days} days"
    )


def _top_agent_by_cost(rows: list[dict[str, Any]]) -> tuple[Optional[str], dict[str, float]]:
    agents: dict[str, dict[str, float]] = {}
    for row in rows:
        name = row.get("agent_name") or "Unknown"
        runs = _safe_int(row.get("run_count"), 1)
        avg = float(row.get("avg_cost_usd") or 0)
        bucket = agents.setdefault(name, {"total": 0.0, "runs": 0.0})
        bucket["total"] += avg * runs
        bucket["runs"] += runs
    if not agents:
        return None, {"total": 0.0, "runs": 0.0}
    top_name = max(agents, key=lambda k: agents[k]["total"])
    return top_name, agents[top_name]


def _summary_prompt_regression(result: dict[str, Any]) -> str:
    baseline, v5 = _baseline_and_v5(result.get("prompts") or [])
    if not baseline or not v5:
        return (
            "I found prompt comparison records, but baseline or prompt_v5_regression_case "
            "data is missing."
        )
    base_rel = baseline.get("reliability_score")
    v5_rel = v5.get("reliability_score")
    delta = float(v5_rel or 0) - float(base_rel or 0)
    if delta < -0.005 or v5.get("regression_detected"):
        return "Yes, prompt_v5_regression_case made things worse compared with the baseline."
    if delta > 0.005:
        return "No, prompt_v5_regression_case did not make things worse — reliability improved vs baseline."
    return "No, prompt_v5_regression_case did not materially change reliability compared with baseline."


def _evidence_prompt_regression(result: dict[str, Any]) -> str:
    baseline, v5 = _baseline_and_v5(result.get("prompts") or [])
    if not baseline or not v5:
        return (
            "Prompt comparison data is available, but baseline or prompt_v5_regression_case "
            "rows were not found."
        )
    base_rel = baseline.get("reliability_score")
    v5_rel = v5.get("reliability_score")
    delta = float(v5_rel or 0) - float(base_rel or 0)
    return (
        f"Baseline reliability ({baseline.get('prompt_version_id')}): {_fmt_pct(base_rel)} · "
        f"prompt_v5 reliability: {_fmt_pct(v5_rel)} · "
        f"Change: {format_change_points(delta)}"
    )


def _baseline_and_v5(prompts: list[dict[str, Any]]):
    baseline = next((p for p in prompts if p.get("prompt_version_id") == "prompt_v1_baseline"), None)
    v5 = next((p for p in prompts if p.get("prompt_version_id") == "prompt_v5_regression_case"), None)
    return baseline, v5


def _summary_safest_model(result: dict[str, Any]) -> str:
    best, task = _best_model_for_task(result)
    if not best:
        task_label = friendly_task(task) if task else "the selected task"
        return f"No model comparison data is available for {task_label}."
    task_label = friendly_task(best.get("task_type") or task)
    return (
        f"The safest model for {task_label} is {best.get('model_name')} "
        f"with {_fmt_pct(best.get('reliability_score'))} reliability."
    )


def _evidence_safest_model(result: dict[str, Any]) -> str:
    best, task = _best_model_for_task(result)
    if not best:
        task_label = friendly_task(task) if task else "the selected task"
        return f"No model rows are available for {task_label} in the comparison data."
    parts = [
        f"Model: {best.get('model_name')}",
        f"Task: {friendly_task(best.get('task_type') or task)}",
        f"Reliability: {_fmt_pct(best.get('reliability_score'))}",
        f"Failure rate: {_fmt_pct(best.get('failure_rate'))}",
    ]
    if best.get("sql_score") is not None:
        parts.append(f"SQL quality: {_fmt_pct(best.get('sql_score'))}")
    elif best.get("correctness_score") is not None:
        parts.append(f"Answer quality: {_fmt_pct(best.get('correctness_score'))}")
    parts.append(f"Run count: {_safe_int(best.get('run_count')):,}")
    return " · ".join(parts)


def _best_model_for_task(result: dict[str, Any]) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    models = result.get("models") or []
    if not models:
        return None, result.get("task_type_filter")
    task = result.get("task_type_filter")
    scoped = [m for m in models if not task or m.get("task_type") == task]
    if not scoped:
        scoped = models
    best = max(scoped, key=lambda m: float(m.get("reliability_score") or 0))
    return best, task or best.get("task_type")


def _summary_top_failure_modes(result: dict[str, Any], days: int) -> str:
    cats = _sorted_failure_categories(result.get("by_category") or [])
    if not cats:
        return f"No failure trends found for the last {days} days."
    top = cats[0]
    label = friendly_failure(top.get("failure_category", ""))
    return (
        f"The most common failure type is {label} "
        f"with {_safe_int(top.get('failure_count')):,} incidents."
    )


def _evidence_top_failure_modes(result: dict[str, Any], days: int) -> str:
    cats = _sorted_failure_categories(result.get("by_category") or [])
    if not cats:
        return f"No failure categories recorded in the last {days} days."
    lines = []
    for cat in cats[:3]:
        label = friendly_failure(cat.get("failure_category", ""))
        lines.append(f"{label}: {_safe_int(cat.get('failure_count')):,}")
    return f"Top failure types · Time window: last {days} days · " + " · ".join(lines)


def _sorted_failure_categories(cats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(cats, key=lambda c: _safe_int(c.get("failure_count")), reverse=True)


def _summary_runs_need_review(result: dict[str, Any]) -> str:
    count, _ = _review_runs(result)
    if count == 0:
        return "There are no runs that need human review in the available incident data."
    noun = "run" if count == 1 else "runs"
    return f"There are {count:,} {noun} that need human review."


def _evidence_runs_need_review(result: dict[str, Any]) -> str:
    count, examples = _review_runs(result)
    if count == 0:
        return "No incident or failure records flagged for human review."
    lines = []
    for ex in examples[:3]:
        run_id = ex.get("run_id", "unknown")
        agent = ex.get("agent_name", "unknown agent")
        sev = ex.get("severity", "unknown severity")
        rel = ex.get("overall_score") or ex.get("reliability_score")
        rel_s = _fmt_pct(rel) if rel is not None else "unavailable reliability"
        lines.append(f"{run_id} ({agent}, severity {sev}, reliability {rel_s})")
    return "Top examples: " + "; ".join(lines) if lines else f"Total flagged: {count:,}"


def _review_runs(result: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    incidents = result.get("incidents") or []
    if not incidents:
        return 0, []
    if "human_review_count" in incidents[0]:
        count = sum(_safe_int(i.get("human_review_count")) for i in incidents)
        ranked = sorted(incidents, key=lambda i: _safe_int(i.get("human_review_count")), reverse=True)
        return count, ranked
    review_rows = [i for i in incidents if i.get("requires_human_review", True)]
    count = len(review_rows)
    ranked = sorted(
        review_rows,
        key=lambda i: (
            0 if str(i.get("severity", "")).lower() == "critical" else 1,
            float(i.get("overall_score") or i.get("confidence_score") or 1),
        ),
    )
    return count, ranked


def _summary_reliability_change(result: dict[str, Any], days: int, question: str) -> str:
    trend = result.get("trend_rows") or []
    summary = result.get("summary") or {}
    if not summary.get("total_runs"):
        return f"No run data found for the last {days} days."

    if len(trend) >= 2:
        ordered = sorted(trend, key=lambda r: str(r.get("run_date", "")))
        prev, curr = ordered[-2], ordered[-1]
        prev_rel = prev.get("reliability_score")
        curr_rel = curr.get("reliability_score")
        if prev_rel is not None and curr_rel is not None:
            delta = float(curr_rel) - float(prev_rel)
            direction = "dropped" if delta < 0 else "rose" if delta > 0 else "held steady"
            return (
                f"Reliability {direction} from {_fmt_pct(prev_rel)} to {_fmt_pct(curr_rel)} "
                f"between the last two available days."
            )

    rel = summary.get("reliability_score")
    if "yesterday" in question and len(trend) <= 1:
        return (
            f"Only a single day of reliability data is available for the last {days} days. "
            f"Overall reliability is {_fmt_pct(rel)}."
        )
    if len(trend) <= 1:
        return (
            f"Insufficient daily trend data to compare day-over-day reliability. "
            f"Overall reliability for the window is {_fmt_pct(rel)}."
        )
    return f"Overall reliability for the last {days} days is {_fmt_pct(rel)}."


def _evidence_reliability_change(result: dict[str, Any], days: int) -> str:
    trend = result.get("trend_rows") or []
    summary = result.get("summary") or {}
    if len(trend) >= 2:
        ordered = sorted(trend, key=lambda r: str(r.get("run_date", "")))
        prev, curr = ordered[-2], ordered[-1]
        return (
            f"Previous day ({prev.get('run_date')}): {_fmt_pct(prev.get('reliability_score'))} · "
            f"Latest day ({curr.get('run_date')}): {_fmt_pct(curr.get('reliability_score'))} · "
            f"Runs on latest day: {_safe_int(curr.get('total_runs')):,}"
        )
    return (
        f"Total runs: {_safe_int(summary.get('total_runs')):,} · "
        f"Reliability: {_fmt_pct(summary.get('reliability_score'))} · "
        f"Failure rate: {_fmt_pct(summary.get('failure_rate'))} · "
        f"Time window: last {days} days"
    )


def _generic_summary(tool_name: str, result: dict[str, Any], days: int) -> str:
    rows = result.get("rows") or result.get("incidents") or result.get("edges") or []
    if not rows:
        return f"No data returned for {tool_name} in the selected window."
    return f"Returned {len(rows)} aggregated records for {result.get('metric', tool_name)}."


def _missing_fields_message(tool_name: str, result: dict[str, Any]) -> str:
    return (
        f"I found metric records for {result.get('metric', tool_name)}, but they do not include "
        "the fields needed to answer this question directly."
    )


def _build_recommendation(question: str, tool_name: str, result: dict[str, Any]) -> str:
    q = _question_lower(question)

    if tool_name == "get_cost_latency_summary" or "expensive" in q:
        return (
            "Review this agent's prompt length, tool usage, and model choice to reduce cost."
        )
    if tool_name == "get_prompt_comparison":
        baseline, v5 = _baseline_and_v5(result.get("prompts") or [])
        if baseline and v5:
            delta = float(v5.get("reliability_score") or 0) - float(baseline.get("reliability_score") or 0)
            if delta < -0.005 or v5.get("regression_detected"):
                return "Roll back or inspect the prompt change if reliability is lower."
        return "Continue monitoring prompt versions before wider rollout."
    if tool_name == "get_model_comparison":
        return "Use this model for Text to SQL tasks, but monitor failure cases."
    if tool_name == "get_failure_trends":
        cats = _sorted_failure_categories(result.get("by_category") or [])
        if cats:
            cat = cats[0].get("failure_category", "unknown")
            recs = {
                "sql_failure": "Prioritize SQL linting and schema validation fixes first.",
                "hallucination": "Strengthen retrieval grounding in prompts.",
                "tool_failure": "Review tool routing and schemas.",
                "prompt_regression": "Compare prompt versions and roll back if needed.",
            }
            return recs.get(cat, "Prioritize fixes for the largest failure category first.")
    if tool_name == "get_recent_incidents":
        return "Review critical runs first, then low reliability runs."
    if tool_name == "get_overall_reliability":
        return "Inspect failure categories and prompt changes during that period."
    return "Review the cited metrics in the dashboard for the relevant agent or prompt version."
