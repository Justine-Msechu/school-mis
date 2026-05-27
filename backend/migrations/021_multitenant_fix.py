"""
Migration 021 — Multi-tenant fixes for school_config and academic_years.

school_config:  Recreate with composite UNIQUE(key, school_id) so each school
                has its own isolated configuration.
academic_years: Add school_id column so each school manages its own calendar.
"""


def run():
    from backend.core.db import execute, fetch_all, fetch_one

    # ── school_config: add school_id and rebuild with composite unique ─────────
    sc_cols = {r["name"] for r in fetch_all("PRAGMA table_info(school_config)", ())}
    if "school_id" not in sc_cols:
        first = fetch_one("SELECT id FROM schools ORDER BY id LIMIT 1", ())
        sid   = first["id"] if first else None

        execute("""
            CREATE TABLE school_config_new (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                key       TEXT NOT NULL,
                value     TEXT,
                school_id INTEGER REFERENCES schools(id),
                UNIQUE(key, school_id)
            )
        """, ())
        execute(
            "INSERT INTO school_config_new (key, value, school_id) "
            "SELECT key, value, ? FROM school_config",
            (sid,),
        )
        execute("DROP TABLE school_config", ())
        execute("ALTER TABLE school_config_new RENAME TO school_config", ())

    # ── academic_years: add school_id column ──────────────────────────────────
    ay_cols = {r["name"] for r in fetch_all("PRAGMA table_info(academic_years)", ())}
    if "school_id" not in ay_cols:
        execute(
            "ALTER TABLE academic_years ADD COLUMN school_id INTEGER REFERENCES schools(id)",
            (),
        )
        # Assign all existing rows to the first registered school
        first = fetch_one("SELECT id FROM schools ORDER BY id LIMIT 1", ())
        if first:
            execute(
                "UPDATE academic_years SET school_id=? WHERE school_id IS NULL",
                (first["id"],),
            )
