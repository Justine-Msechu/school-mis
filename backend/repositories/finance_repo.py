"""
FinanceRepository — all data access for the finance domain.

Covers: student_bills, fee_payments, fee_structures, fee_types,
        fee_waivers, ledger_entries (new), expenses.
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from backend.repositories.base import BaseRepository
from backend.domain.finance.ledger import LedgerEntry
from backend.core.exceptions import NotFoundError, ConflictError


class FinanceRepository(BaseRepository):
    table = "fee_payments"

    # ── Bills ─────────────────────────────────────────────────────────────────

    def get_bill(self, bill_id: int) -> dict | None:
        return self._one(
            """SELECT sb.*,
                      s.first_name || ' ' || s.last_name AS student_name,
                      s.admission_no,
                      ft.name AS fee_type_name,
                      c.name  AS class_name
               FROM student_bills sb
               JOIN students s       ON s.id  = sb.student_id
               JOIN fee_structures fs ON fs.id = sb.fee_structure_id
               JOIN fee_types ft      ON ft.id = fs.fee_type_id
               LEFT JOIN classes c   ON c.id  = s.class_id
               WHERE sb.id = ?""",
            (bill_id,),
        )

    def get_student_bills(self, student_id: int, academic_year_id: int | None = None) -> list[dict]:
        where = "sb.student_id = ?"
        params: list = [student_id]
        if academic_year_id:
            where += " AND sb.academic_year_id = ?"
            params.append(academic_year_id)
        return self._q(
            f"""SELECT sb.*,
                       ft.name AS fee_type_name,
                       fs.term AS term,
                       ay.label AS year_label
                FROM student_bills sb
                JOIN fee_structures fs ON fs.id = sb.fee_structure_id
                JOIN fee_types ft      ON ft.id = fs.fee_type_id
                LEFT JOIN academic_years ay ON ay.id = sb.academic_year_id
                WHERE {where}
                ORDER BY sb.due_date DESC""",
            params,
        )

    def get_student_by_admission(self, admission_no: str) -> dict | None:
        return self._one(
            "SELECT * FROM students WHERE admission_no = ? AND is_active = 1",
            (admission_no.strip(),),
        )

    # ── Payments ──────────────────────────────────────────────────────────────

    def get_payment(self, payment_id: int) -> dict | None:
        return self._one(
            """SELECT fp.*,
                      s.first_name || ' ' || s.last_name AS student_name,
                      s.admission_no
               FROM fee_payments fp
               JOIN students s ON s.id = fp.student_id
               WHERE fp.id = ?""",
            (payment_id,),
        )

    def list_payments(
        self,
        student_id: int | None = None,
        academic_year_id: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        where = ["1=1"]
        params: list = []
        if student_id:
            where.append("fp.student_id = ?")
            params.append(student_id)
        if academic_year_id:
            where.append("fp.academic_year_id = ?")
            params.append(academic_year_id)
        params.append(limit)
        return self._q(
            f"""SELECT fp.*,
                       s.first_name || ' ' || s.last_name AS student_name,
                       s.admission_no,
                       ft.name AS fee_type_name
                FROM fee_payments fp
                JOIN students s ON s.id = fp.student_id
                LEFT JOIN fee_types ft ON ft.id = fp.fee_type_id
                WHERE {' AND '.join(where)}
                ORDER BY fp.payment_date DESC, fp.id DESC
                LIMIT ?""",
            params,
        )

    def insert_payment(self, data: dict) -> int:
        now = datetime.now(timezone.utc).isoformat()
        return self._exec(
            """INSERT INTO fee_payments
               (student_id, fee_type_id, academic_year_id, amount_paid,
                payment_date, receipt_no, payment_method, notes, recorded_by,
                bill_id, reference_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data["student_id"],
                data.get("fee_type_id"),
                data.get("academic_year_id"),
                data["amount"],
                data["payment_date"],
                data["receipt_no"],
                data.get("method", "cash"),
                data.get("notes", ""),
                data.get("recorded_by"),
                data.get("bill_id"),
                data.get("reference_no", ""),
                now,
            ),
        )

    def mark_payment_reversed(self, payment_id: int, reversed_by: int, reason: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """UPDATE fee_payments
               SET notes = notes || ' [REVERSED: ' || ? || '] by user ' || ? || ' at ' || ?
               WHERE id = ?""",
            (reason, reversed_by, now, payment_id),
        )

    # ── Bill status updates ───────────────────────────────────────────────────

    def update_bill_status(self, bill_id: int, new_status: str, amount_paid: float) -> None:
        self.conn.execute(
            "UPDATE student_bills SET status=?, amount_paid=? WHERE id=?",
            (new_status, amount_paid, bill_id),
        )

    # ── Ledger (new table) ────────────────────────────────────────────────────

    def insert_ledger_entries(self, entries: list[LedgerEntry]) -> None:
        """Insert all entries in the same transaction — caller must commit."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            """INSERT INTO ledger_entries
               (entry_date, account_code, account_name,
                debit_amount, credit_amount,
                reference_type, reference_id, description, posted_by, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    e.entry_date, e.account_code, e.account_name,
                    e.debit_amount, e.credit_amount,
                    e.reference_type, e.reference_id, e.description,
                    e.posted_by, now,
                )
                for e in entries
            ],
        )

    def get_ledger_summary(
        self,
        account_code: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        where = ["1=1"]
        params: list = []
        if account_code:
            where.append("account_code = ?")
            params.append(account_code)
        if from_date:
            where.append("entry_date >= ?")
            params.append(from_date)
        if to_date:
            where.append("entry_date <= ?")
            params.append(to_date)
        return self._q(
            f"""SELECT account_code, account_name,
                       SUM(debit_amount) AS total_debit,
                       SUM(credit_amount) AS total_credit,
                       SUM(debit_amount) - SUM(credit_amount) AS balance
                FROM ledger_entries
                WHERE {' AND '.join(where)}
                GROUP BY account_code, account_name
                ORDER BY account_code""",
            params,
        )

    def get_ledger_entries(
        self,
        reference_type: str | None = None,
        reference_id: int | None = None,
        limit: int = 200,
    ) -> list[dict]:
        where = ["1=1"]
        params: list = []
        if reference_type:
            where.append("reference_type = ?")
            params.append(reference_type)
        if reference_id:
            where.append("reference_id = ?")
            params.append(reference_id)
        params.append(limit)
        return self._q(
            f"""SELECT * FROM ledger_entries
                WHERE {' AND '.join(where)}
                ORDER BY entry_date DESC, id DESC
                LIMIT ?""",
            params,
        )

    # ── Receipt number generation ─────────────────────────────────────────────

    def next_receipt_no(self) -> str:
        from datetime import date
        year = date.today().year
        row = self._one(
            "SELECT MAX(CAST(SUBSTR(receipt_no, -6) AS INTEGER)) AS n FROM fee_payments WHERE receipt_no LIKE ?",
            (f"RCP-{year}-%",),
        )
        seq = (row["n"] or 0) + 1 if row else 1
        return f"RCP-{year}-{seq:06d}"

    # ── Fee structures ────────────────────────────────────────────────────────

    def list_fee_structures(self, academic_year_id: int | None = None) -> list[dict]:
        where = "1=1"
        params: list = []
        if academic_year_id:
            where = "fs.academic_year_id = ?"
            params.append(academic_year_id)
        return self._q(
            f"""SELECT fs.*, ft.name AS fee_type_name, ay.label AS year_label,
                       c.name AS class_name,
                       s.first_name || ' ' || s.last_name AS student_name,
                       s.admission_no
                FROM fee_structures fs
                JOIN fee_types ft ON ft.id = fs.fee_type_id
                LEFT JOIN academic_years ay ON ay.id = fs.academic_year_id
                LEFT JOIN classes c ON c.id = fs.class_id
                LEFT JOIN students s ON s.id = fs.student_id
                WHERE {where}
                ORDER BY ay.label DESC, ft.name""",
            params,
        )

    def list_fee_types(self) -> list[dict]:
        return self._q("SELECT * FROM fee_types ORDER BY name")

    # ── Expenses ──────────────────────────────────────────────────────────────

    def insert_expense(self, data: dict) -> int:
        now = datetime.now(timezone.utc).isoformat()
        return self._exec(
            """INSERT INTO expenses
               (category, description, amount, expense_date, receipt_ref, recorded_by, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                data.get("category", "General"),
                data["description"],
                data["amount"],
                data["expense_date"],
                data.get("reference", ""),
                data.get("recorded_by"),
                now,
            ),
        )

    def list_expenses(self, limit: int = 100) -> list[dict]:
        return self._q(
            """SELECT e.*, u.full_name AS recorder_name
               FROM expenses e
               LEFT JOIN users u ON u.id = e.recorded_by
               ORDER BY e.expense_date DESC, e.id DESC
               LIMIT ?""",
            (limit,),
        )

    # ── Financial summary ─────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        total_billed = (self._one("SELECT COALESCE(SUM(amount_due), 0) AS n FROM student_bills") or {}).get("n", 0)
        total_paid   = (self._one("SELECT COALESCE(SUM(amount_paid), 0) AS n FROM fee_payments") or {}).get("n", 0)
        total_exp    = (self._one("SELECT COALESCE(SUM(amount), 0) AS n FROM expenses") or {}).get("n", 0)
        return {
            "total_billed":    total_billed,
            "total_collected": total_paid,
            "balance":         total_billed - total_paid,
            "total_expenses":  total_exp,
        }
