"""
School MIS — Database Layer  (v3)
Added: finance, welfare, inventory, accounting, reporting domains.

Dual-mode: if DATABASE_URL is set (PostgreSQL/Docker) all queries go through
backend.core.db (psycopg2 pool + auto-conversion layer).
Otherwise the original SQLite path is used (desktop app / local dev).
"""

import os, hashlib, secrets

_DATABASE_URL = os.environ.get("DATABASE_URL")

if _DATABASE_URL:
    # PostgreSQL mode: import all DB helpers from the pool layer.
    # The function definitions below are still executed but guarded by _DATABASE_URL
    # checks at their start, so these imports take precedence.
    from backend.core.db import (                           # noqa: F401
        fetch_one, fetch_all, execute, execute_many,
        row_to_dict, rows_to_dicts,
    )
    import sqlite3  # still imported so the module doesn't crash on bare import
    DB_PATH = None
else:
    import sqlite3
    DB_PATH = os.environ.get(
        "SCHOOL_MIS_DB_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "school_mis.db"),
    )

# Roles are pure display labels — no logic, no permissions.
# All permission assignments live in the `role_permissions` DB table
# and are managed exclusively through the Roles & Access UI.
ROLES = {
    "superadmin":     {"label": "Platform Admin",   "color": "#DC2626"},
    "admin":          {"label": "Administrator",    "color": "#7C3AED"},
    "head_teacher":   {"label": "Head Teacher",     "color": "#059669"},
    "academic":       {"label": "Academic Officer", "color": "#0891B2"},
    "accountant":     {"label": "Accountant",       "color": "#DC2626"},
    "welfare_officer":{"label": "Welfare Officer",  "color": "#9333EA"},
    "storekeeper":    {"label": "Store Keeper",     "color": "#D97706"},
    "class_teacher":  {"label": "Class Teacher",    "color": "#2563EB"},
    "subject_teacher":{"label": "Subject Teacher",  "color": "#7C3AED"},
    "librarian":      {"label": "Librarian",        "color": "#F59E0B"},
    "nurse":          {"label": "Nurse",            "color": "#EC4899"},
    "student_portal": {"label": "Student",          "color": "#6366F1"},
    "parent_portal":  {"label": "Parent / Guardian","color": "#10B981"},
}

# Default role→permission mapping used ONLY for the initial DB seed.
# After first run the DB is the sole source of truth — edit via
# Roles & Access UI, never by changing this dict.
_DEFAULT_ROLE_PERMISSIONS = {
    "admin": ["*"],
    "head_teacher": [
        "student.view", "student.create", "student.edit", "student.promote",
        "teachers.view", "teachers.manage",
        "classes.view", "classes.manage",
        "timetable.view", "timetable.manage",
        "attendance.view", "attendance.mark",
        "grades.view", "grades.write", "grades.submit",
        "grades.approve", "grades.publish", "grades.change_request.review",
        "finance.view", "finance.structure.view", "finance.billing.generate",
        "finance.waiver.approve", "finance.report",
        "welfare.view", "welfare.classify", "welfare.edit",
        "welfare.verify", "welfare.sponsor.manage",
        "accounting.view", "accounting.report",
        "reports.view", "reports.academic", "reports.finance",
        "reports.welfare", "reports.inventory",
        "settings.view", "settings.school.manage",
        "settings.years.manage", "settings.users.manage",
        "library.view",
        "transport.view", "transport.manage", "transport.assign",
        "health.view", "health.record", "health.report",
        "homework.view", "leave.review", "audit.view",
        "enrollment.view", "enrollment.manage",
        "guardian.view", "guardian.manage",
        "report_cards.view", "report_cards.generate",
        "report_cards.publish", "report_cards.comment",
    ],
    "academic": [
        "student.view", "student.edit", "student.promote",
        "teachers.view", "teachers.manage",
        "classes.view", "classes.manage",
        "timetable.view", "timetable.manage",
        "attendance.view", "attendance.mark", "attendance.report",
        "grades.view", "grades.write", "grades.submit",
        "grades.approve", "grades.publish", "grades.change_request.review",
        "homework.view", "homework.assign", "leave.review",
        "reports.view", "reports.academic",
        "enrollment.view", "enrollment.manage",
        "guardian.view", "guardian.manage",
        "report_cards.view", "report_cards.generate",
        "report_cards.publish", "report_cards.comment",
        "settings.view", "settings.teachers.manage", "settings.years.manage",
    ],
    "accountant": [
        "student.view",
        "finance.view", "finance.structure.view",
        "finance.payment.record", "finance.payment.void",
        "finance.billing.generate", "finance.waiver.create", "finance.report",
        "accounting.view", "accounting.expense.record", "accounting.report",
        "transport.view",
        "reports.view", "reports.finance",
    ],
    "welfare_officer": [
        "student.view",
        "welfare.view", "welfare.classify", "welfare.edit",
        "welfare.verify", "welfare.sponsor.manage",
        "finance.waiver.create",
        "health.view", "reports.view", "reports.welfare",
    ],
    "storekeeper": [
        "student.view.eligibility",
        "inventory.view", "inventory.stock.add", "inventory.stock.adjust",
        "inventory.stock.manage", "inventory.issue", "inventory.return",
        "inventory.report", "reports.view", "reports.inventory",
    ],
    "class_teacher": [
        "student.view",
        "attendance.view", "attendance.mark",
        "grades.view", "grades.write", "grades.submit",
        "grades.change_request.create",
        "classes.view", "timetable.view",
        "guardian.view",
        "report_cards.view", "report_cards.comment",
        "homework.view", "homework.assign", "homework.grade",
        "leave.review",
        "reports.view", "reports.academic",
    ],
    "subject_teacher": [
        "student.view",
        "attendance.view", "attendance.mark",
        "grades.view", "grades.write", "grades.submit",
        "grades.change_request.create",
        "classes.view", "timetable.view", "report_cards.view",
        "homework.view", "homework.assign", "homework.grade",
        "reports.view",
    ],
    "librarian": [
        "student.view",
        "library.view", "library.checkout", "library.manage",
    ],
    "nurse": [
        "student.view",
        "health.view", "health.record", "health.report",
    ],
    "student_portal":  ["portal.student.grades", "portal.student.homework"],
    "parent_portal":   ["portal.parent.grades", "portal.parent.fees", "portal.parent.leave"],
}


def get_connection():
    if _DATABASE_URL:
        from backend.core.db import _get_conn
        return _get_conn()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def initialize_database():
    if _DATABASE_URL:
        from backend.pg_schema import run as _pg_run
        _pg_run()
        return
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS school_config (
        key TEXT PRIMARY KEY, value TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS academic_years (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL UNIQUE,
        start_date TEXT NOT NULL, end_date TEXT NOT NULL,
        is_current INTEGER DEFAULT 0)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL, last_name TEXT NOT NULL,
        gender TEXT CHECK(gender IN ('Male','Female','Other')),
        phone TEXT, email TEXT,
        role TEXT DEFAULT 'Teacher',
        qualification TEXT, hire_date TEXT,
        is_active INTEGER DEFAULT 1, notes TEXT,
        created_at TEXT DEFAULT (date('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'subject_teacher',
        teacher_id INTEGER REFERENCES teachers(id),
        full_name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        must_change_pw INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, grade_level INTEGER NOT NULL,
        academic_year_id INTEGER REFERENCES academic_years(id),
        teacher_id INTEGER REFERENCES teachers(id),
        capacity INTEGER DEFAULT 40, room TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission_no TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL, last_name TEXT NOT NULL,
        gender TEXT CHECK(gender IN ('Male','Female','Other')),
        date_of_birth TEXT,
        class_id INTEGER REFERENCES classes(id),
        parent_name TEXT, parent_phone TEXT, parent_email TEXT,
        address TEXT, photo_path TEXT,
        enrollment_date TEXT DEFAULT (date('now')),
        is_active INTEGER DEFAULT 1, notes TEXT,
        created_at TEXT DEFAULT (date('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, code TEXT UNIQUE,
        grade_level INTEGER)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS teacher_subjects (
        teacher_id INTEGER REFERENCES teachers(id),
        subject_id INTEGER REFERENCES subjects(id),
        class_id   INTEGER REFERENCES classes(id),
        PRIMARY KEY (teacher_id, subject_id, class_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER REFERENCES classes(id),
        subject_id INTEGER REFERENCES subjects(id),
        teacher_id INTEGER REFERENCES teachers(id),
        day_of_week TEXT CHECK(day_of_week IN ('Mon','Tue','Wed','Thu','Fri')),
        start_time TEXT, end_time TEXT)""")

    # ── Structured timetable (versions + periods + slots) ──────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS timetable_periods (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        period_no   INTEGER NOT NULL DEFAULT 0,
        start_time  TEXT NOT NULL,
        end_time    TEXT NOT NULL,
        is_break    INTEGER NOT NULL DEFAULT 0,
        sort_order  INTEGER NOT NULL DEFAULT 0)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS timetable_versions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        term_id          INTEGER,
        name             TEXT NOT NULL,
        status           TEXT NOT NULL DEFAULT 'draft'
                         CHECK(status IN ('draft','active','archived')),
        effective_from   TEXT,
        effective_to     TEXT,
        created_by       INTEGER REFERENCES users(id),
        created_at       TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS timetable_slots (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        version_id  INTEGER NOT NULL REFERENCES timetable_versions(id),
        class_id    INTEGER NOT NULL REFERENCES classes(id),
        subject_id  INTEGER NOT NULL REFERENCES subjects(id),
        teacher_id  INTEGER REFERENCES teachers(id),
        period_id   INTEGER NOT NULL REFERENCES timetable_periods(id),
        day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 1 AND 7),
        room        TEXT,
        notes       TEXT,
        UNIQUE(version_id, class_id, period_id, day_of_week))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id),
        class_id INTEGER REFERENCES classes(id),
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late','Excused')),
        notes TEXT,
        recorded_by INTEGER REFERENCES users(id),
        UNIQUE(student_id, date))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        academic_year_id INTEGER REFERENCES academic_years(id),
        term INTEGER CHECK(term IN (1,2,3)),
        start_date TEXT, end_date TEXT,
        status TEXT DEFAULT 'open' CHECK(status IN ('open','locked','published')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id),
        exam_id INTEGER NOT NULL REFERENCES exams(id),
        subject_id INTEGER NOT NULL REFERENCES subjects(id),
        score REAL, max_score REAL DEFAULT 100,
        grade_letter TEXT, remarks TEXT,
        entered_by INTEGER REFERENCES users(id),
        approved_by INTEGER REFERENCES users(id),
        status TEXT DEFAULT 'draft'
            CHECK(status IN ('draft','submitted_locked','approved')),
        UNIQUE(student_id, exam_id, subject_id))""")

    # Grade change requests — required for modifying locked/approved grades
    cur.execute("""CREATE TABLE IF NOT EXISTS grade_change_requests (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        grade_id        INTEGER NOT NULL REFERENCES grades(id),
        requested_by    INTEGER REFERENCES users(id),
        proposed_score  REAL,
        proposed_max    REAL DEFAULT 100,
        reason          TEXT NOT NULL,
        status          TEXT DEFAULT 'pending'
                        CHECK(status IN ('pending','approved','rejected')),
        reviewed_by     INTEGER REFERENCES users(id),
        review_note     TEXT,
        reviewed_at     TEXT,
        created_at      TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS result_approval_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        grade_id    INTEGER NOT NULL REFERENCES grades(id),
        from_status TEXT,
        to_status   TEXT,
        action      TEXT,
        actor_id    INTEGER REFERENCES users(id),
        comment     TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS grade_scales (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        grade_letter     TEXT NOT NULL,
        min_pct          REAL NOT NULL,
        max_pct          REAL NOT NULL,
        remarks          TEXT,
        UNIQUE(academic_year_id, grade_letter))""")

    # Period-based attendance for secondary schools
    cur.execute("""CREATE TABLE IF NOT EXISTS period_attendance (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id  INTEGER NOT NULL REFERENCES students(id),
        class_id    INTEGER REFERENCES classes(id),
        subject_id  INTEGER REFERENCES subjects(id),
        date        TEXT NOT NULL,
        period_no   INTEGER NOT NULL DEFAULT 1,
        status      TEXT NOT NULL CHECK(status IN ('Present','Absent','Late','Excused')),
        notes       TEXT,
        recorded_by INTEGER REFERENCES users(id),
        created_at  TEXT DEFAULT (datetime('now')),
        UNIQUE(student_id, date, subject_id, period_no))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fee_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, amount REAL NOT NULL,
        term INTEGER, description TEXT)""")

    # ── Finance domain ──────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS fee_structures (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        class_id         INTEGER REFERENCES classes(id),
        fee_type_id      INTEGER NOT NULL REFERENCES fee_types(id),
        amount           REAL NOT NULL,
        term             INTEGER CHECK(term IN (1,2,3)),
        due_date         TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS student_bills (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        fee_structure_id INTEGER NOT NULL REFERENCES fee_structures(id),
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        control_number   TEXT NOT NULL UNIQUE,
        amount_due       REAL NOT NULL,
        amount_paid      REAL NOT NULL DEFAULT 0,
        discount_amount  REAL NOT NULL DEFAULT 0,
        status           TEXT NOT NULL DEFAULT 'unpaid'
                         CHECK(status IN ('unpaid','partial','paid','waived')),
        due_date         TEXT,
        created_at       TEXT DEFAULT (datetime('now')),
        UNIQUE(student_id, fee_structure_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fee_payments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id          INTEGER REFERENCES student_bills(id),
        student_id       INTEGER NOT NULL REFERENCES students(id),
        fee_type_id      INTEGER REFERENCES fee_types(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        amount_paid      REAL NOT NULL,
        payment_date     TEXT NOT NULL DEFAULT (date('now')),
        control_number   TEXT,
        receipt_no       TEXT UNIQUE,
        payment_method   TEXT DEFAULT 'Cash'
                         CHECK(payment_method IN
                              ('Cash','Mobile Money','Bank Transfer','Cheque')),
        reference_no     TEXT,
        notes            TEXT,
        recorded_by      INTEGER REFERENCES users(id),
        created_at       TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fee_waivers (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        bill_id          INTEGER REFERENCES student_bills(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        waiver_type      TEXT NOT NULL
                         CHECK(waiver_type IN ('orphan_exemption','scholarship',
                                               'partial_discount','staff_child','other')),
        discount_percent REAL NOT NULL DEFAULT 100,
        approved_by      INTEGER REFERENCES users(id),
        reason           TEXT,
        created_at       TEXT DEFAULT (datetime('now')))""")

    # ── Welfare domain ──────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS welfare_records (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL UNIQUE REFERENCES students(id),
        category        TEXT NOT NULL
                        CHECK(category IN ('orphan','half_orphan','sponsored','vulnerable')),
        verified        INTEGER DEFAULT 0,
        verified_by     INTEGER REFERENCES users(id),
        verified_date   TEXT,
        sponsor_name    TEXT,
        sponsor_org     TEXT,
        support_type    TEXT
                        CHECK(support_type IN ('full_fees','partial','non_financial')),
        notes           TEXT,
        created_at      TEXT DEFAULT (datetime('now')))""")

    # ── Inventory domain ────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS inventory_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        category    TEXT CHECK(category IN
                        ('uniform','book','stationery','equipment','other')),
        unit        TEXT DEFAULT 'pcs',
        unit_price  REAL NOT NULL DEFAULT 0,
        stock_qty   INTEGER NOT NULL DEFAULT 0,
        reorder_qty INTEGER DEFAULT 5,
        is_active   INTEGER DEFAULT 1)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS inventory_transactions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id     INTEGER NOT NULL REFERENCES inventory_items(id),
        type        TEXT NOT NULL
                    CHECK(type IN ('stock_in','issued','adjusted','returned')),
        qty         INTEGER NOT NULL,
        student_id  INTEGER REFERENCES students(id),
        bill_id     INTEGER REFERENCES student_bills(id),
        reference   TEXT,
        notes       TEXT,
        recorded_by INTEGER REFERENCES users(id),
        created_at  TEXT DEFAULT (datetime('now')))""")

    # ── Promotion domain ────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS student_promotions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        from_class_id    INTEGER REFERENCES classes(id),
        to_class_id      INTEGER REFERENCES classes(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        action           TEXT NOT NULL CHECK(action IN ('promote','hold_back','graduate')),
        notes            TEXT,
        promoted_by      INTEGER REFERENCES users(id),
        created_at       TEXT DEFAULT (datetime('now')))""")

    # ── Health / Infirmary domain ────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS health_visits (
        id                       INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id               INTEGER NOT NULL REFERENCES students(id),
        visit_date               TEXT NOT NULL DEFAULT (date('now')),
        visit_time               TEXT,
        symptoms                 TEXT,
        diagnosis                TEXT,
        treatment                TEXT,
        action_taken             TEXT
                                 CHECK(action_taken IN
                                      ('treated','referred','sent_home','rest','other')),
        referred_to              TEXT,
        parent_notified          INTEGER DEFAULT 0,
        parent_notification_note TEXT,
        nurse_name               TEXT,
        created_by               INTEGER REFERENCES users(id),
        created_at               TEXT DEFAULT (datetime('now')))""")

    # ── Transport domain ────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS transport_routes (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL,
        description  TEXT,
        vehicle_no   TEXT,
        driver_name  TEXT,
        driver_phone TEXT,
        fare_term1   REAL DEFAULT 0,
        fare_term2   REAL DEFAULT 0,
        fare_term3   REAL DEFAULT 0,
        is_active    INTEGER DEFAULT 1,
        created_at   TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS transport_subscriptions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        route_id         INTEGER NOT NULL REFERENCES transport_routes(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        term             INTEGER CHECK(term IN (1,2,3)),
        status           TEXT NOT NULL DEFAULT 'active'
                         CHECK(status IN ('active','cancelled')),
        notes            TEXT,
        assigned_by      INTEGER REFERENCES users(id),
        created_at       TEXT DEFAULT (datetime('now')),
        UNIQUE(student_id, route_id, academic_year_id, term))""")

    # ── Library domain ──────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS library_books (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        title            TEXT NOT NULL,
        author           TEXT,
        isbn             TEXT,
        category         TEXT DEFAULT 'other'
                         CHECK(category IN ('textbook','fiction','reference','non_fiction','other')),
        shelf_location   TEXT,
        publisher        TEXT,
        year             TEXT,
        total_copies     INTEGER NOT NULL DEFAULT 1,
        available_copies INTEGER NOT NULL DEFAULT 1,
        notes            TEXT,
        is_active        INTEGER DEFAULT 1,
        created_at       TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS library_loans (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id         INTEGER NOT NULL REFERENCES library_books(id),
        borrower_type   TEXT NOT NULL CHECK(borrower_type IN ('student','teacher')),
        borrower_id     INTEGER NOT NULL,
        borrower_name   TEXT,
        issue_date      TEXT NOT NULL DEFAULT (date('now')),
        due_date        TEXT NOT NULL,
        return_date     TEXT,
        fine_amount     REAL DEFAULT 0,
        fine_paid       INTEGER DEFAULT 0,
        status          TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active','returned','overdue','lost')),
        notes           TEXT,
        issued_by       INTEGER REFERENCES users(id),
        returned_to     INTEGER REFERENCES users(id),
        created_at      TEXT DEFAULT (datetime('now')))""")

    # ── Accounting domain ───────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        category     TEXT NOT NULL
                     CHECK(category IN
                          ('salaries','utilities','supplies','maintenance',
                           'transport','welfare','other')),
        description  TEXT NOT NULL,
        amount       REAL NOT NULL,
        expense_date TEXT NOT NULL DEFAULT (date('now')),
        receipt_ref  TEXT,
        approved_by  INTEGER REFERENCES users(id),
        recorded_by  INTEGER REFERENCES users(id),
        created_at   TEXT DEFAULT (datetime('now')))""")

    # ── Grade status migration: 'submitted' → 'submitted_locked' ───────────────
    # Runs once; recreates grades table with updated CHECK constraint + renames data.
    _g_migrated = cur.execute(
        "SELECT 1 FROM school_config WHERE key='grade_status_v2'"
    ).fetchone()
    if not _g_migrated:
        try:
            cur.execute("ALTER TABLE grades RENAME TO _grades_old")
            cur.execute("""CREATE TABLE grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id),
                exam_id INTEGER NOT NULL REFERENCES exams(id),
                subject_id INTEGER NOT NULL REFERENCES subjects(id),
                score REAL, max_score REAL DEFAULT 100,
                grade_letter TEXT, remarks TEXT,
                entered_by INTEGER REFERENCES users(id),
                approved_by INTEGER REFERENCES users(id),
                status TEXT DEFAULT 'draft'
                    CHECK(status IN ('draft','submitted_locked','approved')),
                UNIQUE(student_id, exam_id, subject_id))""")
            cur.execute("""INSERT INTO grades
                SELECT id, student_id, exam_id, subject_id, score, max_score,
                       grade_letter, remarks, entered_by, approved_by,
                       CASE WHEN status='submitted' THEN 'submitted_locked' ELSE status END
                FROM _grades_old""")
            cur.execute("DROP TABLE _grades_old")
        except Exception:
            try: cur.execute("ALTER TABLE _grades_old RENAME TO grades")
            except Exception: pass
        cur.execute(
            "INSERT OR REPLACE INTO school_config(key,value) VALUES('grade_status_v2','1')"
        )

    # ── Migrate existing tables (safe — skips if column already exists) ────────
    _migrations = [
        ("students",     "student_category", "TEXT DEFAULT 'regular'"),
        ("students",     "sponsor_name",     "TEXT"),
        ("students",     "sponsor_org",      "TEXT"),
        ("fee_payments", "bill_id",          "INTEGER"),
        ("fee_payments", "control_number",   "TEXT"),
        ("fee_payments", "reference_no",     "TEXT"),
        ("fee_payments", "created_at",       "TEXT DEFAULT (datetime('now'))"),
        ("audit_log",    "before_state",     "TEXT"),
        ("audit_log",    "after_state",      "TEXT"),
        ("subjects",        "credit_hours",     "INTEGER DEFAULT 1"),
        ("subjects",        "subject_type",     "TEXT DEFAULT 'compulsory'"),
        ("fee_structures",  "student_id",       "INTEGER REFERENCES students(id)"),
        ("fee_structures",  "student_type",     "TEXT"),
        ("students",        "student_type",     "TEXT DEFAULT 'Day'"),
        ("fee_payments",    "status",           "TEXT DEFAULT 'confirmed'"),
        ("fee_payments",    "confirmed_by",     "INTEGER REFERENCES users(id)"),
        ("fee_payments",    "confirmed_at",     "TEXT"),
    ]
    for table, col, col_type in _migrations:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # column already exists

    # ── Portal account linkage tables ─────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS student_portal_accounts (
        user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL UNIQUE REFERENCES students(id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS parent_portal_accounts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES students(id),
        relation   TEXT DEFAULT 'Parent',
        UNIQUE(user_id, student_id))""")

    # ── Homework tables ───────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS homework_assignments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id    INTEGER REFERENCES classes(id),
        subject_id  INTEGER REFERENCES subjects(id),
        teacher_id  INTEGER REFERENCES teachers(id),
        title       TEXT NOT NULL,
        description TEXT,
        deadline    TEXT NOT NULL,
        max_points  REAL DEFAULT 10,
        created_by  INTEGER REFERENCES users(id),
        created_at  TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS homework_submissions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL REFERENCES homework_assignments(id),
        student_id    INTEGER NOT NULL REFERENCES students(id),
        file_path     TEXT,
        notes         TEXT,
        submitted_at  TEXT DEFAULT (datetime('now')),
        status        TEXT DEFAULT 'submitted'
                      CHECK(status IN ('submitted','late','graded')),
        points_earned REAL,
        feedback      TEXT,
        graded_by     INTEGER REFERENCES users(id),
        graded_at     TEXT,
        UNIQUE(assignment_id, student_id))""")

    # ── Leave requests ────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS leave_requests (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id   INTEGER NOT NULL REFERENCES students(id),
        submitted_by INTEGER REFERENCES users(id),
        date_from    TEXT NOT NULL,
        date_to      TEXT NOT NULL,
        reason       TEXT NOT NULL,
        status       TEXT DEFAULT 'pending'
                     CHECK(status IN ('pending','approved','rejected')),
        reviewed_by  INTEGER REFERENCES users(id),
        review_note  TEXT,
        reviewed_at  TEXT,
        created_at   TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL, table_name TEXT, record_id INTEGER,
        detail TEXT,
        before_state TEXT, after_state TEXT,
        ts TEXT DEFAULT (datetime('now')))""")

    # ── RBAC tables ──────────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL,
        color TEXT DEFAULT '#6B7280',
        is_system INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        domain TEXT NOT NULL,
        action TEXT NOT NULL,
        description TEXT,
        scope_type TEXT DEFAULT 'GLOBAL'
            CHECK(scope_type IN ('GLOBAL','SCHOOL','CLASS','DEPARTMENT','OWN')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS role_permissions (
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
        PRIMARY KEY (role_id, permission_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_roles (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        granted_by INTEGER REFERENCES users(id),
        granted_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, role_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_scopes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        scope_type TEXT NOT NULL
            CHECK(scope_type IN ('GLOBAL','SCHOOL','CLASS','DEPARTMENT','OWN')),
        scope_value TEXT,
        permission_code TEXT,
        created_at TEXT DEFAULT (datetime('now')))""")

    # ── Policy override table ─────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS policy_overrides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_rule  TEXT NOT NULL,
        entity_type  TEXT NOT NULL,
        entity_id    INTEGER NOT NULL,
        decision     TEXT NOT NULL CHECK(decision IN ('allow','deny')),
        reason       TEXT,
        granted_by   INTEGER REFERENCES users(id),
        expires_at   TEXT,
        created_at   TEXT DEFAULT (datetime('now')),
        UNIQUE(policy_rule, entity_type, entity_id))""")

    # ── Direct user permission overrides ──────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS user_permission_overrides (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        permission  TEXT NOT NULL,
        effect      TEXT NOT NULL CHECK(effect IN ('ALLOW','DENY')),
        reason      TEXT,
        granted_by  INTEGER REFERENCES users(id),
        expires_at  TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, permission))""")

    # ── Teacher subject+class assignments (user-based, not teacher record) ────
    cur.execute("""CREATE TABLE IF NOT EXISTS teacher_assignments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_id         INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        subject_id       INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        academic_year_id INTEGER REFERENCES academic_years(id),
        is_active        INTEGER NOT NULL DEFAULT 1,
        assigned_by      INTEGER REFERENCES users(id),
        assigned_at      TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, class_id, subject_id, academic_year_id))""")

    # ── Class teacher assignments (one teacher responsible for a whole class) ─
    cur.execute("""CREATE TABLE IF NOT EXISTS class_teacher_assignments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_id         INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        academic_year_id INTEGER REFERENCES academic_years(id),
        is_active        INTEGER NOT NULL DEFAULT 1,
        assigned_by      INTEGER REFERENCES users(id),
        assigned_at      TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, class_id, academic_year_id))""")

    # ── Advanced finance tables ────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS locked_periods (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        term             INTEGER,
        locked_by        INTEGER REFERENCES users(id),
        locked_at        TEXT DEFAULT (datetime('now')),
        note             TEXT,
        UNIQUE(academic_year_id, term))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS late_fee_rules (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        fee_type_id      INTEGER REFERENCES fee_types(id),
        days_after_due   INTEGER NOT NULL DEFAULT 7,
        charge_type      TEXT NOT NULL DEFAULT 'percent'
                         CHECK(charge_type IN ('fixed','percent')),
        charge_amount    REAL NOT NULL,
        max_charge       REAL,
        is_active        INTEGER DEFAULT 1,
        created_at       TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS payment_schedules (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        bill_id          INTEGER NOT NULL REFERENCES student_bills(id),
        installment_no   INTEGER NOT NULL,
        due_date         TEXT NOT NULL,
        amount_due       REAL NOT NULL,
        amount_paid      REAL NOT NULL DEFAULT 0,
        status           TEXT DEFAULT 'unpaid'
                         CHECK(status IN ('unpaid','partial','paid')),
        created_at       TEXT DEFAULT (datetime('now')),
        UNIQUE(bill_id, installment_no))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS pending_approvals (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type      TEXT NOT NULL,
        payload          TEXT NOT NULL,
        description      TEXT,
        requested_by     INTEGER REFERENCES users(id),
        approved_by      INTEGER REFERENCES users(id),
        status           TEXT DEFAULT 'pending'
                         CHECK(status IN ('pending','approved','rejected')),
        note             TEXT,
        created_at       TEXT DEFAULT (datetime('now')),
        resolved_at      TEXT)""")

    # Seed school_type default if not set
    cur.execute(
        "INSERT OR IGNORE INTO school_config(key,value) VALUES('school_type','primary')"
    )

    # Seed default timetable periods (idempotent)
    cur.execute("SELECT COUNT(*) FROM timetable_periods")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO timetable_periods(name,period_no,start_time,end_time,is_break,sort_order) VALUES(?,?,?,?,?,?)",
            [
                ("Period 1",  1, "07:30", "08:10", 0, 1),
                ("Period 2",  2, "08:10", "08:50", 0, 2),
                ("Period 3",  3, "08:50", "09:30", 0, 3),
                ("Break",     0, "09:30", "09:50", 1, 4),
                ("Period 4",  4, "09:50", "10:30", 0, 5),
                ("Period 5",  5, "10:30", "11:10", 0, 6),
                ("Period 6",  6, "11:10", "11:50", 0, 7),
                ("Lunch",     0, "11:50", "12:30", 1, 8),
                ("Period 7",  7, "12:30", "13:10", 0, 9),
                ("Period 8",  8, "13:10", "13:50", 0, 10),
            ],
        )

    # Seed defaults on first run
    cur.execute("SELECT COUNT(*) FROM academic_years")
    if cur.fetchone()[0] == 0:
        cur.execute("""INSERT INTO academic_years(label,start_date,end_date,is_current)
            VALUES('2024/2025','2024-09-01','2025-07-31',1)""")
        cur.executemany("INSERT OR IGNORE INTO subjects(name,code) VALUES(?,?)", [
            ("Mathematics","MATH"),("English Language","ENG"),
            ("Kiswahili","KSW"),("Science","SCI"),
            ("Social Studies","SST"),("Religious Education","RE"),
            ("Physical Education","PE"),("Arts & Craft","ART"),
        ])

    # ── RBAC seed — idempotent, runs on every startup ────────────────────────
    # Granular permission registry (INSERT OR IGNORE — never removes existing codes)
    _ALL_PERMISSIONS = [
        # code,                         domain,       action,          description,                         scope
        ("*",                           "system",     "*",             "Full system access",                "GLOBAL"),
        # Student
        ("student.view",                "student",    "view",          "View student records",              "GLOBAL"),
        ("student.view.eligibility",    "student",    "eligibility",   "Eligibility check only (no PII)",   "GLOBAL"),
        ("student.create",              "student",    "create",        "Create student records",            "GLOBAL"),
        ("student.edit",                "student",    "edit",          "Edit student records",              "GLOBAL"),
        ("student.delete",              "student",    "delete",        "Delete/deactivate students",        "GLOBAL"),
        ("student.promote",             "student",    "promote",       "Promote students",                  "GLOBAL"),
        # Teachers
        ("teachers.view",               "teachers",   "view",          "View teacher records",              "GLOBAL"),
        ("teachers.manage",             "teachers",   "manage",        "Create and edit teachers",          "GLOBAL"),
        # Classes
        ("classes.view",                "classes",    "view",          "View class information",            "GLOBAL"),
        ("classes.manage",              "classes",    "manage",        "Create and edit classes",           "GLOBAL"),
        # Timetable
        ("timetable.view",              "timetable",  "view",          "View class timetables",             "GLOBAL"),
        ("timetable.manage",            "timetable",  "manage",        "Create and edit timetable slots",   "GLOBAL"),
        # Attendance
        ("attendance.view",             "attendance", "view",          "View attendance records",           "CLASS"),
        ("attendance.mark",             "attendance", "mark",          "Mark student attendance",           "CLASS"),
        ("attendance.edit",             "attendance", "edit",          "Edit past attendance",              "CLASS"),
        ("attendance.report",           "attendance", "report",        "Attendance reports",                "GLOBAL"),
        # Grades
        ("grades.view",                 "grades",     "view",          "View grades",                       "CLASS"),
        ("grades.enter",                "grades",     "enter",         "Enter and submit grades",           "CLASS"),
        ("grades.approve",              "grades",     "approve",       "Approve submitted grades",          "GLOBAL"),
        ("grades.publish",              "grades",     "publish",       "Publish approved grades",           "GLOBAL"),
        ("grades.change_request",       "grades",     "change_req",    "Submit grade change requests",       "GLOBAL"),
        ("grades.change_request.review","grades",     "change_review", "Approve/reject grade change requests","GLOBAL"),
        # Finance — granular, no wildcard for non-admin
        ("finance.view",                "finance",    "view",          "View billing and payment status",   "GLOBAL"),
        ("finance.structure.view",      "finance",    "struct.view",   "View fee structures",               "GLOBAL"),
        ("finance.structure.manage",    "finance",    "struct.manage", "Create/edit/delete fee structures", "GLOBAL"),
        ("finance.billing.generate",    "finance",    "billing",       "Run billing engine",                "GLOBAL"),
        ("finance.payment.record",      "finance",    "pay.record",    "Record fee payments",               "GLOBAL"),
        ("finance.payment.void",        "finance",    "pay.void",      "Void payments",                     "GLOBAL"),
        ("finance.waiver.create",       "finance",    "waiver.create", "Create fee waivers",                "GLOBAL"),
        ("finance.waiver.approve",      "finance",    "waiver.approve","Approve fee waivers",               "GLOBAL"),
        ("finance.report",              "finance",    "report",        "View financial reports",            "GLOBAL"),
        # Inventory — store keeper has these, but NOT student.view
        ("inventory.view",              "inventory",  "view",          "View inventory stock",              "GLOBAL"),
        ("inventory.stock.add",         "inventory",  "stock.add",     "Record incoming stock",             "GLOBAL"),
        ("inventory.stock.adjust",      "inventory",  "stock.adjust",  "Adjust stock levels",               "GLOBAL"),
        ("inventory.stock.manage",      "inventory",  "stock.manage",  "Manage inventory items",            "GLOBAL"),
        ("inventory.issue",             "inventory",  "issue",         "Issue items to students",           "GLOBAL"),
        ("inventory.return",            "inventory",  "return",        "Record item returns",               "GLOBAL"),
        ("inventory.report",            "inventory",  "report",        "View inventory reports",            "GLOBAL"),
        # Welfare
        ("welfare.view",                "welfare",    "view",          "View welfare records",              "GLOBAL"),
        ("welfare.classify",            "welfare",    "classify",      "Classify students",                 "GLOBAL"),
        ("welfare.edit",                "welfare",    "edit",          "Edit welfare records",              "GLOBAL"),
        ("welfare.verify",              "welfare",    "verify",        "Verify welfare status",             "GLOBAL"),
        ("welfare.sponsor.manage",      "welfare",    "sponsor",       "Manage sponsorships",               "GLOBAL"),
        # Accounting
        ("accounting.view",             "accounting", "view",          "View accounting records",           "GLOBAL"),
        ("accounting.expense.record",   "accounting", "expense",       "Record school expenses",            "GLOBAL"),
        ("accounting.report",           "accounting", "report",        "View accounting reports",           "GLOBAL"),
        # Reports
        ("reports.view",                "reports",    "view",          "Access reports module",             "GLOBAL"),
        ("reports.academic",            "reports",    "academic",      "Academic reports",                  "GLOBAL"),
        ("reports.finance",             "reports",    "finance",       "Finance reports",                   "GLOBAL"),
        ("reports.welfare",             "reports",    "welfare",       "Welfare reports",                   "GLOBAL"),
        ("reports.inventory",           "reports",    "inventory",     "Inventory reports",                 "GLOBAL"),
        # Settings
        ("settings.view",               "settings",   "view",          "View settings",                     "GLOBAL"),
        ("settings.school.manage",      "settings",   "school",        "Manage school info",                "GLOBAL"),
        ("settings.years.manage",       "settings",   "years",         "Manage academic years",             "GLOBAL"),
        ("settings.users.manage",       "settings",   "users",         "Manage all user accounts",          "GLOBAL"),
        ("settings.teachers.manage",    "settings",   "teachers",      "Create and manage teacher accounts","GLOBAL"),
        ("settings.roles.manage",       "settings",   "roles",         "Manage roles and permissions",      "GLOBAL"),
        # Library
        ("library.view",                "library",    "view",          "View library catalogue and loans",  "GLOBAL"),
        ("library.checkout",            "library",    "checkout",      "Issue and return books",            "GLOBAL"),
        ("library.manage",              "library",    "manage",        "Add, edit and deactivate books",    "GLOBAL"),
        # Transport
        ("transport.view",              "transport",  "view",          "View routes and subscriptions",     "GLOBAL"),
        ("transport.manage",            "transport",  "manage",        "Add and edit transport routes",     "GLOBAL"),
        ("transport.assign",            "transport",  "assign",        "Assign students to routes",         "GLOBAL"),
        # Health / Infirmary
        ("health.view",                 "health",     "view",          "View health visit records",         "GLOBAL"),
        ("health.record",               "health",     "record",        "Record health visits",              "GLOBAL"),
        ("health.report",               "health",     "report",        "View health reports",               "GLOBAL"),
        # Homework
        ("homework.view",               "homework",   "view",          "View homework assignments",         "CLASS"),
        ("homework.assign",             "homework",   "assign",        "Create homework assignments",       "CLASS"),
        ("homework.grade",              "homework",   "grade",         "Grade homework submissions",        "CLASS"),
        # Leave requests
        ("leave.review",                "leave",      "review",        "Review student leave requests",     "GLOBAL"),
        # Portal — student
        ("portal.student.grades",       "portal",     "student.grades",   "Student: view own approved grades", "OWN"),
        ("portal.student.homework",     "portal",     "student.homework", "Student: view and submit homework", "OWN"),
        # Portal — parent
        ("portal.parent.grades",        "portal",     "parent.grades",    "Parent: view children's grades",    "OWN"),
        ("portal.parent.fees",          "portal",     "parent.fees",      "Parent: view fee balances",         "OWN"),
        ("portal.parent.leave",         "portal",     "parent.leave",     "Parent: submit leave requests",     "OWN"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO permissions(code,domain,action,description,scope_type)"
        " VALUES(?,?,?,?,?)",
        _ALL_PERMISSIONS
    )

    # Upsert role display info (label/color only — no permissions here)
    for role_name, info in ROLES.items():
        cur.execute(
            "INSERT OR IGNORE INTO roles(name,label,color) VALUES(?,?,?)",
            (role_name, info["label"], info["color"])
        )
        cur.execute(
            "UPDATE roles SET label=?,color=? WHERE name=?",
            (info["label"], info["color"], role_name)
        )

    # Seed role_permissions ONCE from _DEFAULT_ROLE_PERMISSIONS.
    # After the first run the DB is the sole source of truth — all further
    # changes must be made through the Roles & Access UI.
    if cur.execute("SELECT COUNT(*) FROM role_permissions").fetchone()[0] == 0:
        for role_name, perm_codes in _DEFAULT_ROLE_PERMISSIONS.items():
            role_row = cur.execute(
                "SELECT id FROM roles WHERE name=?", (role_name,)
            ).fetchone()
            if not role_row:
                continue
            role_id = role_row[0]
            for perm_code in perm_codes:
                perm_row = cur.execute(
                    "SELECT id FROM permissions WHERE code=?", (perm_code,)
                ).fetchone()
                if perm_row:
                    cur.execute(
                        "INSERT OR IGNORE INTO role_permissions(role_id,permission_id)"
                        " VALUES(?,?)",
                        (role_id, perm_row[0])
                    )

    # NOTE: user_roles are intentionally NOT auto-seeded.
    # Roles are assigned explicitly via the Roles & Access page.

    conn.commit()
    conn.close()


# ── Auth helpers ──────────────────────────────────────────────────────────────
def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt

def verify_password(password, stored_hash, salt):
    h, _ = hash_password(password, salt)
    return h == stored_hash

def create_user(username, password, role, full_name, teacher_id=None, must_change=False):
    h, salt = hash_password(password)
    return execute("""INSERT INTO users(username,password_hash,salt,role,full_name,teacher_id,must_change_pw)
        VALUES(?,?,?,?,?,?,?)""", (username, h, salt, role, full_name, teacher_id, 1 if must_change else 0))

def authenticate(username: str, password: str):
    user = fetch_one("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
    if not user: return None
    if verify_password(password, user["password_hash"], user["salt"]):
        execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],))
        return dict(user)
    return None

# ── Config helpers ────────────────────────────────────────────────────────────
def get_config(key, default=None):
    row = fetch_one("SELECT value FROM school_config WHERE key=?", (key,))
    return row["value"] if row else default

def set_config(key, value):
    execute("INSERT INTO school_config(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value) if value is not None else ""))

def is_setup_complete():
    return get_config("setup_complete") == "1"

# ── Generic query helpers (SQLite only — PG versions imported at module top) ───
if not _DATABASE_URL:
    def fetch_all(sql, params=()):
        conn = get_connection()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def fetch_one(sql, params=()):
        conn = get_connection()
        row = conn.execute(sql, params).fetchone()
        conn.close()
        return row

    def execute(sql, params=()):
        conn = get_connection()
        cur = conn.execute(sql, params)
        conn.commit()
        last_id = cur.lastrowid
        conn.close()
        return last_id

    def execute_many(sql, data):
        conn = get_connection()
        conn.executemany(sql, data)
        conn.commit()
        conn.close()

    def row_to_dict(row):
        return dict(row) if row else None

    def rows_to_dicts(rows):
        return [dict(r) for r in rows]


def db_write(sql, params=(), action="", table="", record_id=None, detail="",
             user_id=None, before_state=None, after_state=None):
    """Write + audit in a single transaction. before/after_state accept dicts (stored as JSON)."""
    import json
    conn = get_connection()
    cur  = conn.execute(sql, params)
    rid  = cur.lastrowid
    if action:
        conn.execute(
            """INSERT INTO audit_log
               (user_id, action, table_name, record_id, detail, before_state, after_state)
               VALUES(?,?,?,?,?,?,?)""",
            (user_id, action, table, record_id or rid, detail,
             json.dumps(before_state) if before_state is not None else None,
             json.dumps(after_state)  if after_state  is not None else None)
        )
    conn.commit()
    conn.close()
    return rid


def db_write_audit(user_id, action, table_name=None, record_id=None,
                   detail="", before_state=None, after_state=None):
    """Write an audit entry without an accompanying data write."""
    import json
    conn = get_connection()
    conn.execute(
        """INSERT INTO audit_log
           (user_id, action, table_name, record_id, detail, before_state, after_state)
           VALUES(?,?,?,?,?,?,?)""",
        (user_id, action, table_name, record_id, detail,
         json.dumps(before_state) if before_state is not None else None,
         json.dumps(after_state)  if after_state  is not None else None)
    )
    conn.commit()
    conn.close()


def get_user_permissions(user_id: int) -> set[str]:
    """
    Returns the full set of permission codes for a user, loaded from DB
    (user_roles → role_permissions → permissions).
    Falls back to empty set if tables not yet seeded.
    """
    try:
        rows = fetch_all("""
            SELECT DISTINCT p.code FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id=ur.role_id
            JOIN permissions p ON p.id=rp.permission_id
            WHERE ur.user_id=?
        """, (user_id,))
        return {r["code"] for r in rows}
    except Exception:
        return set()


def sync_user_role(user_id: int, role_name: str):
    """Ensure user_roles row matches the users.role string (called on login)."""
    try:
        role_row = fetch_one("SELECT id FROM roles WHERE name=?", (role_name,))
        if not role_row:
            return
        execute(
            "INSERT OR IGNORE INTO user_roles(user_id,role_id) VALUES(?,?)",
            (user_id, role_row["id"])
        )
    except Exception:
        pass


def gen_control_number(student_admission: str, year_label: str, term: int, seq: int) -> str:
    yr = year_label.split("/")[0]
    adm = student_admission.replace(" ", "")
    return f"SCH-{yr}-{adm}-T{term}-{seq:03d}"


def gen_receipt_number() -> str:
    import datetime, random
    d = datetime.date.today().strftime("%Y%m%d")
    seq = random.randint(1, 9999)
    return f"RCP-{d}-{seq:04d}"
