"""
Thread-safe SQLite connection management for the FastAPI backend.

Uses thread-local connections to avoid sharing a single connection across
async workers. Each request gets its own connection; it's closed after the
request completes via the FastAPI dependency.

All write operations that need atomicity should use the transaction() context manager.
"""

from __future__ import annotations
import sqlite3
import threading
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Path to the shared database file (overridable via env var for Docker)
import os as _os
DB_PATH = Path(_os.environ.get(
    "SCHOOL_MIS_DB_PATH",
    str(Path(__file__).parent.parent.parent / "school_mis.db"),
))

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return the thread-local connection, creating it if needed."""
    if not getattr(_local, "conn", None):
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        # Performance and integrity pragmas
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA cache_size=-32000")   # 32 MB
        conn.execute("PRAGMA temp_store=MEMORY")
        _local.conn = conn
    return _local.conn


def get_db() -> sqlite3.Connection:
    """FastAPI dependency: return a connection for the current request thread."""
    return _get_conn()


@contextmanager
def transaction(conn: sqlite3.Connection | None = None):
    """Context manager for atomic writes. Rolls back on any exception."""
    c = conn or _get_conn()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise


def fetch_one(sql: str, params: Any = (), conn: sqlite3.Connection | None = None) -> sqlite3.Row | None:
    c = conn or _get_conn()
    cur = c.execute(sql, params)
    return cur.fetchone()


def fetch_all(sql: str, params: Any = (), conn: sqlite3.Connection | None = None) -> list[sqlite3.Row]:
    c = conn or _get_conn()
    cur = c.execute(sql, params)
    return cur.fetchall()


def execute(sql: str, params: Any = (), conn: sqlite3.Connection | None = None) -> int:
    """Execute a single write statement. Returns lastrowid."""
    c = conn or _get_conn()
    cur = c.execute(sql, params)
    c.commit()
    return cur.lastrowid


def execute_many(sql: str, params_list: list, conn: sqlite3.Connection | None = None) -> int:
    """Execute a write statement for each param set in a single transaction."""
    c = conn or _get_conn()
    cur = c.executemany(sql, params_list)
    c.commit()
    return cur.rowcount


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]
