"""
services/finance_service.py — All finance business logic.

UI modules call these methods instead of touching the DB directly.
"""

from __future__ import annotations
from services.base import BaseService, ServiceError, PolicyViolation
from database.db import (
    fetch_one, fetch_all, execute, db_write,
    gen_receipt_number, gen_control_number,
)


class FinanceService(BaseService):

    # ── Payment recording ─────────────────────────────────────────────────────

    def get_bill_by_control(self, control_number: str) -> dict:
        """Look up a student bill by its control number. Raises ServiceError if not found."""
        bill = fetch_one("""
            SELECT sb.*,
                   s.first_name||' '||s.last_name AS student_name,
                   s.admission_no,
                   ft.name AS fee_name,
                   c.name  AS class_name
            FROM student_bills sb
            JOIN students s       ON s.id  = sb.student_id
            JOIN fee_structures fs ON fs.id = sb.fee_structure_id
            JOIN fee_types ft      ON ft.id = fs.fee_type_id
            LEFT JOIN classes c   ON c.id  = s.class_id
            WHERE sb.control_number = ?
        """, (control_number.strip(),))
        if not bill:
            raise ServiceError(f"No bill found for control number: {control_number}")
        return dict(bill)

    def record_payment(
        self,
        control_number: str,
        amount: float,
        method: str,
        payment_date: str,
        ref_no: str = "",
        notes: str = "",
        receipt_no: str | None = None,
    ) -> dict:
        """
        Record a fee payment against a bill.

        Flow:
          1. Look up bill by control number
          2. RBAC: require payment.record permission
          3. Policy: enforce all payment rules (waived, paid, overpayment, …)
          4. Write to fee_payments + update student_bills.status
          5. Audit log

        Returns dict with receipt_no, new_status, balance_remaining.
        """
        self._require_permission("finance.payment.record")

        bill = self.get_bill_by_control(control_number)

        # ── Policy enforcement ────────────────────────────────────────────────
        self._enforce(
            "payment.record",
            subject=bill,
            data={"amount": amount, "method": method},
        )

        # ── Write ─────────────────────────────────────────────────────────────
        rno = receipt_no or gen_receipt_number()
        new_paid   = bill["amount_paid"] + amount
        new_status = (
            "paid"
            if new_paid >= (bill["amount_due"] - bill["discount_amount"])
            else "partial"
        )

        payment_id = db_write(
            """INSERT INTO fee_payments
               (bill_id, student_id, academic_year_id, amount_paid,
                payment_date, control_number, receipt_no,
                payment_method, reference_no, notes, recorded_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                bill["id"], bill["student_id"], bill["academic_year_id"],
                amount, payment_date, bill["control_number"],
                rno, method, ref_no, notes, self._session.user_id,
            ),
            action="payment_recorded", table="fee_payments",
            detail=f"Receipt {rno} TZS {amount:,.0f}",
            user_id=self._session.user_id,
            after_state={
                "receipt_no": rno, "amount": amount,
                "method": method, "status": new_status,
            },
        )
        execute(
            "UPDATE student_bills SET amount_paid=?, status=? WHERE id=?",
            (new_paid, new_status, bill["id"]),
        )

        balance = max(bill["amount_due"] - new_paid - bill["discount_amount"], 0)
        return {
            "payment_id":       payment_id,
            "receipt_no":       rno,
            "new_status":       new_status,
            "balance_remaining": balance,
            "bill":             bill,
            "amount_paid":      amount,
            "student_name":     bill.get("student_name", ""),
            "admission_no":     bill.get("admission_no", ""),
            "class_name":       bill.get("class_name", "—"),
            "fee_name":         bill.get("fee_name", "—"),
            "payment_date":     payment_date,
            "method":           method,
            "ref_no":           ref_no,
        }

    # ── Fee structures ────────────────────────────────────────────────────────

    def create_fee_structure(
        self,
        academic_year_id: int,
        fee_type_id: int,
        amount: float,
        term: int,
        class_id: int | None = None,
        due_date: str | None = None,
    ) -> int:
        self._require_permission("finance.structure.manage")
        if amount <= 0:
            raise ServiceError("Fee amount must be greater than zero.")
        fs_id = execute(
            """INSERT INTO fee_structures
               (academic_year_id, class_id, fee_type_id, amount, term, due_date)
               VALUES (?,?,?,?,?,?)""",
            (academic_year_id, class_id, fee_type_id, amount, term, due_date),
        )
        self._audit("fee_structure_created", "fee_structures", fs_id,
                    detail=f"Amount TZS {amount:,.0f} term={term}")
        return fs_id

    def update_fee_structure(
        self,
        fs_id: int,
        academic_year_id: int,
        fee_type_id: int,
        amount: float,
        term: int | None,
        class_id: int | None = None,
        due_date: str | None = None,
    ) -> None:
        self._require_permission("finance.structure.manage")
        fs = fetch_one("SELECT * FROM fee_structures WHERE id=?", (fs_id,))
        if not fs:
            raise ServiceError("Fee structure not found.")
        has_payments = fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills sb "
            "JOIN fee_payments fp ON fp.bill_id=sb.id "
            "WHERE sb.fee_structure_id=?", (fs_id,)
        )
        self._enforce(
            "fee.structure.edit",
            subject={"id": fs_id, "has_payments": (has_payments and has_payments["n"] > 0)},
        )
        if amount <= 0:
            raise ServiceError("Fee amount must be greater than zero.")
        execute(
            """UPDATE fee_structures
               SET academic_year_id=?, class_id=?, fee_type_id=?,
                   amount=?, term=?, due_date=? WHERE id=?""",
            (academic_year_id, class_id, fee_type_id, amount, term, due_date, fs_id),
        )
        self._audit("fee_structure_updated", "fee_structures", fs_id,
                    before=dict(fs),
                    after={"amount": amount, "term": term})

    def delete_fee_structure(self, fs_id: int):
        self._require_permission("finance.structure.manage")
        fs = fetch_one("SELECT * FROM fee_structures WHERE id=?", (fs_id,))
        if not fs:
            raise ServiceError("Fee structure not found.")
        has_payments = fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills sb "
            "JOIN fee_payments fp ON fp.bill_id=sb.id "
            "WHERE sb.fee_structure_id=?", (fs_id,)
        )
        self._enforce(
            "fee.structure.delete",
            subject={"id": fs_id, "has_payments": (has_payments and has_payments["n"] > 0)},
        )
        execute("DELETE FROM fee_structures WHERE id=?", (fs_id,))
        self._audit("fee_structure_deleted", "fee_structures", fs_id,
                    before=dict(fs))

    # ── Billing engine ────────────────────────────────────────────────────────

    def run_billing(self, academic_year_id: int, term: int | None = None) -> dict:
        """
        Generate student_bills for all active students against fee structures
        for the given year and term. Orphan students get auto-waiver instead.

        Returns: {"billed": n, "waived": n, "skipped": n}
        """
        self._require_permission("finance.billing.generate")

        if term is not None:
            structures = fetch_all(
                "SELECT * FROM fee_structures WHERE academic_year_id=? AND term=?",
                (academic_year_id, term),
            )
        else:
            structures = fetch_all(
                "SELECT * FROM fee_structures WHERE academic_year_id=?",
                (academic_year_id,),
            )
        if not structures:
            raise ServiceError("No fee structures defined for this year/term.")

        year_row = fetch_one("SELECT label FROM academic_years WHERE id=?", (academic_year_id,))
        year_label = year_row["label"] if year_row else "2024/2025"

        students = fetch_all("SELECT * FROM students WHERE is_active=1")
        billed = waived = skipped = 0

        for student in students:
            # Check if orphan → skip billing, apply waiver
            is_orphan = student["student_category"] == "orphan"
            result = self._evaluate(
                "fee.bill_student",
                subject=dict(student),
                data={"term": term},
            )

            for fs in structures:
                # Only bill if structure applies to all classes or student's class
                if fs["class_id"] and fs["class_id"] != student["class_id"]:
                    continue

                seq = fetch_one(
                    "SELECT COUNT(*) AS n FROM student_bills WHERE fee_structure_id=?",
                    (fs["id"],)
                )["n"] + 1
                ctrl = gen_control_number(student["admission_no"], year_label, fs["term"] or 0, seq)

                # Check if bill already exists
                exists = fetch_one(
                    "SELECT id FROM student_bills WHERE student_id=? AND fee_structure_id=?",
                    (student["id"], fs["id"]),
                )
                if exists:
                    skipped += 1
                    continue

                if is_orphan or not result.allowed:
                    # Create bill + immediately waive it
                    bill_id = execute(
                        """INSERT INTO student_bills
                           (student_id, fee_structure_id, academic_year_id,
                            control_number, amount_due, discount_amount, status, due_date)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (student["id"], fs["id"], academic_year_id,
                         ctrl, fs["amount"], fs["amount"], "waived", fs["due_date"]),
                    )
                    execute(
                        """INSERT INTO fee_waivers
                           (student_id, bill_id, academic_year_id, waiver_type,
                            discount_percent, reason, approved_by)
                           VALUES (?,?,?,'orphan_exemption',100,'Auto: orphan exemption',?)""",
                        (student["id"], bill_id, academic_year_id, self._session.user_id),
                    )
                    waived += 1
                else:
                    execute(
                        """INSERT INTO student_bills
                           (student_id, fee_structure_id, academic_year_id,
                            control_number, amount_due, status, due_date)
                           VALUES (?,?,?,?,?,?,?)""",
                        (student["id"], fs["id"], academic_year_id,
                         ctrl, fs["amount"], "unpaid", fs["due_date"]),
                    )
                    billed += 1

        self._audit("billing_run", "student_bills",
                    detail=f"Year {year_label} T{term}: {billed} billed, {waived} waived, {skipped} skipped")
        return {"billed": billed, "waived": waived, "skipped": skipped}

    # ── Waivers ───────────────────────────────────────────────────────────────

    def apply_waiver(
        self,
        bill_id: int,
        waiver_type: str,
        discount_percent: float,
        reason: str = "",
    ) -> None:
        self._require_permission("finance.waiver.create")
        bill = fetch_one("SELECT * FROM student_bills WHERE id=?", (bill_id,))
        if not bill:
            raise ServiceError("Bill not found.")
        if discount_percent <= 0 or discount_percent > 100:
            raise ServiceError("Discount percent must be between 1 and 100.")

        discount_amount = bill["amount_due"] * discount_percent / 100
        new_status = "waived" if discount_percent >= 100 else bill["status"]

        execute(
            """INSERT OR REPLACE INTO fee_waivers
               (student_id, bill_id, academic_year_id, waiver_type,
                discount_percent, reason, approved_by)
               VALUES (?,?,?,?,?,?,?)""",
            (bill["student_id"], bill_id, bill["academic_year_id"],
             waiver_type, discount_percent, reason, self._session.user_id),
        )
        execute(
            "UPDATE student_bills SET discount_amount=?, status=? WHERE id=?",
            (discount_amount, new_status, bill_id),
        )
        self._audit("waiver_applied", "fee_waivers",
                    detail=f"Bill {bill_id}: {discount_percent}% {waiver_type}",
                    after={"discount_percent": discount_percent, "waiver_type": waiver_type})

    def apply_blanket_waiver(
        self,
        student_id: int,
        academic_year_id: int,
        waiver_type: str,
        discount_percent: float,
        reason: str = "",
    ) -> int:
        """Apply a waiver to all outstanding bills for a student. Returns count of bills updated."""
        self._require_permission("finance.waiver.create")
        if discount_percent <= 0 or discount_percent > 100:
            raise ServiceError("Discount percent must be between 1 and 100.")

        bills = fetch_all(
            "SELECT id, amount_due, amount_paid FROM student_bills "
            "WHERE student_id=? AND status IN ('unpaid','partial')",
            (student_id,),
        )

        execute(
            """INSERT INTO fee_waivers
               (student_id, bill_id, academic_year_id, waiver_type,
                discount_percent, reason, approved_by)
               VALUES (?,?,?,?,?,?,?)""",
            (student_id, None, academic_year_id,
             waiver_type, discount_percent, reason, self._session.user_id),
        )

        for bill in bills:
            discount = bill["amount_due"] * discount_percent / 100
            new_status = "waived" if discount_percent >= 100 else (
                "paid" if (bill["amount_paid"] + discount) >= bill["amount_due"] else "partial"
            )
            execute(
                "UPDATE student_bills SET discount_amount=?, status=? WHERE id=?",
                (discount, new_status, bill["id"]),
            )

        self._audit("blanket_waiver_applied", "fee_waivers",
                    detail=f"Student {student_id}: {discount_percent}% {waiver_type} on {len(bills)} bill(s)",
                    after={"discount_percent": discount_percent, "waiver_type": waiver_type})
        return len(bills)


# Singleton
finance_service = FinanceService()
