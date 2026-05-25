"""
Migration 002 — Enterprise Phase 2

New tables:
  enrollments              — proper student-class-year relationship (replaces students.class_id)
  guardians                — full guardian/parent records
  guardian_students        — many-to-many guardian ↔ student
  report_cards             — immutable report card snapshots
  report_card_subjects     — per-subject snapshot rows
  report_card_comments     — teacher/principal comments per card
  report_card_jobs         — batch generation job tracking
  timetable_versions       — draft/active/archived timetable sets
  timetable_periods        — period definitions (Period 1 = 08:00–08:45)
  timetable_slots          — actual schedule entries (replaces old timetable)
  documents                — uploaded file records
  document_associations    — polymorphic document ↔ any entity link
  announcements            — school-wide announcements
  announcement_targets     — who sees each announcement
  portal_auth_tokens       — parent/student portal session tokens
"""

import sqlite3, sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "school_mis.db"

MIGRATIONS = [

    # ── PHASE 1: ENROLLMENT SYSTEM ────────────────────────────────────────────

    """
    CREATE TABLE IF NOT EXISTS enrollments (
        id               INTEGER PRIMARY KEY,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        class_id         INTEGER NOT NULL REFERENCES classes(id),
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        enrollment_date  TEXT NOT NULL DEFAULT (date('now')),
        status           TEXT NOT NULL DEFAULT 'active'
            CHECK(status IN ('active','transferred','graduated','withdrawn','archived')),
        transfer_from_class_id INTEGER REFERENCES classes(id),
        transfer_reason  TEXT,
        exit_date        TEXT,
        notes            TEXT,
        created_by       INTEGER REFERENCES users(id),
        created_at       TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(student_id, academic_year_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_enrollment_student ON enrollments(student_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_enrollment_class   ON enrollments(class_id, academic_year_id)",

    # ── PHASE 4: GUARDIAN / PARENT SYSTEM ────────────────────────────────────

    """
    CREATE TABLE IF NOT EXISTS guardians (
        id               INTEGER PRIMARY KEY,
        full_name        TEXT NOT NULL,
        relationship     TEXT NOT NULL DEFAULT 'guardian'
            CHECK(relationship IN ('father','mother','guardian','grandparent','sibling','other')),
        gender           TEXT CHECK(gender IN ('male','female','other')),
        phone            TEXT,
        alt_phone        TEXT,
        email            TEXT,
        id_number        TEXT,
        occupation       TEXT,
        address          TEXT,
        is_emergency_contact INTEGER NOT NULL DEFAULT 0,
        is_pickup_authorized INTEGER NOT NULL DEFAULT 1,
        is_billing_contact   INTEGER NOT NULL DEFAULT 0,
        communication_pref   TEXT NOT NULL DEFAULT 'phone'
            CHECK(communication_pref IN ('phone','email','sms','all')),
        user_id          INTEGER REFERENCES users(id),
        photo_path       TEXT,
        notes            TEXT,
        created_at       TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
        deleted_at       TEXT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS guardian_students (
        id           INTEGER PRIMARY KEY,
        guardian_id  INTEGER NOT NULL REFERENCES guardians(id),
        student_id   INTEGER NOT NULL REFERENCES students(id),
        is_primary   INTEGER NOT NULL DEFAULT 0,
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(guardian_id, student_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_gs_guardian ON guardian_students(guardian_id)",
    "CREATE INDEX IF NOT EXISTS idx_gs_student  ON guardian_students(student_id)",

    # ── PHASE 2: REPORT CARD ENGINE ───────────────────────────────────────────

    """
    CREATE TABLE IF NOT EXISTS report_cards (
        id               INTEGER PRIMARY KEY,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        exam_id          INTEGER NOT NULL REFERENCES exams(id),
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        class_id         INTEGER NOT NULL REFERENCES classes(id),
        class_name_snapshot TEXT NOT NULL DEFAULT '',
        total_marks      REAL,
        total_possible   REAL,
        overall_pct      REAL,
        overall_grade    TEXT,
        class_rank       INTEGER,
        stream_rank      INTEGER,
        days_present     INTEGER,
        days_absent      INTEGER,
        days_total       INTEGER,
        principal_comment TEXT,
        class_teacher_comment TEXT,
        is_published     INTEGER NOT NULL DEFAULT 0,
        is_locked        INTEGER NOT NULL DEFAULT 0,
        pdf_path         TEXT,
        generated_at     TEXT NOT NULL DEFAULT (datetime('now')),
        generated_by     INTEGER REFERENCES users(id),
        published_at     TEXT,
        published_by     INTEGER REFERENCES users(id),
        locked_at        TEXT,
        UNIQUE(student_id, exam_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_rc_student ON report_cards(student_id, exam_id)",
    "CREATE INDEX IF NOT EXISTS idx_rc_exam    ON report_cards(exam_id, class_id)",

    """
    CREATE TABLE IF NOT EXISTS report_card_subjects (
        id              INTEGER PRIMARY KEY,
        report_card_id  INTEGER NOT NULL REFERENCES report_cards(id),
        subject_id      INTEGER NOT NULL REFERENCES subjects(id),
        subject_name    TEXT NOT NULL,
        marks_obtained  REAL,
        total_marks     REAL,
        percentage      REAL,
        grade_label     TEXT,
        gpa_points      REAL,
        position        INTEGER,
        teacher_name    TEXT,
        remarks         TEXT,
        UNIQUE(report_card_id, subject_id)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS report_card_comments (
        id             INTEGER PRIMARY KEY,
        report_card_id INTEGER NOT NULL REFERENCES report_cards(id),
        author_id      INTEGER REFERENCES users(id),
        author_role    TEXT,
        comment_type   TEXT NOT NULL DEFAULT 'teacher'
            CHECK(comment_type IN ('teacher','principal','guidance','general')),
        comment_text   TEXT NOT NULL,
        created_at     TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS report_card_jobs (
        id               INTEGER PRIMARY KEY,
        exam_id          INTEGER NOT NULL REFERENCES exams(id),
        class_id         INTEGER REFERENCES classes(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        status           TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','running','completed','failed')),
        total_students   INTEGER,
        processed        INTEGER NOT NULL DEFAULT 0,
        failed_count     INTEGER NOT NULL DEFAULT 0,
        error_log        TEXT,
        started_at       TEXT,
        completed_at     TEXT,
        initiated_by     INTEGER REFERENCES users(id),
        created_at       TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,

    # ── PHASE 3: TIMETABLE ENGINE ─────────────────────────────────────────────

    """
    CREATE TABLE IF NOT EXISTS timetable_versions (
        id               INTEGER PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        term_id          INTEGER REFERENCES terms(id),
        name             TEXT NOT NULL,
        status           TEXT NOT NULL DEFAULT 'draft'
            CHECK(status IN ('draft','active','archived')),
        effective_from   TEXT,
        effective_to     TEXT,
        created_by       INTEGER REFERENCES users(id),
        created_at       TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS timetable_periods (
        id           INTEGER PRIMARY KEY,
        name         TEXT NOT NULL,
        period_no    INTEGER NOT NULL,
        start_time   TEXT NOT NULL,
        end_time     TEXT NOT NULL,
        is_break     INTEGER NOT NULL DEFAULT 0,
        sort_order   INTEGER NOT NULL DEFAULT 0,
        UNIQUE(period_no)
    )
    """,

    # Seed standard school periods
    """
    INSERT OR IGNORE INTO timetable_periods (name, period_no, start_time, end_time, sort_order) VALUES
        ('Period 1',    1, '07:30', '08:15', 1),
        ('Period 2',    2, '08:15', '09:00', 2),
        ('Period 3',    3, '09:00', '09:45', 3),
        ('Break',       0, '09:45', '10:15', 4),
        ('Period 4',    4, '10:15', '11:00', 5),
        ('Period 5',    5, '11:00', '11:45', 6),
        ('Period 6',    6, '11:45', '12:30', 7),
        ('Lunch',       0, '12:30', '13:00', 8),
        ('Period 7',    7, '13:00', '13:45', 9),
        ('Period 8',    8, '13:45', '14:30', 10)
    """,

    """
    CREATE TABLE IF NOT EXISTS timetable_slots (
        id                   INTEGER PRIMARY KEY,
        version_id           INTEGER NOT NULL REFERENCES timetable_versions(id),
        class_id             INTEGER NOT NULL REFERENCES classes(id),
        subject_id           INTEGER NOT NULL REFERENCES subjects(id),
        teacher_id           INTEGER REFERENCES teachers(id),
        period_id            INTEGER NOT NULL REFERENCES timetable_periods(id),
        day_of_week          INTEGER NOT NULL CHECK(day_of_week BETWEEN 1 AND 6),
        room                 TEXT,
        notes                TEXT,
        created_at           TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_slot_version_class ON timetable_slots(version_id, class_id)",
    "CREATE INDEX IF NOT EXISTS idx_slot_teacher       ON timetable_slots(teacher_id, day_of_week, period_id)",

    # ── PHASE 8: DOCUMENT SYSTEM ──────────────────────────────────────────────

    """
    CREATE TABLE IF NOT EXISTS documents (
        id             INTEGER PRIMARY KEY,
        filename       TEXT NOT NULL,
        original_name  TEXT NOT NULL,
        mime_type      TEXT NOT NULL,
        file_size      INTEGER,
        storage_path   TEXT NOT NULL,
        category       TEXT NOT NULL DEFAULT 'general'
            CHECK(category IN ('photo','receipt','medical','report','certificate','other','general')),
        uploaded_by    INTEGER REFERENCES users(id),
        is_public      INTEGER NOT NULL DEFAULT 0,
        created_at     TEXT NOT NULL DEFAULT (datetime('now')),
        deleted_at     TEXT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS document_associations (
        id           INTEGER PRIMARY KEY,
        document_id  INTEGER NOT NULL REFERENCES documents(id),
        entity_type  TEXT NOT NULL,
        entity_id    INTEGER NOT NULL,
        label        TEXT,
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(document_id, entity_type, entity_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_doc_assoc ON document_associations(entity_type, entity_id)",

    # ── ANNOUNCEMENTS ─────────────────────────────────────────────────────────

    """
    CREATE TABLE IF NOT EXISTS announcements (
        id           INTEGER PRIMARY KEY,
        title        TEXT NOT NULL,
        body         TEXT NOT NULL,
        category     TEXT NOT NULL DEFAULT 'general'
            CHECK(category IN ('general','academic','finance','health','event','urgent')),
        is_pinned    INTEGER NOT NULL DEFAULT 0,
        published_at TEXT,
        expires_at   TEXT,
        author_id    INTEGER REFERENCES users(id),
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        deleted_at   TEXT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS announcement_targets (
        id              INTEGER PRIMARY KEY,
        announcement_id INTEGER NOT NULL REFERENCES announcements(id),
        target_type     TEXT NOT NULL CHECK(target_type IN ('all','role','class','student','guardian')),
        target_id       INTEGER
    )
    """,

    # ── PORTAL AUTH ───────────────────────────────────────────────────────────

    """
    CREATE TABLE IF NOT EXISTS portal_auth_tokens (
        id             INTEGER PRIMARY KEY,
        user_id        INTEGER NOT NULL REFERENCES users(id),
        token          TEXT NOT NULL UNIQUE,
        portal_type    TEXT NOT NULL CHECK(portal_type IN ('parent','student')),
        created_at     TEXT NOT NULL DEFAULT (datetime('now')),
        expires_at     TEXT NOT NULL,
        invalidated_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_portal_token ON portal_auth_tokens(token)",

    # ── PERFORMANCE INDEXES for phase 2 ───────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_report_card_job ON report_card_jobs(exam_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_announcement_pub ON announcements(published_at, expires_at)",
]


def run(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=OFF")
    success = skipped = warnings = 0
    for sql in MIGRATIONS:
        stmt = sql.strip()
        if not stmt:
            continue
        try:
            conn.execute(stmt)
            conn.commit()
            success += 1
        except sqlite3.OperationalError as e:
            msg = str(e)
            if any(x in msg for x in ("already exists", "duplicate column", "UNIQUE constraint")):
                skipped += 1
            else:
                print(f"[WARN] {msg[:120]}", file=sys.stderr)
                warnings += 1
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    conn.close()
    print(f"Migration 002 complete: {success} applied, {skipped} skipped, {warnings} warnings")


if __name__ == "__main__":
    run()
