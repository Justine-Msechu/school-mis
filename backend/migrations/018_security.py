"""
Migration 018 — Security hardening + SaaS foundations.

Changes:
  schools           — new table: one row per school tenant
  users             — add school_id, pw_scheme columns
  login_sessions    — add token_hash, school_id, last_used_at, is_active columns
                      (token_hash stores SHA-256 of the raw token, NOT the raw token)
  rate_limit_log    — per-user per-endpoint request counts for rate limiting
"""


def run():
    import sqlite3, os

    def _apply(conn):
        # ── schools (SaaS tenant registry) ──────────────────────────────────
        conn.execute("""
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

        # Upgrade existing schools table if columns missing
        sc_cols = {r[1] for r in conn.execute("PRAGMA table_info(schools)").fetchall()}
        if "subscription_status" not in sc_cols:
            conn.execute("ALTER TABLE schools ADD COLUMN subscription_status TEXT DEFAULT 'trial'")
        if "trial_ends" not in sc_cols:
            conn.execute("ALTER TABLE schools ADD COLUMN trial_ends TEXT")

        # ── users: school_id + pw_scheme ────────────────────────────────────
        u_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "school_id" not in u_cols:
            conn.execute("ALTER TABLE users ADD COLUMN school_id INTEGER REFERENCES schools(id)")
        if "pw_scheme" not in u_cols:
            # sha256 = legacy; bcrypt = new
            conn.execute("ALTER TABLE users ADD COLUMN pw_scheme TEXT DEFAULT 'sha256'")

        # ── login_sessions: extend for DB-backed tokens ──────────────────────
        s_cols = {r[1] for r in conn.execute("PRAGMA table_info(login_sessions)").fetchall()}
        if "token_hash" not in s_cols:
            conn.execute("ALTER TABLE login_sessions ADD COLUMN token_hash TEXT")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_token_hash ON login_sessions(token_hash)")
        if "school_id" not in s_cols:
            conn.execute("ALTER TABLE login_sessions ADD COLUMN school_id INTEGER")
        if "last_used_at" not in s_cols:
            conn.execute("ALTER TABLE login_sessions ADD COLUMN last_used_at TEXT DEFAULT (datetime('now'))")
        if "is_active" not in s_cols:
            conn.execute("ALTER TABLE login_sessions ADD COLUMN is_active INTEGER DEFAULT 1")
        # Invalidate any old in-memory-style sessions (session_token without hash)
        conn.execute("UPDATE login_sessions SET is_active=0 WHERE token_hash IS NULL")

        # ── rate_limit_log ───────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                school_id   INTEGER,
                endpoint    TEXT    NOT NULL DEFAULT 'api',
                ts          REAL    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rll_user_ts ON rate_limit_log(user_id, ts)"
        )

        conn.commit()

    # Apply to both DB paths
    from backend.core.db import _get_conn
    _apply(_get_conn())

    prod = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "school_mis.db")
    )
    if os.path.exists(prod):
        c2 = sqlite3.connect(prod)
        _apply(c2)
        c2.close()
