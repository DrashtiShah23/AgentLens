"""Investigation agent with LangGraph support and deterministic fallback."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.agent.prompts import SUMMARY_PROMPT, SYSTEM_PROMPT
from app.agent.response_formatter import format_structured_response
from app.agent.tools import (
    InvestigationTools, build_tool_kwargs, detect_tool, parse_time_window, reject_unsafe_input,
)
from observatory.config.settings import Settings, get_settings

try:
    from langgraph.graph import END, StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class BaseInvestigationAgent(ABC):
    @abstractmethod
    def investigate(self, question: str) -> dict[str, Any]:
        ...


class DeterministicInvestigationAgent(BaseInvestigationAgent):
    """Fallback agent — no LLM, structured metric summaries only."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.tools = InvestigationTools(self.settings)

    def investigate(self, question: str) -> dict[str, Any]:
        safety = reject_unsafe_input(question)
        if safety:
            return {
                "question": question, "error": safety, "llm_used": False,
                "summary": safety, "recommended_action": "Rephrase as a natural language question.",
            }
        if not self._is_reliability_scope(question):
            return {
                "question": question,
                "error": "Question is outside reliability observability scope.",
                "summary": "I can only answer questions about agent reliability, failures, prompts, models, cost, and latency.",
                "recommended_action": "Ask about reliability trends, failure modes, or prompt regressions.",
                "llm_used": False,
            }

        days, assumptions = parse_time_window(question)
        tool_name = detect_tool(question)
        run_id = self._extract_run_id(question) if tool_name == "get_run_details" else None
        if tool_name == "get_run_details" and not run_id:
            return {
                "question": question,
                "error": "No run_id found in question.",
                "summary": "Please provide a run ID to look up run details.",
                "recommended_action": "Open Run Review Center and pick a run to inspect.",
                "llm_used": False,
            }
        kwargs = build_tool_kwargs(
            tool_name, question, days,
            run_id=run_id,
            model_name=self._extract_model_name(question),
        )
        result = self.tools.dispatch(tool_name, **kwargs)
        if result.get("error"):
            return {
                "question": question,
                "error": result["error"],
                "summary": "I could not complete that investigation because the metric tool returned an error.",
                "recommended_action": "Run dashboard smoke check or inspect logs.",
                "metric_data": result,
                "time_window_days": days,
                "assumptions": assumptions,
                "llm_used": False,
            }
        return format_structured_response(question, tool_name, result, assumptions, days)

    @staticmethod
    def _is_reliability_scope(question: str) -> bool:
        keywords = [
            "reliability", "failure", "prompt", "model", "agent", "cost", "latency",
            "incident", "run", "sql", "tool", "hallucin", "regression", "lineage",
        ]
        return any(k in question.lower() for k in keywords)

    @staticmethod
    def _extract_run_id(question: str) -> Optional[str]:
        match = re.search(r"run_[a-f0-9]{8,}", question)
        return match.group(0) if match else None

    @staticmethod
    def _extract_model_name(question: str) -> Optional[str]:
        for name in ["mart_agent_reliability", "mart_prompt_regression", "stg_agent_runs"]:
            if name in question:
                return name
        match = re.search(r"mart_\w+", question)
        return match.group(0) if match else None


class LangGraphInvestigationAgent(DeterministicInvestigationAgent):
    """LangGraph wrapper — adds optional LLM summary when enabled."""

    def investigate(self, question: str) -> dict[str, Any]:
        response = super().investigate(question)
        if response.get("error") or not self.settings.use_llm:
            return response
        response["llm_used"] = False
        llm_summary = self._maybe_llm_summary(question, response)
        if llm_summary:
            response["summary"] = llm_summary
            response["llm_used"] = True
        return response

    def _maybe_llm_summary(self, question: str, response: dict[str, Any]) -> Optional[str]:
        try:
            import urllib.request
            import json
            prompt = SUMMARY_PROMPT.format(
                question=question,
                assumptions=response.get("assumptions", []),
                data=str(response.get("metric_data", {}))[:2000],
            )
            payload = json.dumps({
                "model": self.settings.llm_model,
                "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return data.get("response", "").strip() or None
        except Exception:
            return None


def create_investigation_agent(settings: Optional[Settings] = None) -> BaseInvestigationAgent:
    """Factory: LangGraph agent if available, else deterministic fallback."""
    resolved = settings or get_settings()
    if LANGGRAPH_AVAILABLE:
        return LangGraphInvestigationAgent(resolved)
    return DeterministicInvestigationAgent(resolved)
