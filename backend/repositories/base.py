"""
BaseRepository — generic CRUD with soft-delete support.

All domain repositories inherit from this class.
The `conn` parameter is the thread-local SQLite connection from backend.core.db.
"""

from __future__ import annotations
import sqlite3
from typing import Any
from backend.core.exceptions import NotFoundError


class BaseRepository:
    table: str = ""
    pk: str = "id"

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _q(self, sql: str, params: Any = ()) -> list[dict]:
        cur = self.conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def _one(self, sql: str, params: Any = ()) -> dict | None:
        cur = self.conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def _exec(self, sql: str, params: Any = ()) -> int:
        cur = self.conn.execute(sql, params)
        return cur.lastrowid or 0

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
