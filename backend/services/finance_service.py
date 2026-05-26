"""
FinanceService — business logic for the finance domain.

This is the authoritative service for the FastAPI layer.
All financial mutations go through here: they enforce business rules,
post double-entry ledger entries, emit events, and write audit records.
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone

from backend.core.exceptions import BusinessRuleError, ValidationError, NotFoundError
from backend.core.audit import AuditService
from backend.core.events import event_bus, Events
from backend.domain.finance.ledger import LedgerEngine
from backend.repositories.finance_repo import FinanceRepository


class FinanceService:
    def __init__(self, conn: sqlite3.Connection):
        self.repo  = FinanceRepository(conn)
        self.conn  = conn
        self.audit = AuditService(conn)
        self._ledger = LedgerEngine()

    # ── Payments ──────────────────────────────────────────────────────────────

    def record_payment(
        self,
        student_id: int,
        amount: float,
        method: str,
        payment_date: str,
        bill_id: int | None = None,
        fee_type_id: int | None = None,
        academic_year_id: int | None = None,
        reference_no: str = "",
        notes: str = "",
        actor: dict | None = None,
    ) -> dict:
        """
        Record a fee payment.

        Business rules enforced here:
          - Amount must be positive
          - If bill_id given, payment must not exceed outstanding balance
          - Receipt number is generated here (unique, sequential)

        After writing, posts double-entry ledger entries.
        """
        actor = actor or {}

        if amount <= 0:
            raise ValidationError("Payment amount must be greater than zero", field="amount")

        # Validate bill balance if bill_id given
        bill = None
        if bill_id:
            bill = self.repo.get_bill(bill_id)
            if not bill:
                raise NotFoundError("Bill", bill_id)
            outstanding = bill["amount_due"] - bill["amount_paid"]
            if amount > outstanding + 0.01:  # small float tolerance
                raise BusinessRuleError(
                    f"Payment of {amount:,.0f} exceeds outstanding balance of {outstanding:,.0f}",
                    rule="overpayment",
                )

        receipt_no = self.repo.next_receipt_no()

        # Get student name for ledger description
        student = self.repo._one(
            "SELECT first_name || ' ' || last_name AS name FROM students WHERE id=?",
            (student_id,),
        )
        student_name = student["name"] if student else f"Student #{student_id}"

        # Write payment — within caller's connection (must commit after)
        payment_id = self.repo.insert_payment({
            "student_id": student_id,
            "amount": amount,
            "payment_date": payment_date,
            "method": method,
            "receipt_no": receipt_no,
            "bill_id": bill_id,
            "fee_type_id": fee_type_id,
            "academic_year_id": academic_year_id,
            "reference_no": reference_no,
            "notes": notes,
            "recorded_by": actor.get("id"),
        })

        # Update bill status if applicable
        if bill and bill_id:
            new_paid = bill["amount_paid"] + amount
            outstanding_after = bill["amount_due"] - new_paid
            new_status = "paid" if outstanding_after <= 0.01 else "partial"
            self.repo.update_bill_status(bill_id, new_status, new_paid)

        # Post double-entry ledger entries
        entries = self._ledger.payment_entries(
            payment_id=payment_id,
            amount=amount,
            method=method,
            payment_date=payment_date,
            student_name=student_name,
            posted_by=actor.get("id"),
        )
        self.repo.insert_ledger_entries(entries)

        self.conn.commit()

        # Write audit
        self.audit.log(
            "fee_payments", payment_id, "INSERT", actor,
            after={"amount": amount, "method": method, "receipt_no": receipt_no, "student_id": student_id},
        )

        # Emit event (notification service picks this up if subscribed)
        event_bus.emit(Events.PAYMENT_RECORDED, {
            "payment_id":  payment_id,
            "student_id":  student_id,
            "student_name": student_name,
            "amount":      amount,
            "method":      method,
            "receipt_no":  receipt_no,
        }, actor_id=actor.get("id"))

        return {"id": payment_id, "receipt_no": receipt_no, "ok": True}

    def reverse_payment(
        self,
        payment_id: int,
        reason: str,
        actor: dict | None = None,
    ) -> dict:
        """
        Reverse a payment — posts mirror ledger entries.
        The original payment row is annotated; never deleted.
        """
        actor = actor or {}
        payment = self.repo.get_payment(payment_id)
        if not payment:
            raise NotFoundError("Payment", payment_id)

        if "[REVERSED:" in (payment.get("notes") or ""):
            raise BusinessRuleError("This payment has already been reversed", rule="double_reversal")

        # Reverse ledger entries
        entries = self._ledger.reversal_entries(
            payment_id=payment_id,
            amount=payment["amount_paid"],
            method=payment.get("payment_method", "cash"),
            reversal_date=datetime.now(timezone.utc).date().isoformat(),
            student_name=payment.get("student_name", ""),
            posted_by=actor.get("id"),
        )
        self.repo.insert_ledger_entries(entries)

        # Annotate original payment
        self.repo.mark_payment_reversed(payment_id, actor.get("id"), reason)

        # Restore bill balance if applicable
        if payment.get("bill_id"):
            bill = self.repo.get_bill(payment["bill_id"])
            if bill:
                new_paid = max(0.0, bill["amount_paid"] - payment["amount_paid"])
                new_status = "partial" if new_paid > 0 else "issued"
                self.repo.update_bill_status(payment["bill_id"], new_status, new_paid)

        self.conn.commit()

        self.audit.log(
            "fee_payments", payment_id, "REVERSE", actor,
            before={"amount_paid": payment["amount_paid"], "status": "confirmed"},
            after={"status": "reversed", "reason": reason},
        )

        event_bus.emit(Events.PAYMENT_REVERSED, {
            "payment_id": payment_id,
            "student_id": payment["student_id"],
            "amount": payment["amount_paid"],
            "reason": reason,
        }, actor_id=actor.get("id"))

        return {"ok": True, "reversed_payment_id": payment_id}

    def record_expense(
        self,
        category: str,
        description: str,
        amount: float,
        expense_date: str,
        reference: str = "",
        vendor: str = "",
        actor: dict | None = None,
    ) -> dict:
        actor = actor or {}
        if amount <= 0:
            raise ValidationError("Expense amount must be positive", field="amount")

        expense_id = self.repo.insert_expense({
            "category":     category,
            "description":  f"{vendor}: {description}" if vendor else description,
            "amount":       amount,
            "expense_date": expense_date,
            "reference":    reference,
            "recorded_by":  actor.get("id"),
        })

        # Post ledger entries for expense
        entries = self._ledger.expense_entries(
            expense_id=expense_id,
            amount=amount,
            expense_date=expense_date,
            category=category,
            description=description,
            posted_by=actor.get("id"),
        )
        self.repo.insert_ledger_entries(entries)

        self.conn.commit()

        self.audit.log(
            "expenses", expense_id, "INSERT", actor,
            after={"category": category, "amount": amount, "description": description},
        )

        event_bus.emit(Events.EXPENSE_RECORDED, {
            "expense_id":   expense_id,
            "category":     category,
            "amount":       amount,
            "expense_date": expense_date,
        }, actor_id=actor.get("id"))

        return {"id": expense_id, "ok": True}

    # ── Student bill ──────────────────────────────────────────────────────────

    def get_student_bill_summary(
        self,
        student_id: int | None = None,
        admission_no: str | None = None,
        academic_year_id: int | None = None,
    ) -> dict:
        if admission_no and not student_id:
            s = self.repo.get_student_by_admission(admission_no)
            if not s:
                raise NotFoundError("Student", admission_no)
            student_id = s["id"]
        if not student_id:
            raise ValidationError("Provide student_id or admission_no")

        bills    = self.repo.get_student_bills(student_id, academic_year_id)
        payments = self.repo.list_payments(student_id=student_id)

        # Waivers
        from database.db import fetch_all as _fa
        waivers = _fa(
            """SELECT w.*, ft.name AS fee_type_name
               FROM fee_waivers w
               LEFT JOIN student_bills sb ON sb.id = w.bill_id
               LEFT JOIN fee_structures fs ON fs.id = sb.fee_structure_id
               LEFT JOIN fee_types ft ON ft.id = fs.fee_type_id
               WHERE w.student_id=?
               ORDER BY w.created_at DESC""",
            (student_id,),
        )

        total_billed   = sum(b["amount_due"] for b in bills)
        total_discount = sum(b.get("discount_amount", 0) or 0 for b in bills)
        total_paid     = sum(p["amount_paid"] for p in payments)
        return {
            "student_id":     student_id,
            "bills":          bills,
            "payments":       payments,
            "waivers":        [dict(w) for w in waivers],
            "total_billed":   total_billed,
            "total_discount": total_discount,
            "total_paid":     total_paid,
            "balance":        total_billed - total_discount - total_paid,
        }

    # ── Ledger / financial reporting ──────────────────────────────────────────

    def get_ledger_summary(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        return self.repo.get_ledger_summary(from_date=from_date, to_date=to_date)

    def get_summary(self) -> dict:
        return self.repo.get_summary()
