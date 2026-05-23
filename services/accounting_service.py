"""
services/accounting_service.py — Accounting domain business logic.
"""

from __future__ import annotations
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, db_write


class AccountingService(BaseService):

    def record_expense(
        self,
        category: str,
        description: str,
        amount: float,
        expense_date: str,
        receipt_ref: str = "",
    ) -> int:
        """
        Record a school expense.

        Flow:
          1. RBAC check
          2. Policy: amount > 0, category required
          3. Write to expenses table + audit
        """
        self._require_permission("accounting.expense.record")

        self._enforce(
            "accounting.expense.record",
            subject={},
            data={"category": category, "amount": amount, "description": description},
        )

        if not description.strip():
            raise ServiceError("Description is required.")

        expense_id = db_write(
            """INSERT INTO expenses
               (category, description, amount, expense_date, receipt_ref, recorded_by)
               VALUES (?,?,?,?,?,?)""",
            (category, description.strip(), amount, expense_date,
             receipt_ref.strip(), self._session.user_id),
            action="expense_recorded", table="expenses",
            detail=f"{category} TZS {amount:,.0f} — {description.strip()[:60]}",
            user_id=self._session.user_id,
            after_state={
                "category": category, "amount": amount,
                "description": description.strip(), "date": expense_date,
            },
        )
        return expense_id

    def get_summary(self, period: str = "month") -> dict:
        """Return income/expense/surplus/waiver totals for a period."""
        self._require_permission("accounting.view")

        if period == "month":
            df  = "AND strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')"
            ef  = "AND strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')"
            wf  = "AND strftime('%Y-%m',fw.created_at)=strftime('%Y-%m','now')"
        elif period == "year":
            df  = "AND strftime('%Y',payment_date)=strftime('%Y','now')"
            ef  = "AND strftime('%Y',expense_date)=strftime('%Y','now')"
            wf  = "AND strftime('%Y',fw.created_at)=strftime('%Y','now')"
        else:
            df = ef = wf = ""

        income  = fetch_one(f"SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments WHERE 1=1 {df}")
        expense = fetch_one(f"SELECT COALESCE(SUM(amount),0) AS t FROM expenses WHERE 1=1 {ef}")
        waivers = fetch_one(
            f"""SELECT COALESCE(SUM(sb.amount_due * fw.discount_percent/100),0) AS t
                FROM fee_waivers fw JOIN student_bills sb ON sb.id=fw.bill_id
                WHERE 1=1 {wf}"""
        )
        inc  = income["t"]  if income  else 0
        exp  = expense["t"] if expense else 0
        waiv = waivers["t"] if waivers else 0
        return {"income": inc, "expense": exp, "surplus": inc - exp, "waivers": waiv}


# Singleton
accounting_service = AccountingService()
