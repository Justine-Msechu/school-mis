"""
Migration 003 — Structural Fixes

Addresses every red flag from the structural audit:

 1.  attendance     — UNIQUE(student_id,date) → UNIQUE(student_id,class_id,date)
                      so transferred students can have attendance in new class on same day
 2.  grades         — add class_id snapshot column (class at time of exam)
 3.  welfare_records — remove UNIQUE(student_id); add is_current flag for history
 4.  teacher_subjects — add academic_year_id so assignments are year-scoped
 5.  timetable_slots  — DB-level UNIQUE to prevent teacher double-booking
 6.  report_cards     — UNIQUE(student_id,exam_id) → UNIQUE(student_id,exam_id,class_id)
 7.  students         — parent_* columns kept but guardian auto-sync added via migration
 8.  login_attempts   — new table for rate limiting brute-force login attempts
 9.  password_changes — new table to track forced password changes
"""

import os, sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get(
    "SCHOOL_MIS_DB_PATH",
    str(Path(__file__).parent.parent.parent / "school_mis.db"),
))


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _table_has_column(cur, table, column):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def _index_exists(cur, name):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone() is not None


def _table_exists(cur, name):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def run():
    import os as _os
    if _os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        print("  [003] structural fixes — skipped (PostgreSQL mode, handled by pg_schema)")
        return

    conn = _conn()
    cur  = conn.cursor()

    # Must disable FK enforcement while recreating tables
    cur.execute("PRAGMA foreign_keys = OFF")
    cur.execute("BEGIN")

    try:

        # ── 1. ATTENDANCE — fix UNIQUE constraint ──────────────────────────────
        # Old: UNIQUE(student_id, date)  ← blocks transfers & period attendance
        # New: UNIQUE(student_id, class_id, date)
        if not _index_exists(cur, "idx_attendance_student_class_date"):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id  INTEGER NOT NULL REFERENCES students(id),
                    class_id    INTEGER REFERENCES classes(id),
                    date        TEXT NOT NULL,
                    status      TEXT NOT NULL
                                CHECK(status IN ('Present','Absent','Late','Excused')),
                    notes       TEXT,
                    recorded_by INTEGER REFERENCES users(id),
                    UNIQUE(student_id, class_id, date)
                )
            """)
            cur.execute("""
                INSERT OR IGNORE INTO attendance_new
                    (id, student_id, class_id, date, status, notes, recorded_by)
                SELECT id, student_id, class_id, date, status, notes, recorded_by
                FROM attendance
            """)
            cur.execute("DROP TABLE attendance")
            cur.execute("ALTER TABLE attendance_new RENAME TO attendance")
            cur.execute("""
                CREATE INDEX idx_attendance_student_class_date
                ON attendance(student_id, class_id, date)
            """)
            print("  [003] attendance UNIQUE fixed")

        # ── 2. GRADES — add class_id snapshot column ───────────────────────────
        if not _table_has_column(cur, "grades", "class_id"):
            cur.execute("ALTER TABLE grades ADD COLUMN class_id INTEGER REFERENCES classes(id)")
            # Backfill from students.class_id (best approximation for existing data)
            cur.execute("""
                UPDATE grades SET class_id = (
                    SELECT s.class_id FROM students s WHERE s.id = grades.student_id
                ) WHERE class_id IS NULL
            """)
            print("  [003] grades.class_id added")

        # ── 3. WELFARE_RECORDS — remove UNIQUE(student_id), add history support ─
        if not _table_has_column(cur, "welfare_records", "is_current"):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS welfare_records_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id    INTEGER NOT NULL REFERENCES students(id),
                    category      TEXT NOT NULL
                                  CHECK(category IN ('orphan','half_orphan','sponsored','vulnerable')),
                    is_current    INTEGER NOT NULL DEFAULT 1,
                    verified      INTEGER DEFAULT 0,
                    verified_by   INTEGER REFERENCES users(id),
                    verified_date TEXT,
                    sponsor_name  TEXT,
                    sponsor_org   TEXT,
                    support_type  TEXT
                                  CHECK(support_type IN ('full_fees','partial','non_financial')),
                    notes         TEXT,
                    superseded_at TEXT,
                    created_at    TEXT DEFAULT (datetime('now'))
                )
            """)
            cur.execute("""
                INSERT OR IGNORE INTO welfare_records_new
                    (id, student_id, category, is_current, verified, verified_by,
                     verified_date, sponsor_name, sponsor_org, support_type, notes, created_at)
                SELECT id, student_id, category, 1, verified, verified_by,
                       verified_date, sponsor_name, sponsor_org, support_type, notes, created_at
                FROM welfare_records
            """)
            cur.execute("DROP TABLE welfare_records")
            cur.execute("ALTER TABLE welfare_records_new RENAME TO welfare_records")
            # Partial-index equivalent: only one is_current=1 per student
            cur.execute("""
                CREATE UNIQUE INDEX idx_welfare_student_current
                ON welfare_records(student_id) WHERE is_current = 1
            """)
            print("  [003] welfare_records history enabled")

        # ── 4. TEACHER_SUBJECTS — add academic_year_id ────────────────────────
        if not _table_has_column(cur, "teacher_subjects", "academic_year_id"):
            cur.execute(
                "ALTER TABLE teacher_subjects ADD COLUMN academic_year_id INTEGER REFERENCES academic_years(id)"
            )
            # Backfill with the current year
            cur.execute("""
                UPDATE teacher_subjects SET academic_year_id = (
                    SELECT id FROM academic_years WHERE is_current = 1 LIMIT 1
                ) WHERE academic_year_id IS NULL
            """)
            print("  [003] teacher_subjects.academic_year_id added")

        # ── 5. TIMETABLE_SLOTS — DB-level teacher conflict prevention ──────────
        if not _index_exists(cur, "idx_timetable_teacher_slot"):
            # Only enforce when teacher_id IS NOT NULL
            cur.execute("""
                CREATE UNIQUE INDEX idx_timetable_teacher_slot
                ON timetable_slots(version_id, teacher_id, day_of_week, period_id)
                WHERE teacher_id IS NOT NULL
            """)
            print("  [003] timetable teacher conflict index added")

        # ── 6. REPORT_CARDS — fix UNIQUE to include class_id ──────────────────
        existing_rc = cur.execute(
            "SELECT sql FROM sqlite_master WHERE name='report_cards'"
        ).fetchone()
        if existing_rc and "UNIQUE(student_id, exam_id)" in existing_rc[0] \
                and "class_id" not in existing_rc[0].split("UNIQUE")[1]:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS report_cards_new (
                    id                   INTEGER PRIMARY KEY,
                    student_id           INTEGER NOT NULL REFERENCES students(id),
                    exam_id              INTEGER NOT NULL REFERENCES exams(id),
                    academic_year_id     INTEGER NOT NULL REFERENCES academic_years(id),
                    class_id             INTEGER NOT NULL REFERENCES classes(id),
                    class_name_snapshot  TEXT NOT NULL DEFAULT '',
                    total_marks          REAL,
                    total_possible       REAL,
                    overall_pct          REAL,
                    overall_grade        TEXT,
                    class_rank           INTEGER,
                    stream_rank          INTEGER,
                    days_present         INTEGER,
                    days_absent          INTEGER,
                    days_total           INTEGER,
                    principal_comment    TEXT,
                    class_teacher_comment TEXT,
                    is_published         INTEGER NOT NULL DEFAULT 0,
                    is_locked            INTEGER NOT NULL DEFAULT 0,
                    pdf_path             TEXT,
                    generated_at         TEXT NOT NULL DEFAULT (datetime('now')),
                    generated_by         INTEGER REFERENCES users(id),
                    published_at         TEXT,
                    published_by         INTEGER REFERENCES users(id),
                    locked_at            TEXT,
                    UNIQUE(student_id, exam_id, class_id)
                )
            """)
            cur.execute("""
                INSERT OR IGNORE INTO report_cards_new SELECT * FROM report_cards
            """)
            cur.execute("DROP TABLE report_cards")
            cur.execute("ALTER TABLE report_cards_new RENAME TO report_cards")
            print("  [003] report_cards UNIQUE fixed (added class_id)")

        # ── 7. PARENT DATA → GUARDIANS auto-migration ─────────────────────────
        # For every student that has parent_name but no linked guardian, create one.
        if _table_exists(cur, "guardians") and _table_exists(cur, "guardian_students"):
            orphaned = cur.execute("""
                SELECT s.id, s.parent_name, s.parent_phone, s.parent_email
                FROM students s
                WHERE s.parent_name IS NOT NULL AND s.parent_name != ''
                  AND s.id NOT IN (SELECT student_id FROM guardian_students)
            """).fetchall()
            for row in orphaned:
                cur.execute("""
                    INSERT INTO guardians (full_name, phone, email, relationship, is_emergency_contact)
                    VALUES (?, ?, ?, 'guardian', 1)
                """, (row["parent_name"], row["parent_phone"], row["parent_email"]))
                gid = cur.lastrowid
                cur.execute("""
                    INSERT OR IGNORE INTO guardian_students (guardian_id, student_id, is_primary)
                    VALUES (?, ?, 1)
                """, (gid, row["id"]))
            if orphaned:
                print(f"  [003] migrated {len(orphaned)} parent records → guardians")

        # ── 8. LOGIN_ATTEMPTS — rate limiting table ────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,   -- username or IP
                succeeded  INTEGER NOT NULL DEFAULT 0,
                ts         TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_login_attempts_identifier_ts
            ON login_attempts(identifier, ts)
        """)
        print("  [003] login_attempts table ready")

        # ── 9. SYNC welfare → students.student_category ────────────────────────
        # Bring existing welfare_records categories into students.student_category
        cur.execute("""
            UPDATE students SET student_category = (
                SELECT CASE wr.category
                           WHEN 'orphan'      THEN 'orphan'
                           WHEN 'half_orphan' THEN 'orphan'
                           WHEN 'sponsored'   THEN 'sponsored'
                           ELSE 'regular'
                       END
                FROM welfare_records wr
                WHERE wr.student_id = students.id AND wr.is_current = 1
                LIMIT 1
            )
            WHERE id IN (SELECT student_id FROM welfare_records WHERE is_current = 1)
        """)

        conn.commit()
        print("  [003] Migration 003 complete")

    except Exception as e:
        conn.rollback()
        print(f"  [003] FAILED — rolling back: {e}")
        raise
    finally:
        cur.execute("PRAGMA foreign_keys = ON")
        conn.close()


if __name__ == "__main__":
    run()
