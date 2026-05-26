"""
Payroll calculation service — TZS, TRA 2024/25 rules.

PAYE bands (monthly taxable income):
  0 – 270,000       → 0%
  270,001 – 520,000 → 8%
  520,001 – 760,000 → 20%
  760,001 – 1,000,000 → 25%
  > 1,000,000       → 30%

NSSF: employee 10% of gross, employer 10% of gross.
Loan Board (HESLB): 15% of gross when loan_board flag is set.
"""

from __future__ import annotations
from datetime import datetime


PAYE_BANDS = [
    (270_000,   0.00),
    (520_000,   0.08),
    (760_000,   0.20),
    (1_000_000, 0.25),
    (float("inf"), 0.30),
]

NSSF_RATE      = 0.10
LOAN_BOARD_RATE = 0.15


def compute_paye(taxable: float) -> float:
    """Progressive PAYE on monthly taxable income (TZS)."""
    tax = 0.0
    prev = 0.0
    for ceiling, rate in PAYE_BANDS:
        if taxable <= prev:
            break
        band_income = min(taxable, ceiling) - prev
        tax += band_income * rate
        prev = ceiling
    return round(tax, 2)


def compute_payslip(
    basic_salary: float,
    housing_allow: float,
    transport_allow: float,
    other_allow: float,
    loan_deduction: float,
    loan_board: bool,
) -> dict:
    gross = basic_salary + housing_allow + transport_allow + other_allow

    nssf_employee = round(gross * NSSF_RATE, 2)
    nssf_employer = round(gross * NSSF_RATE, 2)

    # Taxable income = gross − NSSF employee share
    taxable = max(gross - nssf_employee, 0)
    paye = compute_paye(taxable)

    lb = round(gross * LOAN_BOARD_RATE, 2) if loan_board else 0.0

    total_deductions = nssf_employee + paye + loan_deduction + lb
    net_pay = round(gross - total_deductions, 2)

    return {
        "basic_salary":    round(basic_salary, 2),
        "housing_allow":   round(housing_allow, 2),
        "transport_allow": round(transport_allow, 2),
        "other_allow":     round(other_allow, 2),
        "gross_pay":       round(gross, 2),
        "nssf_employee":   nssf_employee,
        "nssf_employer":   nssf_employer,
        "paye":            paye,
        "loan_deduction":  round(loan_deduction, 2),
        "loan_board":      lb,
        "total_deductions": round(total_deductions, 2),
        "net_pay":         net_pay,
    }


class PayrollService:
    def __init__(self, conn):
        self._conn = conn

    # ── Salary config ──────────────────────────────────────────────────────────

    def upsert_salary_config(self, teacher_id: int, data: dict, actor_id: int) -> dict:
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            """INSERT INTO payroll_salary_config
                   (teacher_id, basic_salary, housing_allow, transport_allow,
                    other_allow, loan_deduction, loan_board, notes, updated_at, updated_by)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(teacher_id) DO UPDATE SET
                   basic_salary    = excluded.basic_salary,
                   housing_allow   = excluded.housing_allow,
                   transport_allow = excluded.transport_allow,
                   other_allow     = excluded.other_allow,
                   loan_deduction  = excluded.loan_deduction,
                   loan_board      = excluded.loan_board,
                   notes           = excluded.notes,
                   updated_at      = excluded.updated_at,
                   updated_by      = excluded.updated_by""",
            (
                teacher_id,
                data.get("basic_salary", 0),
                data.get("housing_allow", 0),
                data.get("transport_allow", 0),
                data.get("other_allow", 0),
                data.get("loan_deduction", 0),
                1 if data.get("loan_board") else 0,
                data.get("notes", ""),
                now,
                actor_id,
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM payroll_salary_config WHERE teacher_id=?", (teacher_id,)
        ).fetchone()
        return dict(row)

    # ── Payroll runs ──────────────────────────────────────────────────────────

    def create_run(self, month: int, year: int, actor_id: int) -> dict:
        import calendar
        label = f"{calendar.month_name[month]} {year}"
        cur = self._conn.execute(
            "INSERT INTO payroll_runs (month, year, label, status, created_by) VALUES (?,?,?,?,?)",
            (month, year, label, "draft", actor_id),
        )
        self._conn.commit()
        run_id = cur.lastrowid
        self._log(run_id, actor_id, "created", f"Payroll run created for {label}")
        return self._get_run(run_id)

    def compute_run(self, run_id: int, actor_id: int) -> int:
        run = self._get_run(run_id)
        if run["status"] == "approved":
            raise ValueError("Cannot recompute an approved payroll run")

        configs = self._conn.execute(
            """SELECT psc.*, t.id as teacher_id
               FROM payroll_salary_config psc
               JOIN teachers t ON t.id = psc.teacher_id
               WHERE t.deleted_at IS NULL AND t.is_active = 1"""
        ).fetchall()

        count = 0
        for cfg in configs:
            ps = compute_payslip(
                cfg["basic_salary"],
                cfg["housing_allow"],
                cfg["transport_allow"],
                cfg["other_allow"],
                cfg["loan_deduction"],
                bool(cfg["loan_board"]),
            )
            self._conn.execute(
                """INSERT INTO payroll_items
                       (run_id, teacher_id, basic_salary, housing_allow, transport_allow,
                        other_allow, gross_pay, nssf_employee, nssf_employer, paye,
                        loan_deduction, loan_board, total_deductions, net_pay)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(run_id, teacher_id) DO UPDATE SET
                       basic_salary     = excluded.basic_salary,
                       housing_allow    = excluded.housing_allow,
                       transport_allow  = excluded.transport_allow,
                       other_allow      = excluded.other_allow,
                       gross_pay        = excluded.gross_pay,
                       nssf_employee    = excluded.nssf_employee,
                       nssf_employer    = excluded.nssf_employer,
                       paye             = excluded.paye,
                       loan_deduction   = excluded.loan_deduction,
                       loan_board       = excluded.loan_board,
                       total_deductions = excluded.total_deductions,
                       net_pay          = excluded.net_pay""",
                (
                    run_id, cfg["teacher_id"],
                    ps["basic_salary"], ps["housing_allow"], ps["transport_allow"],
                    ps["other_allow"], ps["gross_pay"], ps["nssf_employee"],
                    ps["nssf_employer"], ps["paye"], ps["loan_deduction"],
                    ps["loan_board"], ps["total_deductions"], ps["net_pay"],
                ),
            )
            count += 1

        self._conn.commit()
        self._log(run_id, actor_id, "computed", f"Computed {count} payslips")
        return count

    def finalize_run(self, run_id: int, actor_id: int):
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "UPDATE payroll_runs SET status='finalized', finalized_at=?, finalized_by=? WHERE id=?",
            (now, actor_id, run_id),
        )
        self._conn.commit()
        self._log(run_id, actor_id, "finalized", "Payroll run finalized")

    def approve_run(self, run_id: int, actor_id: int):
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "UPDATE payroll_runs SET status='approved', approved_at=?, approved_by=? WHERE id=?",
            (now, actor_id, run_id),
        )
        self._conn.commit()
        self._log(run_id, actor_id, "approved", "Payroll run approved")
        # Post journal entry
        self._post_journal(run_id, actor_id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_run(self, run_id: int) -> dict:
        row = self._conn.execute(
            "SELECT * FROM payroll_runs WHERE id=?", (run_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Payroll run {run_id} not found")
        return dict(row)

    def _log(self, run_id: int, actor_id: int, action: str, note: str):
        try:
            self._conn.execute(
                "INSERT INTO payroll_audit_log (run_id, actor_id, action, note) VALUES (?,?,?,?)",
                (run_id, actor_id, action, note),
            )
            self._conn.commit()
        except Exception:
            pass

    def _post_journal(self, run_id: int, actor_id: int):
        """Post salary expense journal entries to the accounting ledger."""
        try:
            totals = self._conn.execute(
                """SELECT SUM(gross_pay) as gross, SUM(nssf_employer) as nssf_emp,
                          SUM(net_pay) as net
                   FROM payroll_items WHERE run_id=?""",
                (run_id,),
            ).fetchone()
            run = self._get_run(run_id)
            desc = f"Payroll — {run['label']}"
            # Salary expense debit
            self._conn.execute(
                """INSERT INTO ledger_entries (date, description, account, debit, credit, created_by)
                   VALUES (date('now'),?,?,?,?,?)""",
                (desc, "Salary Expense", round(totals["gross"] or 0, 2), 0, actor_id),
            )
            # Cash/Bank credit (net pay to staff)
            self._conn.execute(
                """INSERT INTO ledger_entries (date, description, account, debit, credit, created_by)
                   VALUES (date('now'),?,?,?,?,?)""",
                (desc, "Cash / Bank", 0, round(totals["net"] or 0, 2), actor_id),
            )
            # NSSF payable
            if totals["nssf_emp"]:
                self._conn.execute(
                    """INSERT INTO ledger_entries (date, description, account, debit, credit, created_by)
                       VALUES (date('now'),?,?,?,?,?)""",
                    (desc + " (NSSF Employer)", "NSSF Payable", 0, round(totals["nssf_emp"], 2), actor_id),
                )
            self._conn.commit()
        except Exception:
            pass  # accounting table may not exist yet in all DBs
