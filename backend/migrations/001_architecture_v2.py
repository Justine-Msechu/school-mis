"""
Migration 001 — Architecture v2.0

Adds tables that were missing for enterprise-grade operation:
  - terms                  (academic term granularity within a year)
  - grade_scales           (configurable grade boundaries per year)
  - result_approval_log    (full approval history trail for grades)
  - ledger_entries         (double-entry bookkeeping)
  - expense_categories     (structured expense categories)
  - notifications          (in-app notification system)
  - notification_recipients
  - login_sessions         (persistent session tracking)
  - sync_queue             (for future cloud sync)
  - class_subjects         (proper class-subject-teacher mapping)

All statements use CREATE TABLE IF NOT EXISTS — safe to run multiple times.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "school_mis.db"

MIGRATIONS = [

    # ── Academic terms ─────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS terms (
        id               INTEGER PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        name             TEXT NOT NULL,
        start_date       TEXT,
        end_date         TEXT,
        is_current       INTEGER NOT NULL DEFAULT 0,
        is_locked        INTEGER NOT NULL DEFAULT 0,
        created_at       TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(academic_year_id, name)
    )
    """,

    # ── Configurable grade scale (per academic year) ───────────────────────────
    """
    CREATE TABLE IF NOT EXISTS grade_scales (
        id               INTEGER PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        label            TEXT NOT NULL,
        min_pct          REAL NOT NULL,
        max_pct          REAL NOT NULL,
        gpa_points       REAL NOT NULL DEFAULT 0,
        remarks          TEXT NOT NULL DEFAULT '',
        UNIQUE(academic_year_id, label)
    )
    """,

    # ── Grade approval history trail ───────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS result_approval_log (
        id          INTEGER PRIMARY KEY,
        grade_id    INTEGER NOT NULL REFERENCES grades(id),
        from_status TEXT NOT NULL,
        to_status   TEXT NOT NULL,
        action      TEXT NOT NULL,
        actor_id    INTEGER REFERENCES users(id),
        comment     TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,

    # ── Double-entry ledger ────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS ledger_entries (
        id             INTEGER PRIMARY KEY,
        entry_date     TEXT NOT NULL,
        account_code   TEXT NOT NULL,
        account_name   TEXT NOT NULL,
        debit_amount   REAL NOT NULL DEFAULT 0,
        credit_amount  REAL NOT NULL DEFAULT 0,
        reference_type TEXT NOT NULL,
        reference_id   INTEGER NOT NULL,
        description    TEXT NOT NULL DEFAULT '',
        posted_by      INTEGER REFERENCES users(id),
        created_at     TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,

    # Ledger indexes
    "CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger_entries(entry_date, account_code)",
    "CREATE INDEX IF NOT EXISTS idx_ledger_ref  ON ledger_entries(reference_type, reference_id)",

    # ── Expense categories ─────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS expense_categories (
        id           INTEGER PRIMARY KEY,
        name         TEXT NOT NULL UNIQUE,
        account_code TEXT NOT NULL DEFAULT 'EXPENSE',
        is_active    INTEGER NOT NULL DEFAULT 1
    )
    """,

    # Seed default expense categories
    """
    INSERT OR IGNORE INTO expense_categories (name, account_code) VALUES
        ('Salaries',         'EXPENSE'),
        ('Utilities',        'EXPENSE'),
        ('Stationery',       'EXPENSE'),
        ('Maintenance',      'EXPENSE'),
        ('Transport',        'EXPENSE'),
        ('Food & Catering',  'EXPENSE'),
        ('Equipment',        'EXPENSE'),
        ('Events',           'EXPENSE'),
        ('Other',            'EXPENSE')
    """,

    # ── In-app notifications ───────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id         INTEGER PRIMARY KEY,
        type       TEXT NOT NULL,
        title      TEXT NOT NULL,
        body       TEXT NOT NULL DEFAULT '',
        data_json  TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS notification_recipients (
        id              INTEGER PRIMARY KEY,
        notification_id INTEGER NOT NULL REFERENCES notifications(id),
        user_id         INTEGER NOT NULL REFERENCES users(id),
        read_at         TEXT,
        dismissed_at    TEXT,
        UNIQUE(notification_id, user_id)
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_notif_user ON notification_recipients(user_id, read_at)",

    # ── Login sessions (persistent, survives backend restart) ─────────────────
    """
    CREATE TABLE IF NOT EXISTS login_sessions (
        id             INTEGER PRIMARY KEY,
        user_id        INTEGER NOT NULL REFERENCES users(id),
        session_token  TEXT NOT NULL UNIQUE,
        ip_address     TEXT,
        user_agent     TEXT,
        created_at     TEXT NOT NULL DEFAULT (datetime('now')),
        expires_at     TEXT NOT NULL,
        invalidated_at TEXT
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_session_token ON login_sessions(session_token)",
    "CREATE INDEX IF NOT EXISTS idx_session_user  ON login_sessions(user_id, invalidated_at)",

    # ── Sync queue (future cloud sync) ────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS sync_queue (
        id           INTEGER PRIMARY KEY,
        table_name   TEXT NOT NULL,
        record_id    INTEGER NOT NULL,
        operation    TEXT NOT NULL CHECK(operation IN ('INSERT','UPDATE','DELETE')),
        payload_json TEXT NOT NULL,
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        synced_at    TEXT,
        sync_error   TEXT,
        retry_count  INTEGER NOT NULL DEFAULT 0
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_sync_pending ON sync_queue(synced_at)",

    # ── Class-subject-teacher mapping ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS class_subjects (
        id             INTEGER PRIMARY KEY,
        class_id       INTEGER NOT NULL REFERENCES classes(id),
        subject_id     INTEGER NOT NULL REFERENCES subjects(id),
        teacher_id     INTEGER REFERENCES teachers(id),
        weekly_periods INTEGER,
        created_at     TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(class_id, subject_id)
    )
    """,

    # ── Soft-delete columns on key tables (add only if missing) ───────────────
    # SQLite's ALTER TABLE is limited; we add columns safely
    "ALTER TABLE students  ADD COLUMN deleted_at TEXT",
    "ALTER TABLE teachers  ADD COLUMN deleted_at TEXT",
    "ALTER TABLE classes   ADD COLUMN deleted_at TEXT",
    "ALTER TABLE subjects  ADD COLUMN deleted_at TEXT",
    "ALTER TABLE fee_structures ADD COLUMN deleted_at TEXT",

    # ── Performance indexes ────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_student_admission ON students(admission_no)",
    "CREATE INDEX IF NOT EXISTS idx_student_class     ON students(class_id, is_active)",
    "CREATE INDEX IF NOT EXISTS idx_attendance_date   ON attendance(date, class_id)",
    "CREATE INDEX IF NOT EXISTS idx_grades_exam_class ON grades(exam_id, subject_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_student  ON fee_payments(student_id, payment_date)",
    "CREATE INDEX IF NOT EXISTS idx_audit_table       ON audit_log(table_name, record_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_user        ON audit_log(user_id, ts)",

    # ── WAL mode and integrity pragmas ────────────────────────────────────────
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
]


def run(db_path: str | Path | None = None) -> None:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=OFF")  # Disable during migration

    success = 0
    skipped = 0
    errors  = 0

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
            # Ignore "duplicate column", "already exists" — idempotent
            if any(x in msg for x in ("already exists", "duplicate column", "no such table")):
                skipped += 1
            else:
                print(f"[WARN] {msg[:120]}\n  SQL: {stmt[:80]}...", file=sys.stderr)
                errors += 1

    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    conn.close()

    print(f"Migration 001 complete: {success} applied, {skipped} skipped, {errors} warnings")


if __name__ == "__main__":
    run()
