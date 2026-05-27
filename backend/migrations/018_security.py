"""
Migration 018 — Security hardening + SaaS foundations.

Changes:
  schools        — new table: one row per school tenant
  users          — add school_id, pw_scheme columns
  login_sessions — add token_hash, school_id, last_used_at, is_active
  rate_limit_log — per-user per-endpoint request counts
"""

from backend.core.db import execute, fetch_all


def run():
    # ── schools (SaaS tenant registry) ──────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS schools (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL UNIQUE,
            subdomain           TEXT    UNIQUE,
            plan                TEXT    DEFAULT 'trial',
            max_users           INTEGER DEFAULT 50,
            is_active           INTEGER DEFAULT 1,
            created_at          TEXT,
            notes               TEXT,
            subscription_status TEXT    DEFAULT 'trial',
            trial_ends          TEXT
        )
    """)

    # Upgrade schools if columns are missing
    sc_cols = {r["name"] for r in fetch_all("PRAGMA table_info(schools)", ())}
    for col, defn in [
        ("subscription_status", "TEXT DEFAULT 'trial'"),
        ("trial_ends",          "TEXT"),
    ]:
        if col not in sc_cols:
            try:
                execute(f"ALTER TABLE schools ADD COLUMN {col} {defn}")
            except Exception:
                pass

    # ── users: school_id + pw_scheme ────────────────────────────────────────
    u_cols = {r["name"] for r in fetch_all("PRAGMA table_info(users)", ())}
    for col, defn in [
        ("school_id", "INTEGER REFERENCES schools(id)"),
        ("pw_scheme",  "TEXT DEFAULT 'sha256'"),
    ]:
        if col not in u_cols:
            try:
                execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
            except Exception:
                pass

    # ── login_sessions: extend for DB-backed tokens ──────────────────────────
    s_cols = {r["name"] for r in fetch_all("PRAGMA table_info(login_sessions)", ())}
    for col, defn in [
        ("token_hash",   "TEXT"),
        ("school_id",    "INTEGER"),
        ("last_used_at", "TEXT DEFAULT (datetime('now'))"),
        ("is_active",    "INTEGER DEFAULT 1"),
    ]:
        if col not in s_cols:
            try:
                execute(f"ALTER TABLE login_sessions ADD COLUMN {col} {defn}")
            except Exception:
                pass

    try:
        execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_token_hash ON login_sessions(token_hash)")
    except Exception:
        pass

    try:
        execute("UPDATE login_sessions SET is_active=0 WHERE token_hash IS NULL")
    except Exception:
        pass

    # ── rate_limit_log ───────────────────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS rate_limit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            school_id INTEGER,
            endpoint  TEXT    NOT NULL DEFAULT 'api',
            ts        REAL    NOT NULL
        )
    """)

    try:
        execute("CREATE INDEX IF NOT EXISTS idx_rll_user_ts ON rate_limit_log(user_id, ts)")
    except Exception:
        pass
