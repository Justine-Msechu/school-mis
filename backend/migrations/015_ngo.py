"""
Migration 015 — NGO / Sponsorship tables.

Creates:
  ngos                  — partner organisations supporting vulnerable students
  student_sponsorships  — links students to NGOs with support type details
  permissions           — ngo.view, ngo.manage
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ngos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL UNIQUE,
            contact_person TEXT,
            phone          TEXT,
            email          TEXT,
            address        TEXT,
            website        TEXT,
            notes          TEXT,
            is_active      INTEGER DEFAULT 1,
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS student_sponsorships (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL REFERENCES students(id),
            ngo_id        INTEGER NOT NULL REFERENCES ngos(id),
            support_types TEXT DEFAULT '',
            fee_amount    REAL DEFAULT 0,
            start_date    TEXT,
            end_date      TEXT,
            notes         TEXT,
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now')),
            UNIQUE(student_id, ngo_id)
        )
    """)

    for code, domain, action, description in [
        ("ngo.view",   "ngo", "view",   "View NGO partners and beneficiary lists"),
        ("ngo.manage", "ngo", "manage", "Create and edit NGO partners and sponsorships"),
    ]:
        conn.execute(
            """INSERT OR IGNORE INTO permissions (code, domain, action, description, scope_type)
               VALUES (?,?,?,?,'global')""",
            (code, domain, action, description),
        )

    conn.commit()
