"""
Migration 016 — Student background & sponsorship detail columns.

Adds to students:
  sponsorship_type     — none | ngo | individual
  sponsor_ngo_id       — FK to ngos (for ngo-sponsored students)
  sponsor_name         — individual sponsor full name
  sponsor_phone        — individual sponsor phone
  sponsor_relationship — e.g. uncle, church, employer
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    cols = {row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()}

    if "student_type" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN student_type TEXT DEFAULT 'Day'")
    if "sponsorship_type" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN sponsorship_type TEXT DEFAULT 'none'")
    if "sponsor_ngo_id" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN sponsor_ngo_id INTEGER")
    if "sponsor_name" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN sponsor_name TEXT")
    if "sponsor_phone" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN sponsor_phone TEXT")
    if "sponsor_relationship" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN sponsor_relationship TEXT")

    conn.commit()
