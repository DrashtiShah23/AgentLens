from typing import Any, Optional

from observatory.config.settings import Settings, get_settings
from observatory.warehouse.duckdb_connection import connection_context


def count_table(table: str, settings: Optional[Settings] = None) -> int:
    with connection_context(settings) as conn:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0]) if row else 0


def get_ingestion_audit(settings: Optional[Settings] = None) -> list[dict[str, Any]]:
    with connection_context(settings) as conn:
        df = conn.execute(
            "SELECT * FROM ingestion_audit ORDER BY processed_at DESC"
        ).fetchdf()
        return df.to_dict(orient="records")
