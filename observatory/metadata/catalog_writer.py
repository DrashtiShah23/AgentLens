"""Write catalog.json with atomic replace semantics."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from observatory.config.settings import Settings, get_settings
from observatory.metadata.dbt_manifest_parser import extract_models, find_manifest, load_manifest
from observatory.metadata.lineage_builder import build_lineage_edges
from observatory.warehouse.duckdb_connection import connection_context


class CatalogWriter:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.metadata_dir = self.settings.resolve_path(self.settings.metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def refresh(self) -> tuple[Path, Path]:
        manifest_path = find_manifest(self.settings.project_root())
        if manifest_path is None:
            raise FileNotFoundError(
                "dbt manifest.json not found. Run: dbt run --project-dir dbt_project"
            )
        manifest = load_manifest(manifest_path)
        models = extract_models(manifest)
        models = self._enrich_row_counts(models)
        edges = build_lineage_edges(manifest)

        catalog = {"models": models, "generated_at": datetime.now(timezone.utc).isoformat()}
        lineage = {"edges": edges, "generated_at": datetime.now(timezone.utc).isoformat()}

        catalog_path = self._atomic_write("catalog.json", catalog)
        lineage_path = self._atomic_write("lineage.json", lineage)
        return catalog_path, lineage_path

    def _enrich_row_counts(self, models: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.settings.resolve_path(self.settings.warehouse_path).exists():
            return models
        try:
            with connection_context(self.settings, read_only=True) as conn:
                for model in models:
                    name = model["model_name"]
                    try:
                        row = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()
                        model["row_count"] = int(row[0]) if row else 0
                    except Exception:
                        model["row_count"] = None
                    model["last_updated_at"] = datetime.now(timezone.utc).isoformat()
        except Exception:
            pass
        return models

    def _atomic_write(self, filename: str, payload: dict[str, Any]) -> Path:
        final_path = self.metadata_dir / filename
        temp_path = self.metadata_dir / f".{filename}.tmp"
        backup_path = self.metadata_dir / f".{filename}.bak"
        try:
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            json.loads(temp_path.read_text())
            if final_path.exists():
                shutil.copy2(final_path, backup_path)
            temp_path.replace(final_path)
            return final_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            if backup_path.exists() and not final_path.exists():
                shutil.copy2(backup_path, final_path)
            raise
