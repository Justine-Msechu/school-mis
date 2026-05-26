"""
Migration 017 — Extended welfare module.

Adds:
  welfare_counseling    — counseling session logs
  welfare_visits        — home visit records
  welfare_distributions — in-kind support (uniform, meals, stationery…)
  welfare_incidents     — at-risk flags and incident reports

Also seeds new permissions for the welfare sub-modules.
"""


def run():
    from backend.core.db import _get_conn
    import sqlite3

    def _run_on(conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS welfare_counseling (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id      INTEGER NOT NULL REFERENCES students(id),
                session_date    TEXT    NOT NULL DEFAULT (date('now')),
                reason          TEXT    NOT NULL,
                notes           TEXT,
                counselor_id    INTEGER,
                follow_up_date  TEXT,
                follow_up_done  INTEGER DEFAULT 0,
                created_at      TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS welfare_visits (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id       INTEGER NOT NULL REFERENCES students(id),
                visit_date       TEXT    NOT NULL DEFAULT (date('now')),
                address_visited  TEXT,
                findings         TEXT    NOT NULL,
                action_taken     TEXT,
                next_visit_date  TEXT,
                officer_id       INTEGER,
                created_at       TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS welfare_distributions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id          INTEGER NOT NULL REFERENCES students(id),
                item_type           TEXT    NOT NULL,
                quantity            REAL    DEFAULT 1,
                unit                TEXT    DEFAULT 'pcs',
                distribution_date   TEXT    NOT NULL DEFAULT (date('now')),
                notes               TEXT,
                distributed_by      INTEGER,
                created_at          TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS welfare_incidents (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id    INTEGER NOT NULL REFERENCES students(id),
                incident_type TEXT    NOT NULL,
                reported_date TEXT    NOT NULL DEFAULT (date('now')),
                description   TEXT    NOT NULL,
                action_taken  TEXT,
                resolved      INTEGER DEFAULT 0,
                resolved_date TEXT,
                reported_by   INTEGER,
                created_at    TEXT    DEFAULT (datetime('now'))
            )
        """)

        # Seed new permissions (ignore duplicates)
        new_perms = [
            ("welfare.counsel",      "welfare", "counsel",      "Log counseling sessions",   "GLOBAL"),
            ("welfare.visits",       "welfare", "visits",       "Log home visits",           "GLOBAL"),
            ("welfare.distributions","welfare", "distributions","Record in-kind support",     "GLOBAL"),
            ("welfare.incidents",    "welfare", "incidents",    "Report/resolve incidents",  "GLOBAL"),
        ]
        for code, domain, action, desc, scope in new_perms:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO permissions (code, domain, action, description, scope_type) VALUES (?,?,?,?,?)",
                    (code, domain, action, desc, scope),
                )
            except Exception:
                pass

        conn.commit()

    # Run on migration DB
    conn1 = _get_conn()
    _run_on(conn1)

    # Run on production DB
    import os
    prod = os.path.join(os.path.dirname(__file__), "..", "..", "school_mis.db")
    prod = os.path.normpath(prod)
    if os.path.exists(prod):
        conn2 = sqlite3.connect(prod)
        _run_on(conn2)
        conn2.close()
