"""
Migration 009 — Payroll module tables.

Creates:
  payroll_salary_config  — per-employee salary settings
  payroll_runs           — monthly payroll runs
  payroll_items          — computed payslip per employee per run
  payroll_audit_log      — approval history
"""

from backend.core.db import execute


_TABLES = [
    """CREATE TABLE IF NOT EXISTS payroll_salary_config (
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
    )""",

    """CREATE TABLE IF NOT EXISTS payroll_runs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        month        INTEGER NOT NULL,
        year         INTEGER NOT NULL,
        label        TEXT    NOT NULL,
        status       TEXT    NOT NULL DEFAULT 'draft',
        created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
        created_by   INTEGER,
        finalized_at TEXT,
        finalized_by INTEGER,
        approved_at  TEXT,
        approved_by  INTEGER,
        UNIQUE(month, year)
    )""",

    """CREATE TABLE IF NOT EXISTS payroll_items (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id           INTEGER NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
        teacher_id       INTEGER NOT NULL REFERENCES teachers(id),
        basic_salary     REAL NOT NULL DEFAULT 0,
        housing_allow    REAL NOT NULL DEFAULT 0,
        transport_allow  REAL NOT NULL DEFAULT 0,
        other_allow      REAL NOT NULL DEFAULT 0,
        gross_pay        REAL NOT NULL DEFAULT 0,
        nssf_employee    REAL NOT NULL DEFAULT 0,
        nssf_employer    REAL NOT NULL DEFAULT 0,
        paye             REAL NOT NULL DEFAULT 0,
        loan_deduction   REAL NOT NULL DEFAULT 0,
        loan_board       REAL NOT NULL DEFAULT 0,
        total_deductions REAL NOT NULL DEFAULT 0,
        net_pay          REAL NOT NULL DEFAULT 0,
        UNIQUE(run_id, teacher_id)
    )""",

    """CREATE TABLE IF NOT EXISTS payroll_audit_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id     INTEGER NOT NULL REFERENCES payroll_runs(id),
        actor_id   INTEGER,
        action     TEXT    NOT NULL,
        note       TEXT,
        created_at TEXT    NOT NULL DEFAULT (datetime('now'))
    )""",
]

_PERMS = [
    ("payroll.view",    "payroll", "view",    "View payroll runs and payslips",        "GLOBAL"),
    ("payroll.manage",  "payroll", "manage",  "Configure salary and run payroll",      "GLOBAL"),
    ("payroll.approve", "payroll", "approve", "Approve / finalise payroll runs",       "GLOBAL"),
]


def run() -> None:
    for stmt in _TABLES:
        try:
            execute(stmt)
        except Exception:
            pass

    for perm in _PERMS:
        try:
            execute(
                "INSERT OR IGNORE INTO permissions(code,domain,action,description,scope_type)"
                " VALUES(?,?,?,?,?)",
                perm,
            )
        except Exception:
            pass
