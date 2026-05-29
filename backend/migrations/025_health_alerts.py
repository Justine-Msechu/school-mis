"""Migration 025 — platform health alerts table."""
from backend.core.db import execute


def run():
    execute("""
        CREATE TABLE IF NOT EXISTS platform_health_alerts (
            id            SERIAL PRIMARY KEY,
            ts            TEXT    NOT NULL DEFAULT NOW()::text,
            metric        TEXT    NOT NULL,
            level         TEXT    NOT NULL DEFAULT 'warning',
            value         REAL,
            threshold     REAL,
            message       TEXT    NOT NULL,
            resolved      INTEGER NOT NULL DEFAULT 0,
            resolved_at   TEXT,
            auto_resolved INTEGER NOT NULL DEFAULT 0
        )
    """)
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_halerts_metric   ON platform_health_alerts(metric)",
        "CREATE INDEX IF NOT EXISTS idx_halerts_resolved ON platform_health_alerts(resolved)",
        "CREATE INDEX IF NOT EXISTS idx_halerts_ts       ON platform_health_alerts(ts DESC)",
    ]:
        try:
            execute(idx)
        except Exception:
            pass
