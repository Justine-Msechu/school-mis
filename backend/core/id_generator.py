"""
Atomic sequential ID generation for students and teachers.

Counters are stored in school_config so they survive restarts and
work correctly across concurrent requests (SQLite serialises writes).

Format:
  Admission number : ADM/YYYY/NNNN   e.g. ADM/2026/0001
  Employee number  : EMP/YYYY/NNNN   e.g. EMP/2026/0001
"""

import datetime
from database.db import fetch_one, execute


def _year() -> int:
    return datetime.date.today().year


def _next_seq(config_key: str) -> int:
    """Increment the counter atomically and return the new value."""
    # Ensure the row exists first (handles PostgreSQL fresh installs where
    # migration 004 is SQLite-only and never seeds school_config in PG mode)
    execute(
        "INSERT OR IGNORE INTO school_config (key, value) VALUES (?, '0')",
        (config_key,),
    )
    execute(
        "UPDATE school_config SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = ?",
        (config_key,),
    )
    row = fetch_one("SELECT value FROM school_config WHERE key = ?", (config_key,))
    return int(row["value"]) if row else 1


def next_admission_no() -> str:
    seq = _next_seq("student_adm_seq")
    return f"ADM/{_year()}/{seq:04d}"


def next_employee_no() -> str:
    seq = _next_seq("teacher_emp_seq")
    return f"EMP/{_year()}/{seq:04d}"
