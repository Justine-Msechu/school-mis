"""
BaseRepository — generic CRUD with soft-delete support.

Works in both SQLite (desktop) and PostgreSQL (server) modes by delegating
all queries to the database.db helpers rather than using the raw connection.
The `conn` parameter is kept for API compatibility but is not used.
"""

from __future__ import annotations
from typing import Any
from backend.core.exceptions import NotFoundError


class BaseRepository:
    table: str = ""
    pk: str = "id"

    def __init__(self, conn=None):
        self.conn = conn  # kept for API compatibility; not used directly

    def _q(self, sql: str, params: Any = ()) -> list[dict]:
        from database.db import fetch_all
        rows = fetch_all(sql, params)
        return [dict(r) for r in rows] if rows else []

    def _one(self, sql: str, params: Any = ()) -> dict | None:
        from database.db import fetch_one
        r = fetch_one(sql, params)
        return dict(r) if r else None

    def _exec(self, sql: str, params: Any = ()) -> int:
        from database.db import execute
        result = execute(sql, params)
        return result or 0

    def get(self, id: int) -> dict | None:
        return self._one(
            f"SELECT * FROM {self.table} WHERE {self.pk}=? AND (deleted_at IS NULL OR deleted_at='')",
            (id,),
        )

    def get_or_raise(self, id: int) -> dict:
        obj = self.get(id)
        if obj is None:
            raise NotFoundError(self.table, id)
        return obj

    def get_raw(self, id: int) -> dict | None:
        """Get including soft-deleted rows."""
        return self._one(f"SELECT * FROM {self.table} WHERE {self.pk}=?", (id,))

    def list(
        self,
        where: str = "1=1",
        params: Any = (),
        order: str = "id DESC",
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        sql = (
            f"SELECT * FROM {self.table} "
            f"WHERE (deleted_at IS NULL OR deleted_at='') AND ({where}) "
            f"ORDER BY {order} LIMIT ? OFFSET ?"
        )
        return self._q(sql, list(params) + [limit, offset])

    def count(self, where: str = "1=1", params: Any = ()) -> int:
        row = self._one(
            f"SELECT COUNT(*) as n FROM {self.table} "
            f"WHERE (deleted_at IS NULL OR deleted_at='') AND ({where})",
            params,
        )
        return row["n"] if row else 0

    def soft_delete(self, id: int, actor_id: int | None = None) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            f"UPDATE {self.table} SET deleted_at=? WHERE {self.pk}=?",
            (now, id),
        )

    def exists(self, id: int) -> bool:
        return self.get(id) is not None
