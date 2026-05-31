MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS contact_inquiries (
        id         SERIAL PRIMARY KEY,
        name       TEXT NOT NULL,
        email      TEXT NOT NULL,
        phone      TEXT,
        school     TEXT,
        message    TEXT NOT NULL,
        status     TEXT NOT NULL DEFAULT 'new',
        created_at TEXT NOT NULL DEFAULT NOW()::text
    )""",
    "CREATE INDEX IF NOT EXISTS idx_inquiries_status ON contact_inquiries(status, created_at)",
]
