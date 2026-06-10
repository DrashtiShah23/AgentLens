"""Read raw JSON log files."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from observatory.utils.file_utils import is_empty_file


@dataclass
class JsonFileReadResult:
    path: Path
    records: list[dict[str, Any]] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    is_empty: bool = False
    already_processed: bool = False


def read_json_file(path: Path) -> JsonFileReadResult:
    result = JsonFileReadResult(path=path)
    if is_empty_file(path):
        result.is_empty = True
        return result
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        result.parse_errors.append(f"JSON parse error: {exc}")
        return result
    if isinstance(payload, list):
        result.records = payload
    elif isinstance(payload, dict):
        if "records" in payload:
            result.records = payload["records"]
        else:
            result.records = [payload]
    else:
        result.parse_errors.append(f"unexpected JSON type: {type(payload).__name__}")
    return result
