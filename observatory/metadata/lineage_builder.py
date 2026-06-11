"""Build lineage graph from dbt manifest."""

from __future__ import annotations

from typing import Any


def build_lineage_edges(manifest: dict[str, Any]) -> list[dict[str, str]]:
    nodes = manifest.get("nodes", {})
    edges: list[dict[str, str]] = []
    for key, node in nodes.items():
        if not key.startswith("model."):
            continue
        downstream = node.get("name", "")
        for parent in node.get("depends_on", {}).get("nodes", []):
            if not parent.startswith("model."):
                continue
            upstream = parent.split(".")[-1]
            edges.append({
                "upstream": upstream,
                "downstream": downstream,
                "transformation_type": _infer_transform(downstream),
                "description": f"{upstream} feeds {downstream}",
            })
    return edges


def _infer_transform(model_name: str) -> str:
    if model_name.startswith("stg_"):
        return "clean_and_cast"
    if model_name.startswith("int_"):
        return "join_and_aggregate"
    if model_name.startswith("mart_"):
        return "aggregate_for_analytics"
    return "transform"
