"""
Migration 008 — Add grade_level to fee_structures.

Allows a fee structure to target all class sections at a given grade level
(e.g. grade_level=7 covers Std 7A and Std 7B) instead of requiring a separate
row per section.
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    try:
        conn.execute("ALTER TABLE fee_structures ADD COLUMN grade_level INTEGER")
    except Exception:
        pass  # already exists

    conn.commit()
