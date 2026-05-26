"""
Migration 010 — Add prorate_pct to payroll_items.

Allows pro-rating a payslip to a percentage of full-month salary
(e.g. 50% for someone who joined mid-month).
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()
    try:
        conn.execute(
            "ALTER TABLE payroll_items ADD COLUMN prorate_pct REAL NOT NULL DEFAULT 100"
        )
    except Exception:
        pass  # already exists
    conn.commit()
