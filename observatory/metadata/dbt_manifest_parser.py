"""Parse dbt manifest.json for model metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_models(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = manifest.get("nodes", {})
    models = []
    for key, node in nodes.items():
        if not key.startswith("model."):
            continue
        layer = _infer_layer(node.get("name", ""))
        columns = [
            {"name": col_name, "description": col.get("description", "")}
            for col_name, col in node.get("columns", {}).items()
        ]
        models.append({
            "model_name": node.get("name", ""),
            "layer": layer,
            "description": node.get("description") or node.get("meta", {}).get("description", ""),
            "owner": "data_engineering",
            "columns": columns,
            "tests": _extract_tests(node),
            "row_count": None,
            "last_updated_at": node.get("created_at"),
        })
    return models


def _infer_layer(name: str) -> str:
    if name.startswith("stg_"):
        return "staging"
    if name.startswith("int_"):
        return "intermediate"
    if name.startswith("mart_"):
        return "mart"
    return "other"


def _extract_tests(node: dict[str, Any]) -> list[str]:
    tests = []
    for col_name, col in node.get("columns", {}).items():
        for test in col.get("tests", []) or []:
            if isinstance(test, str):
                tests.append(f"{col_name}:{test}")
            elif isinstance(test, dict):
                tests.append(f"{col_name}:{list(test.keys())[0]}")
    return tests


def find_manifest(project_root: Path) -> Optional[Path]:
    candidates = [
        project_root / "dbt_project" / "target" / "manifest.json",
        project_root / "target" / "manifest.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None
