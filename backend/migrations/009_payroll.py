"""
Migration 009 — Payroll module tables.

Creates:
  payroll_salary_config  — per-employee salary settings (basic salary, allowances, deductions)
  payroll_runs           — monthly payroll runs (one per month/year)
  payroll_items          — computed payslip per employee per run
  payroll_audit_log      — who approved/finalized what
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS payroll_salary_config (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id      INTEGER NOT NULL UNIQUE REFERENCES teachers(id) ON DELETE CASCADE,
            basic_salary    REAL    NOT NULL DEFAULT 0,
            housing_allow   REAL    NOT NULL DEFAULT 0,
            transport_allow REAL    NOT NULL DEFAULT 0,
            other_allow     REAL    NOT NULL DEFAULT 0,
            loan_deduction  REAL    NOT NULL DEFAULT 0,
            loan_board      INTEGER NOT NULL DEFAULT 0,
            notes           TEXT,
            updated_at      TEXT,
            updated_by      INTEGER
        );

        CREATE TABLE IF NOT EXISTS payroll_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            month       INTEGER NOT NULL,
            year        INTEGER NOT NULL,
            label       TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'draft',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            created_by  INTEGER,
            finalized_at TEXT,
            finalized_by INTEGER,
            approved_at  TEXT,
            approved_by  INTEGER,
            UNIQUE(month, year)
        );

        CREATE TABLE IF NOT EXISTS payroll_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          INTEGER NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
            teacher_id      INTEGER NOT NULL REFERENCES teachers(id),
            basic_salary    REAL NOT NULL DEFAULT 0,
            housing_allow   REAL NOT NULL DEFAULT 0,
            transport_allow REAL NOT NULL DEFAULT 0,
            other_allow     REAL NOT NULL DEFAULT 0,
            gross_pay       REAL NOT NULL DEFAULT 0,
            nssf_employee   REAL NOT NULL DEFAULT 0,
            nssf_employer   REAL NOT NULL DEFAULT 0,
            paye            REAL NOT NULL DEFAULT 0,
            loan_deduction  REAL NOT NULL DEFAULT 0,
            loan_board      REAL NOT NULL DEFAULT 0,
            total_deductions REAL NOT NULL DEFAULT 0,
            net_pay         REAL NOT NULL DEFAULT 0,
            UNIQUE(run_id, teacher_id)
        );

        CREATE TABLE IF NOT EXISTS payroll_audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL REFERENCES payroll_runs(id),
            actor_id    INTEGER,
            action      TEXT NOT NULL,
            note        TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    # Add payroll permissions to the permissions seed table if not present
    perms = [
        ("payroll.view",    "payroll", "view",    "View payroll runs and payslips", "GLOBAL"),
        ("payroll.manage",  "payroll", "manage",  "Configure salary and run payroll", "GLOBAL"),
        ("payroll.approve", "payroll", "approve", "Approve / finalise payroll runs", "GLOBAL"),
    ]
    for perm in perms:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO permissions (key, module, action, description, scope) VALUES (?,?,?,?,?)",
                perm,
            )
        except Exception:
            pass

    # Grant payroll permissions to admin and head_teacher by default
    for role in ("admin", "head_teacher", "accountant"):
        for perm_key in ("payroll.view", "payroll.manage", "payroll.approve"):
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_key, permission_key) VALUES (?,?)",
                    (role, perm_key),
                )
            except Exception:
                pass

    conn.commit()
