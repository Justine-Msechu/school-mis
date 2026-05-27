"""
Migration 004 — Auto-generated IDs

  1. teachers — add employee_no, date_of_birth, subject_specialization, joining_date columns
  2. school_config — seed student_adm_seq and teacher_emp_seq counters
  3. Backfill existing teachers with auto-generated employee_no
  4. Backfill existing students admission_no sequence counter
"""

import os, sqlite3, datetime
from pathlib import Path

DB_PATH = Path(os.environ.get(
    "SCHOOL_MIS_DB_PATH",
    str(Path(__file__).parent.parent.parent / "school_mis.db"),
))


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _col_exists(cur, table, col):
    return col in [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def run():
    conn = _conn()
    cur  = conn.cursor()

    # ── 1. Add missing columns to teachers ────────────────────────────────────
    for col, definition in [
        ("employee_no",            "TEXT"),
        ("date_of_birth",          "TEXT"),
        ("subject_specialization", "TEXT"),
        ("joining_date",           "TEXT"),
    ]:
        if not _col_exists(cur, "teachers", col):
            cur.execute(f"ALTER TABLE teachers ADD COLUMN {col} {definition}")

    # Unique index on employee_no (sparse — allows NULL for legacy rows pre-migration)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teachers_employee_no
        ON teachers(employee_no) WHERE employee_no IS NOT NULL
    """)

    # Unique index on students.admission_no (should already be UNIQUE, but ensure index)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_admission_no
        ON students(admission_no)
    """)

    # ── 2. Determine current year for format ──────────────────────────────────
    year = datetime.date.today().year

    # ── 3. Seed sequence counters in school_config ────────────────────────────
    # student_adm_seq: find max existing numeric suffix from admission_no
    rows = cur.execute("SELECT admission_no FROM students WHERE admission_no IS NOT NULL").fetchall()
    max_adm = 0
    for r in rows:
        adm = r[0].replace("/", "").replace("-", "")
        digits = "".join(c for c in adm if c.isdigit())
        if digits:
            max_adm = max(max_adm, int(digits))
    cur.execute(
        "INSERT OR IGNORE INTO school_config (key, value) VALUES ('student_adm_seq', ?)",
        (str(max_adm),),
    )

    # teacher_emp_seq: find max existing numeric suffix from employee_no
    rows2 = cur.execute("SELECT employee_no FROM teachers WHERE employee_no IS NOT NULL").fetchall()
    max_emp = 0
    for r in rows2:
        emp = r[0].replace("/", "").replace("-", "")
        digits = "".join(c for c in emp if c.isdigit())
        if digits:
            max_emp = max(max_emp, int(digits))
    cur.execute(
        "INSERT OR IGNORE INTO school_config (key, value) VALUES ('teacher_emp_seq', ?)",
        (str(max_emp),),
    )

    # ── 4. Backfill existing teachers with employee_no ────────────────────────
    teachers_no_id = cur.execute(
        "SELECT id FROM teachers WHERE employee_no IS NULL OR employee_no = '' ORDER BY id"
    ).fetchall()
    for row in teachers_no_id:
        cur.execute("UPDATE school_config SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'teacher_emp_seq'")
        seq_row = cur.execute("SELECT value FROM school_config WHERE key = 'teacher_emp_seq'").fetchone()
        seq = int(seq_row[0])
        emp_no = f"EMP/{year}/{seq:04d}"
        cur.execute("UPDATE teachers SET employee_no = ? WHERE id = ?", (emp_no, row[0]))

    conn.commit()
    conn.close()
    print(f"  [004] teachers columns + employee_no backfill done ({len(teachers_no_id)} teachers updated)")
    print("  [004] sequence counters seeded in school_config")
    print("  [004] Migration 004 complete")


if __name__ == "__main__":
    run()
