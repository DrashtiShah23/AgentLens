from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import duckdb

from observatory.config.settings import Settings, get_settings


class DuckDBConnection:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.database_path), read_only=read_only)


def get_connection(settings: Optional[Settings] = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    s = settings or get_settings()
    path = s.resolve_path(s.warehouse_path)
    return DuckDBConnection(path).connect(read_only=read_only)


@contextmanager
def connection_context(settings: Optional[Settings] = None, read_only: bool = False
                       ) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = get_connection(settings, read_only)
    try:
        yield conn
    finally:
        conn.close()
