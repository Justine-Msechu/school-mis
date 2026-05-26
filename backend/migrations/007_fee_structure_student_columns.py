"""
Migration 007 — Add student_id and student_type columns to fee_structures.

The original fee_structures table was created by the PyQt6 desktop app and
only had class_id. The web backend's list/create endpoints expect student_id
and student_type to support per-student fee overrides.
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    try:
        conn.execute("ALTER TABLE fee_structures ADD COLUMN student_id INTEGER REFERENCES students(id)")
    except Exception:
        pass  # already exists

    try:
        conn.execute("ALTER TABLE fee_structures ADD COLUMN student_type TEXT")
    except Exception:
        pass  # already exists

    conn.commit()
