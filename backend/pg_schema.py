"""
PostgreSQL schema initialisation — runs on every startup (all idempotent).
Creates all tables for a fresh install; migrations add columns as needed.
"""

from __future__ import annotations
import json
import logging

log = logging.getLogger(__name__)

# Every statement is CREATE TABLE IF NOT EXISTS or CREATE INDEX IF NOT EXISTS,
# so the full list is safe to execute on an already-initialised database.

_DDL: list[str] = [

    # ── Multi-tenant school registry ──────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS schools (
        id                  SERIAL PRIMARY KEY,
        name                TEXT    NOT NULL UNIQUE,
        subdomain           TEXT    UNIQUE,
        plan                TEXT    DEFAULT 'trial',
        max_users           INTEGER DEFAULT 50,
        is_active           INTEGER DEFAULT 1,
        created_at          TEXT    DEFAULT NOW()::text,
        notes               TEXT,
        subscription_status TEXT    DEFAULT 'pending',
        trial_ends          TEXT,
        email               TEXT,
        contact_phone       TEXT,
        admin_name          TEXT,
        school_type         TEXT    DEFAULT 'primary',
        school_ownership    TEXT    DEFAULT 'private',
        registration_number TEXT,
        school_address      TEXT,
        school_location     TEXT,
        country             TEXT    DEFAULT 'Tanzania',
        website             TEXT,
        login_header_message TEXT
    )""",

    # ── Configuration (per school) ────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS school_config (
        id        SERIAL PRIMARY KEY,
        key       TEXT NOT NULL,
        value     TEXT,
        school_id INTEGER REFERENCES schools(id),
        UNIQUE(key, school_id)
    )""",
    # Partial unique index so ON CONFLICT DO NOTHING works for global (school_id IS NULL) rows.
    # The composite UNIQUE(key, school_id) allows duplicate (key, NULL) pairs in PostgreSQL
    # because NULL != NULL — this index closes that gap.
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_school_config_global_key ON school_config(key) WHERE school_id IS NULL",

    # ── Academic calendar ─────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS academic_years (
        id        SERIAL PRIMARY KEY,
        label     TEXT    NOT NULL UNIQUE,
        start_date TEXT   NOT NULL,
        end_date   TEXT   NOT NULL,
        is_current INTEGER DEFAULT 0,
        school_id  INTEGER REFERENCES schools(id)
    )""",

    """CREATE TABLE IF NOT EXISTS terms (
        id               SERIAL PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        name             TEXT    NOT NULL,
        start_date       TEXT,
        end_date         TEXT,
        is_current       INTEGER NOT NULL DEFAULT 0,
        is_locked        INTEGER NOT NULL DEFAULT 0,
        created_at       TEXT    NOT NULL DEFAULT NOW()::text,
        UNIQUE(academic_year_id, name)
    )""",

    # ── Teachers ──────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS teachers (
        id                     SERIAL PRIMARY KEY,
        first_name             TEXT    NOT NULL,
        last_name              TEXT    NOT NULL,
        employee_no            TEXT    UNIQUE,
        gender                 TEXT    CHECK(gender IN ('Male','Female','Other')),
        date_of_birth          TEXT,
        phone                  TEXT,
        email                  TEXT,
        subject_specialization TEXT,
        role                   TEXT    DEFAULT 'Teacher',
        qualification          TEXT,
        joining_date           TEXT,
        hire_date              TEXT,
        is_active              INTEGER DEFAULT 1,
        notes                  TEXT,
        created_at             TEXT    DEFAULT CURRENT_DATE::text,
        deleted_at             TEXT
    )""",

    # ── Users ─────────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS users (
        id              SERIAL PRIMARY KEY,
        username        TEXT    UNIQUE NOT NULL,
        password_hash   TEXT    NOT NULL,
        salt            TEXT    NOT NULL,
        role            TEXT    NOT NULL DEFAULT 'subject_teacher',
        teacher_id      INTEGER REFERENCES teachers(id),
        full_name       TEXT    NOT NULL,
        is_active       INTEGER DEFAULT 1,
        must_change_pw  INTEGER DEFAULT 0,
        created_at      TEXT    DEFAULT NOW()::text,
        last_login      TEXT,
        school_id       INTEGER REFERENCES schools(id),
        pw_scheme       TEXT    DEFAULT 'sha256'
    )""",

    # ── Login sessions (persistent, DB-backed) ────────────────────────────────
    """CREATE TABLE IF NOT EXISTS login_sessions (
        id             SERIAL PRIMARY KEY,
        user_id        INTEGER NOT NULL REFERENCES users(id),
        session_token  TEXT    NOT NULL UNIQUE,
        token_hash     TEXT    UNIQUE,
        ip_address     TEXT,
        user_agent     TEXT,
        created_at     TEXT    NOT NULL DEFAULT NOW()::text,
        expires_at     TEXT    NOT NULL,
        invalidated_at TEXT,
        school_id      INTEGER,
        last_used_at   TEXT    DEFAULT NOW()::text,
        is_active      INTEGER DEFAULT 1
    )""",
    "CREATE INDEX IF NOT EXISTS idx_session_token    ON login_sessions(session_token)",
    "CREATE INDEX IF NOT EXISTS idx_session_user     ON login_sessions(user_id, invalidated_at)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_tk_hash ON login_sessions(token_hash)",

    # ── Rate limiting ─────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS rate_limit_log (
        id        SERIAL PRIMARY KEY,
        user_id   INTEGER NOT NULL,
        school_id INTEGER,
        endpoint  TEXT    NOT NULL DEFAULT 'api',
        ts        DOUBLE PRECISION NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_rll_user_ts ON rate_limit_log(user_id, ts)",

    # ── Classes ───────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS classes (
        id               SERIAL PRIMARY KEY,
        name             TEXT    NOT NULL,
        grade_level      INTEGER NOT NULL,
        academic_year_id INTEGER REFERENCES academic_years(id),
        teacher_id       INTEGER REFERENCES teachers(id),
        capacity         INTEGER DEFAULT 40,
        room             TEXT,
        deleted_at       TEXT
    )""",

    # ── Students ──────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS students (
        id               SERIAL PRIMARY KEY,
        admission_no     TEXT    UNIQUE NOT NULL,
        first_name       TEXT    NOT NULL,
        last_name        TEXT    NOT NULL,
        gender           TEXT    CHECK(gender IN ('Male','Female','Other')),
        date_of_birth    TEXT,
        class_id         INTEGER REFERENCES classes(id),
        parent_name      TEXT,
        parent_phone     TEXT,
        parent_email     TEXT,
        address          TEXT,
        photo_path       TEXT,
        enrollment_date  TEXT    DEFAULT CURRENT_DATE::text,
        is_active        INTEGER DEFAULT 1,
        notes            TEXT,
        created_at       TEXT    DEFAULT CURRENT_DATE::text,
        student_category TEXT    DEFAULT 'regular',
        sponsor_name     TEXT,
        sponsor_org      TEXT,
        student_type     TEXT    DEFAULT 'Day',
        deleted_at       TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_student_admission ON students(admission_no)",
    "CREATE INDEX IF NOT EXISTS idx_student_class     ON students(class_id, is_active)",

    # ── Subjects ──────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS subjects (
        id           SERIAL PRIMARY KEY,
        name         TEXT    NOT NULL,
        code         TEXT    UNIQUE,
        grade_level  INTEGER,
        credit_hours INTEGER DEFAULT 1,
        subject_type TEXT    DEFAULT 'compulsory',
        deleted_at   TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS teacher_subjects (
        teacher_id INTEGER REFERENCES teachers(id),
        subject_id INTEGER REFERENCES subjects(id),
        class_id   INTEGER REFERENCES classes(id),
        PRIMARY KEY (teacher_id, subject_id, class_id)
    )""",

    """CREATE TABLE IF NOT EXISTS class_subjects (
        id             SERIAL PRIMARY KEY,
        class_id       INTEGER NOT NULL REFERENCES classes(id),
        subject_id     INTEGER NOT NULL REFERENCES subjects(id),
        teacher_id     INTEGER REFERENCES teachers(id),
        weekly_periods INTEGER,
        created_at     TEXT    NOT NULL DEFAULT NOW()::text,
        UNIQUE(class_id, subject_id)
    )""",

    # ── Timetable ─────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS timetable (
        id         SERIAL PRIMARY KEY,
        class_id   INTEGER REFERENCES classes(id),
        subject_id INTEGER REFERENCES subjects(id),
        teacher_id INTEGER REFERENCES teachers(id),
        day_of_week TEXT CHECK(day_of_week IN ('Mon','Tue','Wed','Thu','Fri')),
        start_time TEXT,
        end_time   TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS timetable_periods (
        id         SERIAL PRIMARY KEY,
        name       TEXT    NOT NULL,
        period_no  INTEGER NOT NULL DEFAULT 0,
        start_time TEXT    NOT NULL,
        end_time   TEXT    NOT NULL,
        is_break   INTEGER NOT NULL DEFAULT 0,
        sort_order INTEGER NOT NULL DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS timetable_versions (
        id               SERIAL PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        term_id          INTEGER,
        name             TEXT    NOT NULL,
        status           TEXT    NOT NULL DEFAULT 'draft'
                         CHECK(status IN ('draft','active','archived')),
        effective_from   TEXT,
        effective_to     TEXT,
        created_by       INTEGER REFERENCES users(id),
        created_at       TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS timetable_slots (
        id          SERIAL PRIMARY KEY,
        version_id  INTEGER NOT NULL REFERENCES timetable_versions(id),
        class_id    INTEGER NOT NULL REFERENCES classes(id),
        subject_id  INTEGER NOT NULL REFERENCES subjects(id),
        teacher_id  INTEGER REFERENCES teachers(id),
        period_id   INTEGER NOT NULL REFERENCES timetable_periods(id),
        day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 1 AND 7),
        room        TEXT,
        notes       TEXT,
        UNIQUE(version_id, class_id, period_id, day_of_week)
    )""",

    # ── Attendance ────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS attendance (
        id          SERIAL PRIMARY KEY,
        student_id  INTEGER NOT NULL REFERENCES students(id),
        class_id    INTEGER REFERENCES classes(id),
        date        TEXT    NOT NULL,
        status      TEXT    NOT NULL CHECK(status IN ('Present','Absent','Late','Excused')),
        notes       TEXT,
        recorded_by INTEGER REFERENCES users(id),
        UNIQUE(student_id, date)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date, class_id)",

    """CREATE TABLE IF NOT EXISTS period_attendance (
        id          SERIAL PRIMARY KEY,
        student_id  INTEGER NOT NULL REFERENCES students(id),
        class_id    INTEGER REFERENCES classes(id),
        subject_id  INTEGER REFERENCES subjects(id),
        date        TEXT    NOT NULL,
        period_no   INTEGER NOT NULL DEFAULT 1,
        status      TEXT    NOT NULL CHECK(status IN ('Present','Absent','Late','Excused')),
        notes       TEXT,
        recorded_by INTEGER REFERENCES users(id),
        created_at  TEXT    DEFAULT NOW()::text,
        UNIQUE(student_id, date, subject_id, period_no)
    )""",

    # ── Grades / Exams ────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS exams (
        id               SERIAL PRIMARY KEY,
        name             TEXT    NOT NULL,
        academic_year_id INTEGER REFERENCES academic_years(id),
        term             INTEGER CHECK(term IN (1,2,3)),
        start_date       TEXT,
        end_date         TEXT,
        status           TEXT    DEFAULT 'open' CHECK(status IN ('open','locked','published'))
    )""",

    """CREATE TABLE IF NOT EXISTS grades (
        id           SERIAL PRIMARY KEY,
        student_id   INTEGER NOT NULL REFERENCES students(id),
        exam_id      INTEGER NOT NULL REFERENCES exams(id),
        subject_id   INTEGER NOT NULL REFERENCES subjects(id),
        score        DOUBLE PRECISION,
        max_score    DOUBLE PRECISION DEFAULT 100,
        grade_letter TEXT,
        remarks      TEXT,
        entered_by   INTEGER REFERENCES users(id),
        approved_by  INTEGER REFERENCES users(id),
        status       TEXT    DEFAULT 'draft'
                     CHECK(status IN ('draft','submitted_locked','approved')),
        UNIQUE(student_id, exam_id, subject_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_grades_exam_class ON grades(exam_id, subject_id)",

    """CREATE TABLE IF NOT EXISTS grade_change_requests (
        id             SERIAL PRIMARY KEY,
        grade_id       INTEGER NOT NULL REFERENCES grades(id),
        requested_by   INTEGER REFERENCES users(id),
        proposed_score DOUBLE PRECISION,
        proposed_max   DOUBLE PRECISION DEFAULT 100,
        reason         TEXT    NOT NULL,
        status         TEXT    DEFAULT 'pending'
                       CHECK(status IN ('pending','approved','rejected')),
        reviewed_by    INTEGER REFERENCES users(id),
        review_note    TEXT,
        reviewed_at    TEXT,
        created_at     TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS result_approval_log (
        id          SERIAL PRIMARY KEY,
        grade_id    INTEGER NOT NULL REFERENCES grades(id),
        from_status TEXT,
        to_status   TEXT,
        action      TEXT,
        actor_id    INTEGER REFERENCES users(id),
        comment     TEXT    DEFAULT '',
        created_at  TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS grade_scales (
        id               SERIAL PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        grade_letter     TEXT,
        label            TEXT,
        min_pct          DOUBLE PRECISION NOT NULL,
        max_pct          DOUBLE PRECISION NOT NULL,
        gpa_points       DOUBLE PRECISION DEFAULT 0,
        remarks          TEXT    DEFAULT ''
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_grade_scales_unique ON grade_scales(academic_year_id, COALESCE(grade_letter, label))",

    # ── Finance ───────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS fee_types (
        id          SERIAL PRIMARY KEY,
        name        TEXT    NOT NULL,
        amount      DOUBLE PRECISION NOT NULL,
        term        INTEGER,
        description TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS fee_structures (
        id               SERIAL PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        class_id         INTEGER REFERENCES classes(id),
        fee_type_id      INTEGER NOT NULL REFERENCES fee_types(id),
        amount           DOUBLE PRECISION NOT NULL,
        term             INTEGER CHECK(term IN (1,2,3)),
        due_date         TEXT,
        student_id       INTEGER REFERENCES students(id),
        student_type     TEXT,
        deleted_at       TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS student_bills (
        id               SERIAL PRIMARY KEY,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        fee_structure_id INTEGER NOT NULL REFERENCES fee_structures(id),
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        control_number   TEXT    NOT NULL UNIQUE,
        amount_due       DOUBLE PRECISION NOT NULL,
        amount_paid      DOUBLE PRECISION NOT NULL DEFAULT 0,
        discount_amount  DOUBLE PRECISION NOT NULL DEFAULT 0,
        status           TEXT    NOT NULL DEFAULT 'unpaid'
                         CHECK(status IN ('unpaid','partial','paid','waived')),
        due_date         TEXT,
        created_at       TEXT    DEFAULT NOW()::text,
        UNIQUE(student_id, fee_structure_id)
    )""",

    """CREATE TABLE IF NOT EXISTS fee_payments (
        id               SERIAL PRIMARY KEY,
        bill_id          INTEGER REFERENCES student_bills(id),
        student_id       INTEGER NOT NULL REFERENCES students(id),
        fee_type_id      INTEGER REFERENCES fee_types(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        amount_paid      DOUBLE PRECISION NOT NULL,
        payment_date     TEXT    NOT NULL DEFAULT CURRENT_DATE::text,
        control_number   TEXT,
        receipt_no       TEXT    UNIQUE,
        payment_method   TEXT    DEFAULT 'Cash'
                         CHECK(payment_method IN ('Cash','Mobile Money','Bank Transfer','Cheque')),
        reference_no     TEXT,
        notes            TEXT,
        recorded_by      INTEGER REFERENCES users(id),
        created_at       TEXT    DEFAULT NOW()::text,
        status           TEXT    DEFAULT 'confirmed',
        confirmed_by     INTEGER REFERENCES users(id),
        confirmed_at     TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_payments_student ON fee_payments(student_id, payment_date)",

    """CREATE TABLE IF NOT EXISTS fee_waivers (
        id               SERIAL PRIMARY KEY,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        bill_id          INTEGER REFERENCES student_bills(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        waiver_type      TEXT    NOT NULL
                         CHECK(waiver_type IN ('orphan_exemption','scholarship',
                                               'partial_discount','staff_child','other')),
        discount_percent DOUBLE PRECISION NOT NULL DEFAULT 100,
        approved_by      INTEGER REFERENCES users(id),
        reason           TEXT,
        created_at       TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS locked_periods (
        id               SERIAL PRIMARY KEY,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        term             INTEGER,
        locked_by        INTEGER REFERENCES users(id),
        locked_at        TEXT    DEFAULT NOW()::text,
        note             TEXT,
        UNIQUE(academic_year_id, term)
    )""",

    """CREATE TABLE IF NOT EXISTS late_fee_rules (
        id             SERIAL PRIMARY KEY,
        fee_type_id    INTEGER REFERENCES fee_types(id),
        days_after_due INTEGER NOT NULL DEFAULT 7,
        charge_type    TEXT    NOT NULL DEFAULT 'percent'
                       CHECK(charge_type IN ('fixed','percent')),
        charge_amount  DOUBLE PRECISION NOT NULL,
        max_charge     DOUBLE PRECISION,
        is_active      INTEGER DEFAULT 1,
        created_at     TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS payment_schedules (
        id             SERIAL PRIMARY KEY,
        student_id     INTEGER NOT NULL REFERENCES students(id),
        bill_id        INTEGER NOT NULL REFERENCES student_bills(id),
        installment_no INTEGER NOT NULL,
        due_date       TEXT    NOT NULL,
        amount_due     DOUBLE PRECISION NOT NULL,
        amount_paid    DOUBLE PRECISION NOT NULL DEFAULT 0,
        status         TEXT    DEFAULT 'unpaid' CHECK(status IN ('unpaid','partial','paid')),
        created_at     TEXT    DEFAULT NOW()::text,
        UNIQUE(bill_id, installment_no)
    )""",

    """CREATE TABLE IF NOT EXISTS pending_approvals (
        id           SERIAL PRIMARY KEY,
        action_type  TEXT    NOT NULL,
        payload      TEXT    NOT NULL,
        description  TEXT,
        requested_by INTEGER REFERENCES users(id),
        approved_by  INTEGER REFERENCES users(id),
        status       TEXT    DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
        note         TEXT,
        created_at   TEXT    DEFAULT NOW()::text,
        resolved_at  TEXT
    )""",

    # ── Accounting ────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS expenses (
        id           SERIAL PRIMARY KEY,
        category     TEXT    NOT NULL
                     CHECK(category IN ('salaries','utilities','supplies','maintenance',
                                        'transport','welfare','other')),
        description  TEXT    NOT NULL,
        amount       DOUBLE PRECISION NOT NULL,
        expense_date TEXT    NOT NULL DEFAULT CURRENT_DATE::text,
        receipt_ref  TEXT,
        approved_by  INTEGER REFERENCES users(id),
        recorded_by  INTEGER REFERENCES users(id),
        created_at   TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS expense_categories (
        id           SERIAL PRIMARY KEY,
        name         TEXT    NOT NULL UNIQUE,
        account_code TEXT    NOT NULL DEFAULT 'EXPENSE',
        is_active    INTEGER NOT NULL DEFAULT 1
    )""",

    """CREATE TABLE IF NOT EXISTS ledger_entries (
        id             SERIAL PRIMARY KEY,
        entry_date     TEXT    NOT NULL,
        account_code   TEXT    NOT NULL,
        account_name   TEXT    NOT NULL,
        debit_amount   DOUBLE PRECISION NOT NULL DEFAULT 0,
        credit_amount  DOUBLE PRECISION NOT NULL DEFAULT 0,
        reference_type TEXT    NOT NULL,
        reference_id   INTEGER NOT NULL,
        description    TEXT    NOT NULL DEFAULT '',
        posted_by      INTEGER REFERENCES users(id),
        created_at     TEXT    NOT NULL DEFAULT NOW()::text
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger_entries(entry_date, account_code)",
    "CREATE INDEX IF NOT EXISTS idx_ledger_ref  ON ledger_entries(reference_type, reference_id)",

    # ── Welfare ───────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS welfare_records (
        id            SERIAL PRIMARY KEY,
        student_id    INTEGER NOT NULL UNIQUE REFERENCES students(id),
        category      TEXT    NOT NULL
                      CHECK(category IN ('orphan','half_orphan','sponsored','vulnerable')),
        verified      INTEGER DEFAULT 0,
        verified_by   INTEGER REFERENCES users(id),
        verified_date TEXT,
        sponsor_name  TEXT,
        sponsor_org   TEXT,
        support_type  TEXT
                      CHECK(support_type IN ('full_fees','partial','non_financial')),
        notes         TEXT,
        created_at    TEXT    DEFAULT NOW()::text
    )""",

    # ── Inventory ─────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS inventory_items (
        id          SERIAL PRIMARY KEY,
        name        TEXT    NOT NULL,
        category    TEXT    CHECK(category IN ('uniform','book','stationery','equipment','other')),
        unit        TEXT    DEFAULT 'pcs',
        unit_price  DOUBLE PRECISION NOT NULL DEFAULT 0,
        stock_qty   INTEGER NOT NULL DEFAULT 0,
        reorder_qty INTEGER DEFAULT 5,
        is_active   INTEGER DEFAULT 1
    )""",

    """CREATE TABLE IF NOT EXISTS inventory_transactions (
        id          SERIAL PRIMARY KEY,
        item_id     INTEGER NOT NULL REFERENCES inventory_items(id),
        type        TEXT    NOT NULL
                    CHECK(type IN ('stock_in','issued','adjusted','returned')),
        qty         INTEGER NOT NULL,
        student_id  INTEGER REFERENCES students(id),
        bill_id     INTEGER REFERENCES student_bills(id),
        reference   TEXT,
        notes       TEXT,
        recorded_by INTEGER REFERENCES users(id),
        created_at  TEXT    DEFAULT NOW()::text
    )""",

    # ── Promotions ────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS student_promotions (
        id               SERIAL PRIMARY KEY,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        from_class_id    INTEGER REFERENCES classes(id),
        to_class_id      INTEGER REFERENCES classes(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        action           TEXT    NOT NULL CHECK(action IN ('promote','hold_back','graduate')),
        notes            TEXT,
        promoted_by      INTEGER REFERENCES users(id),
        created_at       TEXT    DEFAULT NOW()::text
    )""",

    # ── Health ────────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS health_visits (
        id                       SERIAL PRIMARY KEY,
        student_id               INTEGER NOT NULL REFERENCES students(id),
        visit_date               TEXT    NOT NULL DEFAULT CURRENT_DATE::text,
        visit_time               TEXT,
        symptoms                 TEXT,
        diagnosis                TEXT,
        treatment                TEXT,
        action_taken             TEXT
                                 CHECK(action_taken IN ('treated','referred','sent_home','rest','other')),
        referred_to              TEXT,
        parent_notified          INTEGER DEFAULT 0,
        parent_notification_note TEXT,
        nurse_name               TEXT,
        created_by               INTEGER REFERENCES users(id),
        created_at               TEXT    DEFAULT NOW()::text
    )""",

    # ── Transport ─────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS transport_routes (
        id           SERIAL PRIMARY KEY,
        name         TEXT    NOT NULL,
        description  TEXT,
        vehicle_no   TEXT,
        driver_name  TEXT,
        driver_phone TEXT,
        fare_term1   DOUBLE PRECISION DEFAULT 0,
        fare_term2   DOUBLE PRECISION DEFAULT 0,
        fare_term3   DOUBLE PRECISION DEFAULT 0,
        is_active    INTEGER DEFAULT 1,
        created_at   TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS transport_subscriptions (
        id               SERIAL PRIMARY KEY,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        route_id         INTEGER NOT NULL REFERENCES transport_routes(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        term             INTEGER CHECK(term IN (1,2,3)),
        status           TEXT    NOT NULL DEFAULT 'active' CHECK(status IN ('active','cancelled')),
        notes            TEXT,
        assigned_by      INTEGER REFERENCES users(id),
        created_at       TEXT    DEFAULT NOW()::text,
        UNIQUE(student_id, route_id, academic_year_id, term)
    )""",

    # ── Library ───────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS library_books (
        id               SERIAL PRIMARY KEY,
        title            TEXT    NOT NULL,
        author           TEXT,
        isbn             TEXT,
        category         TEXT    DEFAULT 'other'
                         CHECK(category IN ('textbook','fiction','reference','non_fiction','other')),
        shelf_location   TEXT,
        publisher        TEXT,
        year             TEXT,
        total_copies     INTEGER NOT NULL DEFAULT 1,
        available_copies INTEGER NOT NULL DEFAULT 1,
        notes            TEXT,
        is_active        INTEGER DEFAULT 1,
        created_at       TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS library_loans (
        id            SERIAL PRIMARY KEY,
        book_id       INTEGER NOT NULL REFERENCES library_books(id),
        borrower_type TEXT    NOT NULL CHECK(borrower_type IN ('student','teacher')),
        borrower_id   INTEGER NOT NULL,
        borrower_name TEXT,
        issue_date    TEXT    NOT NULL DEFAULT CURRENT_DATE::text,
        due_date      TEXT    NOT NULL,
        return_date   TEXT,
        fine_amount   DOUBLE PRECISION DEFAULT 0,
        fine_paid     INTEGER DEFAULT 0,
        status        TEXT    NOT NULL DEFAULT 'active'
                      CHECK(status IN ('active','returned','overdue','lost')),
        notes         TEXT,
        issued_by     INTEGER REFERENCES users(id),
        returned_to   INTEGER REFERENCES users(id),
        created_at    TEXT    DEFAULT NOW()::text
    )""",

    # ── Portal accounts ───────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS student_portal_accounts (
        user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL UNIQUE REFERENCES students(id)
    )""",

    """CREATE TABLE IF NOT EXISTS parent_portal_accounts (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES students(id),
        relation   TEXT    DEFAULT 'Parent',
        UNIQUE(user_id, student_id)
    )""",

    # ── Homework ──────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS homework_assignments (
        id          SERIAL PRIMARY KEY,
        class_id    INTEGER REFERENCES classes(id),
        subject_id  INTEGER REFERENCES subjects(id),
        teacher_id  INTEGER REFERENCES teachers(id),
        title       TEXT    NOT NULL,
        description TEXT,
        deadline    TEXT    NOT NULL,
        max_points  DOUBLE PRECISION DEFAULT 10,
        created_by  INTEGER REFERENCES users(id),
        created_at  TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS homework_submissions (
        id            SERIAL PRIMARY KEY,
        assignment_id INTEGER NOT NULL REFERENCES homework_assignments(id),
        student_id    INTEGER NOT NULL REFERENCES students(id),
        file_path     TEXT,
        notes         TEXT,
        submitted_at  TEXT    DEFAULT NOW()::text,
        status        TEXT    DEFAULT 'submitted'
                      CHECK(status IN ('submitted','late','graded')),
        points_earned DOUBLE PRECISION,
        feedback      TEXT,
        graded_by     INTEGER REFERENCES users(id),
        graded_at     TEXT,
        UNIQUE(assignment_id, student_id)
    )""",

    # ── Leave requests ────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS leave_requests (
        id           SERIAL PRIMARY KEY,
        student_id   INTEGER NOT NULL REFERENCES students(id),
        submitted_by INTEGER REFERENCES users(id),
        date_from    TEXT    NOT NULL,
        date_to      TEXT    NOT NULL,
        reason       TEXT    NOT NULL,
        status       TEXT    DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
        reviewed_by  INTEGER REFERENCES users(id),
        review_note  TEXT,
        reviewed_at  TEXT,
        created_at   TEXT    DEFAULT NOW()::text
    )""",

    # ── Audit log ─────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS audit_log (
        id           SERIAL PRIMARY KEY,
        user_id      INTEGER REFERENCES users(id),
        action       TEXT    NOT NULL,
        table_name   TEXT,
        record_id    INTEGER,
        detail       TEXT,
        before_state TEXT,
        after_state  TEXT,
        ts           TEXT    DEFAULT NOW()::text
    )""",
    "CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name, record_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_user  ON audit_log(user_id, ts)",

    # ── RBAC ──────────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS roles (
        id         SERIAL PRIMARY KEY,
        name       TEXT    UNIQUE NOT NULL,
        label      TEXT    NOT NULL,
        color      TEXT    DEFAULT '#6B7280',
        is_system  INTEGER DEFAULT 1,
        created_at TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS permissions (
        id          SERIAL PRIMARY KEY,
        code        TEXT    UNIQUE NOT NULL,
        domain      TEXT    NOT NULL,
        action      TEXT    NOT NULL,
        description TEXT,
        scope_type  TEXT    DEFAULT 'GLOBAL'
                    CHECK(scope_type IN ('GLOBAL','SCHOOL','CLASS','DEPARTMENT','OWN'))
    )""",

    """CREATE TABLE IF NOT EXISTS role_permissions (
        role_id       INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
        PRIMARY KEY (role_id, permission_id)
    )""",

    """CREATE TABLE IF NOT EXISTS user_roles (
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_id    INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        granted_by INTEGER REFERENCES users(id),
        granted_at TEXT    DEFAULT NOW()::text,
        PRIMARY KEY (user_id, role_id)
    )""",

    """CREATE TABLE IF NOT EXISTS user_scopes (
        id              SERIAL PRIMARY KEY,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        scope_type      TEXT    NOT NULL
                        CHECK(scope_type IN ('GLOBAL','SCHOOL','CLASS','DEPARTMENT','OWN')),
        scope_value     TEXT,
        permission_code TEXT,
        created_at      TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS policy_overrides (
        id          SERIAL PRIMARY KEY,
        policy_rule TEXT    NOT NULL,
        entity_type TEXT    NOT NULL,
        entity_id   INTEGER NOT NULL,
        decision    TEXT    NOT NULL CHECK(decision IN ('allow','deny')),
        reason      TEXT,
        granted_by  INTEGER REFERENCES users(id),
        expires_at  TEXT,
        created_at  TEXT    DEFAULT NOW()::text,
        UNIQUE(policy_rule, entity_type, entity_id)
    )""",

    """CREATE TABLE IF NOT EXISTS user_permission_overrides (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        permission TEXT    NOT NULL,
        effect     TEXT    NOT NULL CHECK(effect IN ('ALLOW','DENY')),
        reason     TEXT,
        granted_by INTEGER REFERENCES users(id),
        expires_at TEXT,
        created_at TEXT    DEFAULT NOW()::text,
        UNIQUE(user_id, permission)
    )""",

    """CREATE TABLE IF NOT EXISTS teacher_assignments (
        id               SERIAL PRIMARY KEY,
        user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_id         INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        subject_id       INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        academic_year_id INTEGER REFERENCES academic_years(id),
        is_active        INTEGER NOT NULL DEFAULT 1,
        assigned_by      INTEGER REFERENCES users(id),
        assigned_at      TEXT    DEFAULT NOW()::text,
        UNIQUE(user_id, class_id, subject_id, academic_year_id)
    )""",

    """CREATE TABLE IF NOT EXISTS class_teacher_assignments (
        id               SERIAL PRIMARY KEY,
        user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_id         INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        academic_year_id INTEGER REFERENCES academic_years(id),
        is_active        INTEGER NOT NULL DEFAULT 1,
        assigned_by      INTEGER REFERENCES users(id),
        assigned_at      TEXT    DEFAULT NOW()::text,
        UNIQUE(user_id, class_id, academic_year_id)
    )""",

    # ── Payroll ───────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS payroll_salary_config (
        id              SERIAL PRIMARY KEY,
        teacher_id      INTEGER NOT NULL UNIQUE REFERENCES teachers(id) ON DELETE CASCADE,
        basic_salary    DOUBLE PRECISION NOT NULL DEFAULT 0,
        housing_allow   DOUBLE PRECISION NOT NULL DEFAULT 0,
        transport_allow DOUBLE PRECISION NOT NULL DEFAULT 0,
        other_allow     DOUBLE PRECISION NOT NULL DEFAULT 0,
        loan_deduction  DOUBLE PRECISION NOT NULL DEFAULT 0,
        loan_board      INTEGER NOT NULL DEFAULT 0,
        notes           TEXT,
        updated_at      TEXT,
        updated_by      INTEGER
    )""",

    """CREATE TABLE IF NOT EXISTS payroll_runs (
        id           SERIAL PRIMARY KEY,
        month        INTEGER NOT NULL,
        year         INTEGER NOT NULL,
        label        TEXT    NOT NULL,
        status       TEXT    NOT NULL DEFAULT 'draft',
        created_at   TEXT    NOT NULL DEFAULT NOW()::text,
        created_by   INTEGER,
        finalized_at TEXT,
        finalized_by INTEGER,
        approved_at  TEXT,
        approved_by  INTEGER,
        UNIQUE(month, year)
    )""",

    """CREATE TABLE IF NOT EXISTS payroll_items (
        id               SERIAL PRIMARY KEY,
        run_id           INTEGER NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
        teacher_id       INTEGER NOT NULL REFERENCES teachers(id),
        basic_salary     DOUBLE PRECISION NOT NULL DEFAULT 0,
        housing_allow    DOUBLE PRECISION NOT NULL DEFAULT 0,
        transport_allow  DOUBLE PRECISION NOT NULL DEFAULT 0,
        other_allow      DOUBLE PRECISION NOT NULL DEFAULT 0,
        gross_pay        DOUBLE PRECISION NOT NULL DEFAULT 0,
        nssf_employee    DOUBLE PRECISION NOT NULL DEFAULT 0,
        nssf_employer    DOUBLE PRECISION NOT NULL DEFAULT 0,
        paye             DOUBLE PRECISION NOT NULL DEFAULT 0,
        loan_deduction   DOUBLE PRECISION NOT NULL DEFAULT 0,
        loan_board       DOUBLE PRECISION NOT NULL DEFAULT 0,
        total_deductions DOUBLE PRECISION NOT NULL DEFAULT 0,
        net_pay          DOUBLE PRECISION NOT NULL DEFAULT 0,
        UNIQUE(run_id, teacher_id)
    )""",

    """CREATE TABLE IF NOT EXISTS payroll_audit_log (
        id         SERIAL PRIMARY KEY,
        run_id     INTEGER NOT NULL REFERENCES payroll_runs(id),
        actor_id   INTEGER,
        action     TEXT    NOT NULL,
        note       TEXT,
        created_at TEXT    NOT NULL DEFAULT NOW()::text
    )""",

    # ── Notifications ─────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS notifications (
        id         SERIAL PRIMARY KEY,
        type       TEXT    NOT NULL,
        title      TEXT    NOT NULL,
        body       TEXT    NOT NULL DEFAULT '',
        data_json  TEXT,
        created_at TEXT    NOT NULL DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS notification_recipients (
        id              SERIAL PRIMARY KEY,
        notification_id INTEGER NOT NULL REFERENCES notifications(id),
        user_id         INTEGER NOT NULL REFERENCES users(id),
        read_at         TEXT,
        dismissed_at    TEXT,
        UNIQUE(notification_id, user_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_notif_user ON notification_recipients(user_id, read_at)",

    # ── Sync queue ────────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS sync_queue (
        id           SERIAL PRIMARY KEY,
        table_name   TEXT    NOT NULL,
        record_id    INTEGER NOT NULL,
        operation    TEXT    NOT NULL CHECK(operation IN ('INSERT','UPDATE','DELETE')),
        payload_json TEXT    NOT NULL,
        created_at   TEXT    NOT NULL DEFAULT NOW()::text,
        synced_at    TEXT,
        sync_error   TEXT,
        retry_count  INTEGER NOT NULL DEFAULT 0
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sync_pending ON sync_queue(synced_at)",

    # ── Subscriptions ─────────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS subscription_plans (
        id               TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        name             TEXT    NOT NULL,
        display_name     TEXT    NOT NULL,
        billing_interval TEXT    NOT NULL CHECK(billing_interval IN ('monthly','yearly')),
        price_amount     INTEGER NOT NULL,
        currency         TEXT    DEFAULT 'TZS',
        max_users        INTEGER NOT NULL,
        max_students     INTEGER NOT NULL,
        features         TEXT    DEFAULT '{}',
        is_active        INTEGER DEFAULT 1,
        sort_order       INTEGER DEFAULT 0,
        created_at       TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS subscriptions_v2 (
        id                       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        organization_id          INTEGER NOT NULL REFERENCES schools(id),
        plan_id                  TEXT    NOT NULL REFERENCES subscription_plans(id),
        status                   TEXT    NOT NULL DEFAULT 'pending',
        provider                 TEXT,
        provider_subscription_id TEXT,
        provider_customer_id     TEXT,
        current_period_start     TEXT,
        current_period_end       TEXT,
        trial_end                TEXT,
        cancel_at_period_end     INTEGER DEFAULT 0,
        canceled_at              TEXT,
        grace_period_days        INTEGER DEFAULT 7,
        grace_period_end         TEXT,
        pending_plan_id          TEXT    REFERENCES subscription_plans(id),
        metadata                 TEXT    DEFAULT '{}',
        created_at               TEXT    DEFAULT NOW()::text,
        updated_at               TEXT    DEFAULT NOW()::text
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sub2_org    ON subscriptions_v2(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_sub2_status ON subscriptions_v2(status)",
    "CREATE INDEX IF NOT EXISTS idx_sub2_period ON subscriptions_v2(current_period_end)",

    """CREATE TABLE IF NOT EXISTS sub_invoices (
        id                   TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        organization_id      INTEGER NOT NULL REFERENCES schools(id),
        subscription_id      TEXT    REFERENCES subscriptions_v2(id),
        provider             TEXT,
        provider_invoice_id  TEXT    UNIQUE,
        status               TEXT    NOT NULL DEFAULT 'open',
        amount_due           INTEGER NOT NULL,
        amount_paid          INTEGER DEFAULT 0,
        currency             TEXT    DEFAULT 'TZS',
        billing_period_start TEXT,
        billing_period_end   TEXT,
        due_date             TEXT,
        paid_at              TEXT,
        invoice_number       TEXT    UNIQUE,
        invoice_pdf_url      TEXT,
        notes                TEXT,
        metadata             TEXT    DEFAULT '{}',
        created_at           TEXT    DEFAULT NOW()::text,
        updated_at           TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS payments (
        id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        organization_id     INTEGER NOT NULL REFERENCES schools(id),
        invoice_id          TEXT    REFERENCES sub_invoices(id),
        subscription_id     TEXT    REFERENCES subscriptions_v2(id),
        provider            TEXT    NOT NULL,
        provider_payment_id TEXT    UNIQUE NOT NULL,
        status              TEXT    NOT NULL,
        amount              INTEGER NOT NULL,
        currency            TEXT    DEFAULT 'TZS',
        payment_method      TEXT,
        failure_code        TEXT,
        failure_reason      TEXT,
        metadata            TEXT    DEFAULT '{}',
        created_at          TEXT    DEFAULT NOW()::text
    )""",

    """CREATE TABLE IF NOT EXISTS webhook_events (
        id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        provider            TEXT    NOT NULL,
        event_id            TEXT    NOT NULL,
        event_type          TEXT    NOT NULL,
        raw_payload         TEXT    NOT NULL,
        parsed_payload      TEXT    NOT NULL,
        signature_header    TEXT,
        status              TEXT    DEFAULT 'pending',
        processing_attempts INTEGER DEFAULT 0,
        last_error          TEXT,
        processed_at        TEXT,
        ip_address          TEXT,
        created_at          TEXT    DEFAULT NOW()::text,
        UNIQUE(provider, event_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_wh_status ON webhook_events(status, created_at)",

    """CREATE TABLE IF NOT EXISTS subscription_history (
        id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        subscription_id TEXT    NOT NULL REFERENCES subscriptions_v2(id),
        organization_id INTEGER NOT NULL REFERENCES schools(id),
        event_type      TEXT    NOT NULL,
        from_status     TEXT,
        to_status       TEXT,
        from_plan_id    TEXT    REFERENCES subscription_plans(id),
        to_plan_id      TEXT    REFERENCES subscription_plans(id),
        triggered_by    TEXT    DEFAULT 'system',
        actor_user_id   INTEGER,
        webhook_event_id TEXT   REFERENCES webhook_events(id),
        notes           TEXT,
        metadata        TEXT    DEFAULT '{}',
        created_at      TEXT    DEFAULT NOW()::text
    )""",
    "CREATE INDEX IF NOT EXISTS idx_hist_org ON subscription_history(organization_id, created_at)",

    # ── Platform feature flags ────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS platform_feature_flags (
        id      SERIAL PRIMARY KEY,
        plan    TEXT    NOT NULL,
        module  TEXT    NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        UNIQUE(plan, module)
    )""",

    # ── Platform announcements ────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS platform_announcements (
        id          SERIAL PRIMARY KEY,
        title       TEXT    NOT NULL,
        body        TEXT    NOT NULL,
        priority    TEXT    NOT NULL DEFAULT 'normal',
        target_plan TEXT    NOT NULL DEFAULT 'all',
        created_at  TEXT    NOT NULL DEFAULT NOW()::text,
        expires_at  TEXT,
        is_active   INTEGER NOT NULL DEFAULT 1,
        created_by  INTEGER REFERENCES users(id)
    )""",
]

# ── Seed data ──────────────────────────────────────────────────────────────────

_EXPENSE_CATEGORIES = [
    ("Salaries",        "EXPENSE"),
    ("Utilities",       "EXPENSE"),
    ("Stationery",      "EXPENSE"),
    ("Maintenance",     "EXPENSE"),
    ("Transport",       "EXPENSE"),
    ("Food & Catering", "EXPENSE"),
    ("Equipment",       "EXPENSE"),
    ("Events",          "EXPENSE"),
    ("Other",           "EXPENSE"),
]

_TIMETABLE_PERIODS = [
    ("Period 1", 1, "07:30", "08:10", 0, 1),
    ("Period 2", 2, "08:10", "08:50", 0, 2),
    ("Period 3", 3, "08:50", "09:30", 0, 3),
    ("Break",    0, "09:30", "09:50", 1, 4),
    ("Period 4", 4, "09:50", "10:30", 0, 5),
    ("Period 5", 5, "10:30", "11:10", 0, 6),
    ("Period 6", 6, "11:10", "11:50", 0, 7),
    ("Lunch",    0, "11:50", "12:30", 1, 8),
    ("Period 7", 7, "12:30", "13:10", 0, 9),
    ("Period 8", 8, "13:10", "13:50", 0, 10),
]

_SUBJECTS_SEED = [
    ("Mathematics",       "MATH"),
    ("English Language",  "ENG"),
    ("Kiswahili",         "KSW"),
    ("Science",           "SCI"),
    ("Social Studies",    "SST"),
    ("Religious Education", "RE"),
    ("Physical Education","PE"),
    ("Arts & Craft",      "ART"),
]

_PLAN_MODULES = {
    "trial":    {"grades","attendance","finance","promotion",
                 "reports","enrollment","guardians","report_cards"},
    "basic":    {"grades","attendance","finance","promotion",
                 "reports","enrollment","guardians","report_cards","library","payroll"},
    "standard": {"grades","attendance","finance","promotion",
                 "reports","enrollment","guardians","report_cards","library","payroll",
                 "accounting","transport","inventory"},
    "premium":  {"grades","attendance","finance","library","accounting","transport",
                 "inventory","health","welfare","promotion","reports","enrollment",
                 "guardians","report_cards","payroll","ngo"},
}

_ALL_MODULES = list({m for s in _PLAN_MODULES.values() for m in s})


def run() -> None:
    """Create all tables and seed initial data. Safe to call on every startup."""
    from backend.core.db import execute, execute_many, fetch_one

    # 1. DDL
    for stmt in _DDL:
        try:
            execute(stmt)
        except Exception as exc:
            log.debug("Schema DDL skipped (%s): %.80s", exc, stmt.strip()[:80])

    # 2. Seed sequence counters for auto-generated IDs (idempotent)
    try:
        for seq_key in ("student_adm_seq", "teacher_emp_seq"):
            execute(
                "INSERT INTO school_config (key, value) VALUES (%s, '0')"
                " ON CONFLICT DO NOTHING",
                (seq_key,),
            )
    except Exception:
        pass

    # 3. Seed expense categories
    try:
        execute_many(
            "INSERT INTO expense_categories(name,account_code) VALUES(%s,%s)"
            " ON CONFLICT DO NOTHING",
            _EXPENSE_CATEGORIES,
        )
    except Exception:
        pass

    # 3. Seed timetable periods (only if empty)
    try:
        row = fetch_one("SELECT COUNT(*) AS cnt FROM timetable_periods")
        if row and row["cnt"] == 0:
            execute_many(
                "INSERT INTO timetable_periods(name,period_no,start_time,end_time,is_break,sort_order)"
                " VALUES(%s,%s,%s,%s,%s,%s)",
                _TIMETABLE_PERIODS,
            )
    except Exception:
        pass

    # 4. Seed academic year (only if empty)
    try:
        row = fetch_one("SELECT COUNT(*) AS cnt FROM academic_years")
        if row and row["cnt"] == 0:
            execute(
                "INSERT INTO academic_years(label,start_date,end_date,is_current)"
                " VALUES(%s,%s,%s,%s)",
                ("2024/2025", "2024-09-01", "2025-07-31", 1),
            )
            execute_many(
                "INSERT INTO subjects(name,code) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                _SUBJECTS_SEED,
            )
    except Exception:
        pass

    # 5. Seed platform feature flags
    try:
        for plan, enabled_set in _PLAN_MODULES.items():
            for module in _ALL_MODULES:
                enabled = 1 if module in enabled_set else 0
                execute(
                    "INSERT INTO platform_feature_flags(plan,module,enabled)"
                    " VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                    (plan, module, enabled),
                )
    except Exception:
        pass

    # 6. Seed subscription plans (if empty)
    try:
        row = fetch_one("SELECT COUNT(*) AS cnt FROM subscription_plans")
        if row and row["cnt"] == 0:
            plans = [
                ("basic",    "Basic",    "monthly", 50_000,    "TZS", 25,  300,  json.dumps({}), 1, 1),
                ("basic",    "Basic",    "yearly",  480_000,   "TZS", 25,  300,  json.dumps({}), 1, 1),
                ("standard", "Standard", "monthly", 100_000,   "TZS", 100, 1000, json.dumps({}), 1, 2),
                ("standard", "Standard", "yearly",  960_000,   "TZS", 100, 1000, json.dumps({}), 1, 2),
                ("premium",  "Premium",  "monthly", 200_000,   "TZS", 500, 5000, json.dumps({}), 1, 3),
                ("premium",  "Premium",  "yearly",  1_920_000, "TZS", 500, 5000, json.dumps({}), 1, 3),
            ]
            execute_many(
                "INSERT INTO subscription_plans"
                "(name,display_name,billing_interval,price_amount,currency,"
                " max_users,max_students,features,is_active,sort_order)"
                " VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                plans,
            )
    except Exception:
        pass

    # 7. Seed RBAC: permissions, roles, role→permission mapping
    try:
        from database.db import ROLES, _DEFAULT_ROLE_PERMISSIONS

        _ALL_PERMISSIONS = [
            ("*",                            "system",      "*",              "Full system access",                 "GLOBAL"),
            ("student.view",                 "student",     "view",           "View student records",               "GLOBAL"),
            ("student.view.eligibility",     "student",     "eligibility",    "Eligibility check only",             "GLOBAL"),
            ("student.create",               "student",     "create",         "Create student records",             "GLOBAL"),
            ("student.edit",                 "student",     "edit",           "Edit student records",               "GLOBAL"),
            ("student.delete",               "student",     "delete",         "Delete/deactivate students",         "GLOBAL"),
            ("student.promote",              "student",     "promote",        "Promote students",                   "GLOBAL"),
            ("teachers.view",                "teachers",    "view",           "View teacher records",               "GLOBAL"),
            ("teachers.manage",              "teachers",    "manage",         "Create and edit teachers",           "GLOBAL"),
            ("classes.view",                 "classes",     "view",           "View class information",             "GLOBAL"),
            ("classes.manage",               "classes",     "manage",         "Create and edit classes",            "GLOBAL"),
            ("timetable.view",               "timetable",   "view",           "View class timetables",              "GLOBAL"),
            ("timetable.manage",             "timetable",   "manage",         "Create and edit timetable slots",    "GLOBAL"),
            ("attendance.view",              "attendance",  "view",           "View attendance records",            "CLASS"),
            ("attendance.mark",              "attendance",  "mark",           "Mark student attendance",            "CLASS"),
            ("attendance.edit",              "attendance",  "edit",           "Edit past attendance",               "CLASS"),
            ("attendance.report",            "attendance",  "report",         "Attendance reports",                 "GLOBAL"),
            ("grades.view",                  "grades",      "view",           "View grades",                        "CLASS"),
            ("grades.enter",                 "grades",      "enter",          "Enter and submit grades",            "CLASS"),
            ("grades.write",                 "grades",      "write",          "Write grades",                       "CLASS"),
            ("grades.submit",                "grades",      "submit",         "Submit grades for approval",         "CLASS"),
            ("grades.approve",               "grades",      "approve",        "Approve submitted grades",           "GLOBAL"),
            ("grades.publish",               "grades",      "publish",        "Publish approved grades",            "GLOBAL"),
            ("grades.change_request",        "grades",      "change_req",     "Submit grade change requests",       "GLOBAL"),
            ("grades.change_request.create", "grades",      "change_create",  "Create grade change requests",       "GLOBAL"),
            ("grades.change_request.review", "grades",      "change_review",  "Approve grade change requests",      "GLOBAL"),
            ("finance.view",                 "finance",     "view",           "View billing and payment status",    "GLOBAL"),
            ("finance.structure.view",       "finance",     "struct.view",    "View fee structures",                "GLOBAL"),
            ("finance.structure.manage",     "finance",     "struct.manage",  "Create/edit fee structures",         "GLOBAL"),
            ("finance.billing.generate",     "finance",     "billing",        "Run billing engine",                 "GLOBAL"),
            ("finance.payment.record",       "finance",     "pay.record",     "Record fee payments",                "GLOBAL"),
            ("finance.payment.void",         "finance",     "pay.void",       "Void payments",                      "GLOBAL"),
            ("finance.waiver.create",        "finance",     "waiver.create",  "Create fee waivers",                 "GLOBAL"),
            ("finance.waiver.approve",       "finance",     "waiver.approve", "Approve fee waivers",                "GLOBAL"),
            ("finance.report",               "finance",     "report",         "View financial reports",             "GLOBAL"),
            ("inventory.view",               "inventory",   "view",           "View inventory stock",               "GLOBAL"),
            ("inventory.stock.add",          "inventory",   "stock.add",      "Record incoming stock",              "GLOBAL"),
            ("inventory.stock.adjust",       "inventory",   "stock.adjust",   "Adjust stock levels",                "GLOBAL"),
            ("inventory.stock.manage",       "inventory",   "stock.manage",   "Manage inventory items",             "GLOBAL"),
            ("inventory.issue",              "inventory",   "issue",          "Issue items to students",            "GLOBAL"),
            ("inventory.return",             "inventory",   "return",         "Record item returns",                "GLOBAL"),
            ("inventory.report",             "inventory",   "report",         "View inventory reports",             "GLOBAL"),
            ("welfare.view",                 "welfare",     "view",           "View welfare records",               "GLOBAL"),
            ("welfare.classify",             "welfare",     "classify",       "Classify students",                  "GLOBAL"),
            ("welfare.edit",                 "welfare",     "edit",           "Edit welfare records",               "GLOBAL"),
            ("welfare.verify",               "welfare",     "verify",         "Verify welfare status",              "GLOBAL"),
            ("welfare.sponsor.manage",       "welfare",     "sponsor",        "Manage sponsorships",                "GLOBAL"),
            ("accounting.view",              "accounting",  "view",           "View accounting records",            "GLOBAL"),
            ("accounting.expense.record",    "accounting",  "expense",        "Record school expenses",             "GLOBAL"),
            ("accounting.report",            "accounting",  "report",         "View accounting reports",            "GLOBAL"),
            ("reports.view",                 "reports",     "view",           "Access reports module",              "GLOBAL"),
            ("reports.academic",             "reports",     "academic",       "Academic reports",                   "GLOBAL"),
            ("reports.finance",              "reports",     "finance",        "Finance reports",                    "GLOBAL"),
            ("reports.welfare",              "reports",     "welfare",        "Welfare reports",                    "GLOBAL"),
            ("reports.inventory",            "reports",     "inventory",      "Inventory reports",                  "GLOBAL"),
            ("settings.view",                "settings",    "view",           "View settings",                      "GLOBAL"),
            ("settings.school.manage",       "settings",    "school",         "Manage school info",                 "GLOBAL"),
            ("settings.years.manage",        "settings",    "years",          "Manage academic years",              "GLOBAL"),
            ("settings.users.manage",        "settings",    "users",          "Manage all user accounts",           "GLOBAL"),
            ("settings.teachers.manage",     "settings",    "teachers",       "Create and manage teacher accounts", "GLOBAL"),
            ("settings.roles.manage",        "settings",    "roles",          "Manage roles and permissions",       "GLOBAL"),
            ("library.view",                 "library",     "view",           "View library catalogue",             "GLOBAL"),
            ("library.checkout",             "library",     "checkout",       "Issue and return books",             "GLOBAL"),
            ("library.manage",               "library",     "manage",         "Add and edit books",                 "GLOBAL"),
            ("transport.view",               "transport",   "view",           "View routes and subscriptions",      "GLOBAL"),
            ("transport.manage",             "transport",   "manage",         "Add and edit transport routes",      "GLOBAL"),
            ("transport.assign",             "transport",   "assign",         "Assign students to routes",          "GLOBAL"),
            ("health.view",                  "health",      "view",           "View health visit records",          "GLOBAL"),
            ("health.record",                "health",      "record",         "Record health visits",               "GLOBAL"),
            ("health.report",                "health",      "report",         "View health reports",                "GLOBAL"),
            ("homework.view",                "homework",    "view",           "View homework assignments",          "CLASS"),
            ("homework.assign",              "homework",    "assign",         "Create homework assignments",        "CLASS"),
            ("homework.write",               "homework",    "write",          "Write homework",                     "CLASS"),
            ("homework.grade",               "homework",    "grade",          "Grade homework submissions",         "CLASS"),
            ("leave.review",                 "leave",       "review",         "Review student leave requests",      "GLOBAL"),
            ("enrollment.view",              "enrollment",  "view",           "View enrollments",                   "GLOBAL"),
            ("enrollment.manage",            "enrollment",  "manage",         "Manage enrollments",                 "GLOBAL"),
            ("guardian.view",                "guardian",    "view",           "View guardian records",              "GLOBAL"),
            ("guardian.manage",              "guardian",    "manage",         "Manage guardian records",            "GLOBAL"),
            ("report_cards.view",            "report_cards","view",           "View report cards",                  "GLOBAL"),
            ("report_cards.generate",        "report_cards","generate",       "Generate report cards",              "GLOBAL"),
            ("report_cards.publish",         "report_cards","publish",        "Publish report cards",               "GLOBAL"),
            ("report_cards.comment",         "report_cards","comment",        "Add comments to report cards",       "GLOBAL"),
            ("audit.view",                   "audit",       "view",           "View audit log",                     "GLOBAL"),
            ("portal.student.grades",        "portal",      "student.grades",    "Student: view own grades",        "OWN"),
            ("portal.student.homework",      "portal",      "student.homework",  "Student: view and submit homework","OWN"),
            ("portal.parent.grades",         "portal",      "parent.grades",     "Parent: view children's grades",  "OWN"),
            ("portal.parent.fees",           "portal",      "parent.fees",       "Parent: view fee balances",       "OWN"),
            ("portal.parent.leave",          "portal",      "parent.leave",      "Parent: submit leave requests",   "OWN"),
        ]
        execute_many(
            "INSERT INTO permissions(code,domain,action,description,scope_type)"
            " VALUES(%s,%s,%s,%s,%s) ON CONFLICT(code) DO NOTHING",
            _ALL_PERMISSIONS,
        )

        for role_name, info in ROLES.items():
            execute(
                "INSERT INTO roles(name,label,color) VALUES(%s,%s,%s)"
                " ON CONFLICT(name) DO UPDATE SET label=EXCLUDED.label, color=EXCLUDED.color",
                (role_name, info["label"], info["color"]),
            )

        rp_count = fetch_one("SELECT COUNT(*) AS n FROM role_permissions")
        if rp_count and rp_count["n"] == 0:
            for role_name, perm_codes in _DEFAULT_ROLE_PERMISSIONS.items():
                role_row = fetch_one("SELECT id FROM roles WHERE name=%s", (role_name,))
                if not role_row:
                    continue
                role_id = role_row["id"]
                pairs = []
                for perm_code in perm_codes:
                    perm_row = fetch_one("SELECT id FROM permissions WHERE code=%s", (perm_code,))
                    if perm_row:
                        pairs.append((role_id, perm_row["id"]))
                if pairs:
                    execute_many(
                        "INSERT INTO role_permissions(role_id,permission_id)"
                        " VALUES(%s,%s) ON CONFLICT DO NOTHING",
                        pairs,
                    )
    except Exception as _e:
        log.warning("RBAC seed failed: %s", _e)

    log.info("PostgreSQL schema initialised")
