"""Migration 023 — centralised error log table."""
from backend.core.db import execute


def run():
    execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id           SERIAL PRIMARY KEY,
            ts           TEXT    NOT NULL DEFAULT NOW()::text,
            source       TEXT    NOT NULL DEFAULT 'backend',
            level        TEXT    NOT NULL DEFAULT 'error',
            path         TEXT,
            method       TEXT,
            user_id      INTEGER,
            school_id    INTEGER,
            role         TEXT,
            error_type   TEXT,
            message      TEXT    NOT NULL,
            stack        TEXT,
            context      TEXT,
            resolved     INTEGER NOT NULL DEFAULT 0,
            resolved_at  TEXT,
            resolved_by  INTEGER
        )
    """)
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_errlogs_ts     ON error_logs(ts DESC)",
        "CREATE INDEX IF NOT EXISTS idx_errlogs_source ON error_logs(source)",
        "CREATE INDEX IF NOT EXISTS idx_errlogs_level  ON error_logs(level)",
        "CREATE INDEX IF NOT EXISTS idx_errlogs_res    ON error_logs(resolved)",
    ]:
        try:
            execute(idx)
        except Exception:
            pass
