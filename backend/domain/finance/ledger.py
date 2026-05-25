"""
Double-entry ledger engine — pure domain logic, no DB access.

Every financial event MUST produce balanced ledger entries (debits = credits).
The LedgerEngine builds entry pairs; the repository persists them atomically.

Account codes:
    CASH          — Cash in Hand
    MPESA         — M-Pesa Receipts
    BANK          — Bank Deposits
    CHEQUE        — Cheque Receipts
    FEE_INCOME    — School Fee Revenue
    TRANSPORT_INC — Transport Fee Revenue
    WAIVER_EXP    — Waiver/Discount Expense
    EXPENSE       — General Expenses
    RECEIVABLE    — Student Fee Receivables (outstanding balance)
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date


PAYMENT_METHOD_ACCOUNT = {
    "cash":   "CASH",
    "mpesa":  "MPESA",
    "bank":   "BANK",
    "cheque": "CHEQUE",
    "waiver": "WAIVER_EXP",
}

ACCOUNT_NAMES = {
    "CASH":          "Cash in Hand",
    "MPESA":         "M-Pesa Receipts",
    "BANK":          "Bank Deposits",
    "CHEQUE":        "Cheque Receipts",
    "FEE_INCOME":    "School Fee Income",
    "TRANSPORT_INC": "Transport Fee Income",
    "WAIVER_EXP":    "Fee Waivers / Discounts",
    "EXPENSE":       "General Expenses",
    "RECEIVABLE":    "Student Fee Receivables",
}


@dataclass
class LedgerEntry:
    entry_date: str          # ISO date string
    account_code: str
    account_name: str
    debit_amount: float
    credit_amount: float
    reference_type: str      # 'payment', 'reversal', 'waiver', 'expense'
    reference_id: int
    description: str
    posted_by: int | None    # user_id


def _entry(
    date_str: str,
    account_code: str,
    debit: float = 0.0,
    credit: float = 0.0,
    ref_type: str = "",
    ref_id: int = 0,
    description: str = "",
    posted_by: int | None = None,
) -> LedgerEntry:
    return LedgerEntry(
        entry_date=date_str,
        account_code=account_code,
        account_name=ACCOUNT_NAMES.get(account_code, account_code),
        debit_amount=debit,
        credit_amount=credit,
        reference_type=ref_type,
        reference_id=ref_id,
        description=description,
        posted_by=posted_by,
    )


class LedgerEngine:
    """
    Produces pairs of ledger entries for each financial event.
    The caller is responsible for persisting them atomically.
    """

    @staticmethod
    def payment_entries(
        payment_id: int,
        amount: float,
        method: str,
        payment_date: str,
        student_name: str,
        posted_by: int | None = None,
    ) -> list[LedgerEntry]:
        """
        Payment received:
            Debit  Cash/Mpesa/Bank  (asset increases)
            Credit FEE_INCOME       (revenue increases)
        """
        acct = PAYMENT_METHOD_ACCOUNT.get(method.lower(), "CASH")
        desc = f"Fee payment — {student_name}"
        return [
            _entry(payment_date, acct,       debit=amount, ref_type="payment", ref_id=payment_id, description=desc, posted_by=posted_by),
            _entry(payment_date, "FEE_INCOME", credit=amount, ref_type="payment", ref_id=payment_id, description=desc, posted_by=posted_by),
        ]

    @staticmethod
    def reversal_entries(
        payment_id: int,
        amount: float,
        method: str,
        reversal_date: str,
        student_name: str,
        posted_by: int | None = None,
    ) -> list[LedgerEntry]:
        """
        Payment reversal — exact mirror of payment entries:
            Debit  FEE_INCOME       (revenue decreases)
            Credit Cash/Mpesa/Bank  (asset decreases)
        """
        acct = PAYMENT_METHOD_ACCOUNT.get(method.lower(), "CASH")
        desc = f"Payment reversal — {student_name}"
        return [
            _entry(reversal_date, "FEE_INCOME", debit=amount, ref_type="reversal", ref_id=payment_id, description=desc, posted_by=posted_by),
            _entry(reversal_date, acct, credit=amount, ref_type="reversal", ref_id=payment_id, description=desc, posted_by=posted_by),
        ]

    @staticmethod
    def waiver_entries(
        waiver_id: int,
        amount: float,
        waiver_date: str,
        student_name: str,
        posted_by: int | None = None,
    ) -> list[LedgerEntry]:
        """
        Fee waiver granted:
            Debit  WAIVER_EXP   (expense increases)
            Credit RECEIVABLE   (reduce what student owes)
        """
        desc = f"Fee waiver — {student_name}"
        return [
            _entry(waiver_date, "WAIVER_EXP",  debit=amount, ref_type="waiver", ref_id=waiver_id, description=desc, posted_by=posted_by),
            _entry(waiver_date, "RECEIVABLE",  credit=amount, ref_type="waiver", ref_id=waiver_id, description=desc, posted_by=posted_by),
        ]

    @staticmethod
    def expense_entries(
        expense_id: int,
        amount: float,
        expense_date: str,
        category: str,
        description: str,
        posted_by: int | None = None,
    ) -> list[LedgerEntry]:
        """
        Expense paid:
            Debit  EXPENSE  (expense increases)
            Credit CASH     (asset decreases)
        """
        desc = f"Expense: {category} — {description[:60]}"
        return [
            _entry(expense_date, "EXPENSE", debit=amount, ref_type="expense", ref_id=expense_id, description=desc, posted_by=posted_by),
            _entry(expense_date, "CASH",   credit=amount, ref_type="expense", ref_id=expense_id, description=desc, posted_by=posted_by),
        ]

    @staticmethod
    def verify_balanced(entries: list[LedgerEntry]) -> bool:
        """Assert that debits == credits (double-entry invariant)."""
        total_debit  = sum(e.debit_amount  for e in entries)
        total_credit = sum(e.credit_amount for e in entries)
        return abs(total_debit - total_credit) < 0.001
