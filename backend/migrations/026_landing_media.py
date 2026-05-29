"""Migration 026 — landing page media (images, posters, banners)."""
from backend.core.db import execute


def run():
    execute("""
        CREATE TABLE IF NOT EXISTS landing_media (
            id          SERIAL PRIMARY KEY,
            filename    TEXT    NOT NULL,
            title       TEXT,
            description TEXT,
            media_type  TEXT    NOT NULL DEFAULT 'poster',
            sort_order  INTEGER NOT NULL DEFAULT 0,
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT NOW()::text,
            uploaded_by INTEGER
        )
    """)
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_lmedia_active ON landing_media(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_lmedia_type   ON landing_media(media_type)",
        "CREATE INDEX IF NOT EXISTS idx_lmedia_sort   ON landing_media(sort_order)",
    ]:
        try:
            execute(idx)
        except Exception:
            pass
