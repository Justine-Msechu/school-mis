"""
PostgreSQL connection pool for the FastAPI backend.

Provides fetch_one, fetch_all, execute, execute_many with:
  - ThreadedConnectionPool (psycopg2) — up to 20 connections
  - Auto-conversion layer: SQLite-flavoured SQL → PostgreSQL SQL
    Handles: ? placeholders, INSERT OR IGNORE/REPLACE, datetime('now'),
             AUTOINCREMENT, PRAGMA table_info, randomblob, IFNULL, etc.
"""

from __future__ import annotations
import os, re, logging
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://school_mis:school_mis@localhost:5432/school_mis",
)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _init_pool() -> None:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(2, 20, dsn=DATABASE_URL)
        log.info("PostgreSQL connection pool ready (max=20, url=%s)", DATABASE_URL.split("@")[-1])


def _get_conn():
    if _pool is None:
        _init_pool()
    return _pool.getconn()  # type: ignore[union-attr]


def _put_conn(conn, *, close: bool = False) -> None:
    if _pool:
        _pool.putconn(conn, close=close)


# ── SQL compatibility layer ────────────────────────────────────────────────────

_PRAGMA_TABLE_INFO = re.compile(
    r"^\s*PRAGMA\s+table_info\s*\(\s*['\"]?(\w+)['\"]?\s*\)\s*$", re.I
)
_PRAGMA = re.compile(r"^\s*PRAGMA\s", re.I)
_INSERT_OR = re.compile(r"\bINSERT\s+OR\s+(?:IGNORE|REPLACE)\s+INTO\b", re.I)
# datetime('now') and datetime('now', '+N unit') — captures optional quoted modifier
_DATETIME_NOW = re.compile(r"datetime\(\s*'now'\s*(?:,\s*'([^']*)'\s*)?\)", re.I)
# date('now') and date('now', '+N unit')
_DATE_NOW = re.compile(r"\bdate\(\s*'now'\s*(?:,\s*'([^']*)'\s*)?\)", re.I)
# sqlite_master table-existence check → information_schema equivalent
_SQLITE_MASTER = re.compile(
    r"SELECT\s+\w+\s+FROM\s+sqlite_master\s+WHERE\s+type\s*=\s*'table'\s+AND\s+name\s*=\s*'(\w+)'",
    re.I,
)
_INT_PK_AI = re.compile(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", re.I)
_INT_PK = re.compile(r"\bINTEGER\s+PRIMARY\s+KEY\b(?!\s*,)", re.I)
_RAND_BLOB_LOWER = re.compile(
    r"lower\s*\(\s*hex\s*\(\s*randomblob\s*\([^)]+\)\s*\)\s*\)", re.I
)
_RAND_BLOB_HEX = re.compile(r"hex\s*\(\s*randomblob\s*\([^)]+\)\s*\)", re.I)
_IFNULL = re.compile(r"\bIFNULL\s*\(", re.I)
_GROUP_CONCAT = re.compile(r"\bGROUP_CONCAT\s*\(", re.I)

# strftime with 'now' (positional — must run before the general strftime rule)
_STRFTIME_NOW = re.compile(r"strftime\s*\(\s*'([^']+)'\s*,\s*'now'\s*\)", re.I)
# general strftime(fmt, col) — col can contain nested parens up to depth 1
_STRFTIME_COL = re.compile(
    r"strftime\s*\(\s*'([^']+)'\s*,\s*([^)(]+(?:\([^)]*\))?[^)(]*)\s*\)", re.I
)

_STRFTIME_FMT_MAP = {
    "%Y-%m-%d": "YYYY-MM-DD",
    "%Y-%m":    "YYYY-MM",
    "%Y":       "YYYY",
    "%m":       "MM",
    "%d":       "DD",
    "%H:%M:%S": "HH24:MI:SS",
    "%Y-W%W":   'IYYY-"W"IW',
    "%d %b":    "DD Mon",
}


_INTERVAL_PAT = re.compile(r'^([+-]?)(\d+)\s+(\w+)$')


def _datetime_now_sub(m: re.Match) -> str:
    """Convert datetime('now', '+/-N unit') → PostgreSQL NOW() expression."""
    mod = (m.group(1) or "").strip()
    if mod:
        mm = _INTERVAL_PAT.match(mod)
        if mm:
            sign, n, unit = mm.group(1) or '+', int(mm.group(2)), mm.group(3)
            op = '-' if sign == '-' else '+'
            return f"(NOW() {op} INTERVAL '{n} {unit}')::text"
    return "NOW()::text"


def _date_now_sub(m: re.Match) -> str:
    """Convert date('now', '+/-N unit') → PostgreSQL CURRENT_DATE expression."""
    mod = (m.group(1) or "").strip()
    if mod:
        mm = _INTERVAL_PAT.match(mod)
        if mm:
            sign, n, unit = mm.group(1) or '+', int(mm.group(2)), mm.group(3)
            op = '-' if sign == '-' else '+'
            return f"(CURRENT_DATE {op} INTERVAL '{n} {unit}')::text"
    return "CURRENT_DATE::text"


def _sqlite_master_sub(m: re.Match) -> str:
    tbl = m.group(1)
    return (
        f"SELECT table_name AS name FROM information_schema.tables "
        f"WHERE table_type='BASE TABLE' AND table_schema='public' AND table_name='{tbl}'"
    )


def _strftime_now_sub(m: re.Match) -> str:
    fmt = _STRFTIME_FMT_MAP.get(m.group(1))
    if fmt:
        return f"TO_CHAR(CURRENT_DATE, '{fmt}')"
    return "CURRENT_DATE::text"


def _strftime_col_sub(m: re.Match) -> str:
    fmt = _STRFTIME_FMT_MAP.get(m.group(1))
    col = m.group(2).strip()
    if fmt:
        return f"TO_CHAR({col}::timestamp, '{fmt}')"
    # Fallback: best-effort SQLite → PG format replacement
    pg_fmt = (m.group(1)
              .replace("%Y", "YYYY").replace("%m", "MM").replace("%d", "DD")
              .replace("%H", "HH24").replace("%M", "MI").replace("%S", "SS"))
    return f"TO_CHAR({col}::timestamp, '{pg_fmt}')"


def _adapt(sql: str) -> tuple[str, bool]:
    """
    Auto-convert SQLite SQL to PostgreSQL SQL.
    Returns (pg_sql, added_on_conflict).
    """
    # PRAGMA table_info(t) → information_schema query
    m = _PRAGMA_TABLE_INFO.match(sql)
    if m:
        tbl = m.group(1)
        return (
            f"SELECT column_name AS name FROM information_schema.columns "
            f"WHERE table_name='{tbl}' AND table_schema='public'",
            False,
        )

    # Other PRAGMA → no-op SELECT
    if _PRAGMA.match(sql):
        return "SELECT 1 AS dummy", False

    has_or_conflict = bool(_INSERT_OR.search(sql))

    # ? → %s
    sql = sql.replace("?", "%s")

    # INSERT OR IGNORE/REPLACE INTO → INSERT INTO
    sql = _INSERT_OR.sub("INSERT INTO", sql)

    # sqlite_master table-check → information_schema
    sql = _SQLITE_MASTER.sub(_sqlite_master_sub, sql)

    # Datetime functions (handles both bare and modifier forms)
    sql = _DATETIME_NOW.sub(_datetime_now_sub, sql)
    sql = _DATE_NOW.sub(_date_now_sub, sql)

    # Dynamic date: date('now', %s || ' months') → CURRENT_DATE + (%s || ' months')::interval
    # (runs after ?→%s so the placeholder is already %s)
    sql = re.sub(
        r"\bdate\('now',\s*%s\s*\|\|\s*'([^']*)'\s*\)",
        lambda m: f"(CURRENT_DATE + (%s || '{m.group(1)}')::interval)",
        sql, flags=re.I,
    )
    # strftime with 'now' → TO_CHAR(CURRENT_DATE, ...) — must run before general strftime
    sql = _STRFTIME_NOW.sub(_strftime_now_sub, sql)
    # strftime with a column reference → TO_CHAR(col::timestamp, ...)
    sql = _STRFTIME_COL.sub(_strftime_col_sub, sql)

    # DDL: AUTOINCREMENT → SERIAL
    sql = _INT_PK_AI.sub("SERIAL PRIMARY KEY", sql)
    sql = _INT_PK.sub("SERIAL PRIMARY KEY", sql)

    # DDL: SQLite random UUID → PostgreSQL
    sql = _RAND_BLOB_LOWER.sub("gen_random_uuid()::text", sql)
    sql = _RAND_BLOB_HEX.sub("encode(gen_random_bytes(16),'hex')", sql)

    # Function aliases
    sql = _IFNULL.sub("COALESCE(", sql)
    sql = _GROUP_CONCAT.sub("STRING_AGG(", sql)

    if has_or_conflict:
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    return sql, has_or_conflict


# ── Public API ─────────────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency — returns pool reference for compatibility."""
    return _pool


@contextmanager
def transaction():
    """Atomic write block. Rolls back on any exception."""
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _put_conn(conn)


def fetch_one(sql: str, params: Any = (), conn=None) -> dict | None:
    adapted, _ = _adapt(sql)
    own = conn is None
    c = conn or _get_conn()
    try:
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(adapted, params or ())
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception:
        if own:
            try:
                c.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            _put_conn(c)


def fetch_all(sql: str, params: Any = (), conn=None) -> list[dict]:
    adapted, _ = _adapt(sql)
    own = conn is None
    c = conn or _get_conn()
    try:
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(adapted, params or ())
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        if own:
            try:
                c.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            _put_conn(c)


def execute(sql: str, params: Any = (), conn=None) -> int:
    """Execute a write statement. Returns the inserted row id (or 0)."""
    adapted, _ = _adapt(sql)
    own = conn is None
    c = conn or _get_conn()
    is_insert = bool(re.match(r"\s*INSERT\s", adapted, re.I))
    try:
        with c.cursor() as cur:
            if is_insert and "RETURNING" not in adapted.upper():
                # Try with RETURNING id; fall back if table has no 'id' column
                try:
                    cur.execute("SAVEPOINT _ex")
                    cur.execute(adapted.rstrip().rstrip(";") + " RETURNING id", params or ())
                    row = cur.fetchone()
                    cur.execute("RELEASE SAVEPOINT _ex")
                    c.commit()
                    return row[0] if row else 0
                except psycopg2.Error:
                    cur.execute("ROLLBACK TO SAVEPOINT _ex")
                    cur.execute("RELEASE SAVEPOINT _ex")
                    cur.execute(adapted, params or ())
                    c.commit()
                    return 0
            else:
                cur.execute(adapted, params or ())
                c.commit()
                return 0
    except Exception:
        try:
            c.rollback()
        except Exception:
            pass
        raise
    finally:
        if own:
            _put_conn(c)


def execute_many(sql: str, params_list: list, conn=None) -> int:
    adapted, _ = _adapt(sql)
    own = conn is None
    c = conn or _get_conn()
    try:
        with c.cursor() as cur:
            cur.executemany(adapted, params_list)
            c.commit()
            return cur.rowcount
    except Exception:
        c.rollback()
        raise
    finally:
        if own:
            _put_conn(c)


def row_to_dict(row: dict | None) -> dict | None:
    return row


def rows_to_dicts(rows: list[dict]) -> list[dict]:
    return rows
