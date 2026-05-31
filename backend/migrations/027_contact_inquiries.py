"""Migration 027 — contact inquiries from landing page form."""
from backend.core.db import execute


def run():
    execute("""
        CREATE TABLE IF NOT EXISTS contact_inquiries (
            id         SERIAL PRIMARY KEY,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL,
            phone      TEXT,
            school     TEXT,
            message    TEXT NOT NULL,
            status     TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL DEFAULT NOW()::text
        )
    """)
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_inquiries_status ON contact_inquiries(status, created_at)",
    ]:
        try:
            execute(idx)
        except Exception:
            pass
