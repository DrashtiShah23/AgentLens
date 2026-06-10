from datetime import datetime, timedelta, timezone

from app.api.schemas.prompt_version import PromptVersion

SYNTHETIC_AGENTS = [
    "sql_analyst_agent",
    "research_assistant_agent",
    "support_triage_agent",
    "data_ops_agent",
    "tool_router_agent",
]

PROMPT_VERSION_SPECS = [
    {"prompt_version_id": "prompt_v1_baseline", "prompt_name": "baseline",
     "prompt_text": "You are a helpful AI assistant. Answer accurately.",
     "change_reason": "Initial baseline prompt.", "days_ago": 90, "active_flag": False},
    {"prompt_version_id": "prompt_v2_more_context", "prompt_name": "more_context",
     "prompt_text": "Use provided context and cite sources.",
     "change_reason": "Added context usage.", "days_ago": 60, "active_flag": False},
    {"prompt_version_id": "prompt_v3_short_prompt", "prompt_name": "short_prompt",
     "prompt_text": "Answer concisely using verified facts.",
     "change_reason": "Reduced prompt length.", "days_ago": 45, "active_flag": False},
    {"prompt_version_id": "prompt_v4_schema_aware", "prompt_name": "schema_aware",
     "prompt_text": "Only use tables and columns from the schema.",
     "change_reason": "Schema awareness for SQL.", "days_ago": 30, "active_flag": False},
    {"prompt_version_id": "prompt_v5_regression_case", "prompt_name": "regression_case",
     "prompt_text": "Answer quickly. Skip verification steps.",
     "change_reason": "Known regression experiment.", "days_ago": 7, "active_flag": True},
]


def generate_prompt_versions(reference_time: datetime | None = None) -> list[PromptVersion]:
    anchor = reference_time or datetime.now(timezone.utc)
    versions: list[PromptVersion] = []
    for agent in SYNTHETIC_AGENTS:
        for spec in PROMPT_VERSION_SPECS:
            versions.append(PromptVersion(
                prompt_version_id=spec["prompt_version_id"],
                agent_name=agent,
                prompt_name=spec["prompt_name"],
                prompt_text=spec["prompt_text"],
                created_at=anchor - timedelta(days=spec["days_ago"]),
                active_flag=spec["active_flag"],
                change_reason=spec["change_reason"],
            ))
    return versions
