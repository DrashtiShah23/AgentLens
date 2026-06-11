"""Write validated agent runs to raw log directory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.api.schemas.agent_run import AgentRun
from observatory.config.settings import Settings, get_settings
from observatory.ingestion.schema_validator import validate_record


class LogWriter:
    """Persist validated run payloads as JSON files."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.raw_dir = self.settings.resolve_path(self.settings.raw_log_dir)

    def write_run(self, payload: dict[str, Any]) -> AgentRun:
        outcome = validate_record(payload, AgentRun)
        if not outcome.valid:
            raise ValueError(outcome.rejection_reason or "validation failed")
        assert outcome.model is not None
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.raw_dir / f"api_run_{ts}_{outcome.model.run_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(outcome.model.model_dump(mode="json"), handle, indent=2)
        return outcome.model
