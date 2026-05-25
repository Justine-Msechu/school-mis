"""
Finance router — thin HTTP controller.

All business logic lives in backend.services.finance_service.FinanceService.
This module: validates input schemas, checks permissions, calls service, returns JSON.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from backend.deps import require_auth
from backend.core.db import get_db
from backend.core.security import require_permission
from backend.core.exceptions import AppError
from backend.services.finance_service import FinanceService

router = APIRouter(tags=["finance"])
Usr = Annotated[dict, Depends(require_auth)]


def _svc(actor: dict = None) -> FinanceService:
    """Create a FinanceService with the thread-local DB connection."""
    from backend.core.db import _get_conn
    return FinanceService(_get_conn())


# ── Fee structures ─────────────────────────────────────────────────────────────

@router.get("/fee-structures")
def get_fee_structures(user: Usr, academic_year_id: int = Query(None)):
    require_permission(user, "finance.structure.view")
    svc = _svc()
    return svc.repo.list_fee_structures(academic_year_id)


@router.get("/fee-types")
def get_fee_types(user: Usr):
    svc = _svc()
    return svc.repo.list_fee_types()


class FeeTypeBody(BaseModel):
    name: str
    is_recurring: int = 1

@router.post("/fee-types")
def create_fee_type(body: FeeTypeBody, user: Usr):
    require_permission(user, "finance.structure.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO fee_types (name, is_recurring) VALUES (?,?)",
            (body.name, body.is_recurring),
        )
        conn.commit()
        return {"id": cur.lastrowid, "name": body.name}
    except Exception as e:
        raise HTTPException(400, str(e))


class FeeStructureBody(BaseModel):
    academic_year_id: int
    fee_type_id:      int
    amount:           float
    class_id:         int | None = None
    term:             int | None = None
    due_date:         str | None = None

@router.post("/fee-structures")
def create_fee_structure(body: FeeStructureBody, user: Usr):
    require_permission(user, "finance.structure.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO fee_structures (academic_year_id, class_id, fee_type_id, amount, term, due_date) VALUES (?,?,?,?,?,?)",
            (body.academic_year_id, body.class_id, body.fee_type_id, body.amount, body.term, body.due_date),
        )
        conn.commit()
        return {"id": cur.lastrowid, "ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Student bill ──────────────────────────────────────────────────────────────

@router.get("/student-bill")
def get_student_bill(
    user: Usr,
    student_id:   int = Query(None),
    admission_no: str = Query(None),
    academic_year_id: int = Query(None),
):
    require_permission(user, "finance.view")
    try:
        svc = _svc()
        return svc.get_student_bill_summary(
            student_id=student_id,
            admission_no=admission_no,
            academic_year_id=academic_year_id,
        )
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


# ── Payments ──────────────────────────────────────────────────────────────────

@router.get("/payments")
def get_payments(
    user:     Usr,
    limit:    int = Query(100),
    student_id: int = Query(None),
    academic_year_id: int = Query(None),
):
    require_permission(user, "finance.view")
    svc = _svc()
    return svc.repo.list_payments(
        student_id=student_id,
        academic_year_id=academic_year_id,
        limit=limit,
    )


class PaymentBody(BaseModel):
    student_id:      int
    amount:          float = Field(gt=0)
    payment_date:    str
    method:          str = "cash"
    bill_id:         int | None = None
    fee_type_id:     int | None = None
    academic_year_id: int | None = None
    reference_no:    str = ""
    notes:           str = ""


@router.post("/payment")
def record_payment(body: PaymentBody, user: Usr):
    require_permission(user, "finance.payment.record")
    try:
        svc = _svc()
        return svc.record_payment(
            student_id=body.student_id,
            amount=body.amount,
            method=body.method,
            payment_date=body.payment_date,
            bill_id=body.bill_id,
            fee_type_id=body.fee_type_id,
            academic_year_id=body.academic_year_id,
            reference_no=body.reference_no,
            notes=body.notes,
            actor=user,
        )
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


class ReverseBody(BaseModel):
    reason: str

@router.post("/payment/{payment_id}/reverse")
def reverse_payment(payment_id: int, body: ReverseBody, user: Usr):
    require_permission(user, "finance.payment.void")
    try:
        svc = _svc()
        return svc.reverse_payment(payment_id, body.reason, actor=user)
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.get("/expense-categories")
def list_expense_categories(user: Usr):
    from backend.core.db import _get_conn
    rows = _get_conn().execute(
        "SELECT * FROM expense_categories WHERE is_active=1 ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/expenses")
def get_expenses(user: Usr, limit: int = Query(100)):
    require_permission(user, "accounting.view")
    svc = _svc()
    return svc.repo.list_expenses(limit)


class ExpenseBody(BaseModel):
    category:    str
    description: str
    amount:      float = Field(gt=0)
    expense_date: str
    reference:   str = ""
    vendor:      str = ""


@router.post("/expense")
def record_expense(body: ExpenseBody, user: Usr):
    require_permission(user, "accounting.expense.record")
    try:
        svc = _svc()
        return svc.record_expense(
            category=body.category,
            description=body.description,
            amount=body.amount,
            expense_date=body.expense_date,
            reference=body.reference,
            vendor=body.vendor,
            actor=user,
        )
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


# ── Ledger / financial reports ────────────────────────────────────────────────

@router.get("/ledger")
def get_ledger_summary(
    user:      Usr,
    from_date: str = Query(None),
    to_date:   str = Query(None),
):
    require_permission(user, "finance.report")
    svc = _svc()
    return svc.get_ledger_summary(from_date=from_date, to_date=to_date)


@router.get("/ledger/entries")
def get_ledger_entries(
    user:           Usr,
    reference_type: str = Query(None),
    reference_id:   int = Query(None),
    limit:          int = Query(200),
):
    require_permission(user, "finance.report")
    svc = _svc()
    return svc.repo.get_ledger_entries(reference_type, reference_id, limit)


@router.get("/summary")
def get_summary(user: Usr):
    require_permission(user, "finance.view")
    svc = _svc()
    base = svc.get_summary()
    recent = svc.repo.list_payments(limit=10)
    return {**base, "recent_payments": recent}
