"""Migration 024 — add request_id to error_logs for request tracing."""
from backend.core.db import execute


def run():
    try:
        execute("ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS request_id VARCHAR(64)", ())
    except Exception:
        pass
    try:
        execute(
            "CREATE INDEX IF NOT EXISTS idx_errlogs_rid ON error_logs(request_id)",
            (),
        )
    except Exception:
        pass
