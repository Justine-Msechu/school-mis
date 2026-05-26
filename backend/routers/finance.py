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
    name:        str
    amount:      float = 0
    term:        int | None = None
    description: str | None = None

@router.post("/fee-types")
def create_fee_type(body: FeeTypeBody, user: Usr):
    require_permission(user, "finance.structure.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO fee_types (name, amount, term, description) VALUES (?,?,?,?)",
            (body.name, body.amount, body.term, body.description),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM fee_types WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)
    except Exception as e:
        raise HTTPException(400, str(e))


class FeeStructureBody(BaseModel):
    academic_year_id: int
    fee_type_id:      int
    amount:           float
    class_id:         int | None = None
    student_id:       int | None = None
    term:             int | None = None
    due_date:         str | None = None

@router.post("/fee-structures")
def create_fee_structure(body: FeeStructureBody, user: Usr):
    require_permission(user, "finance.structure.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO fee_structures
               (academic_year_id, class_id, student_id, fee_type_id, amount, term, due_date)
               VALUES (?,?,?,?,?,?,?)""",
            (body.academic_year_id, body.class_id, body.student_id,
             body.fee_type_id, body.amount, body.term, body.due_date),
        )
        conn.commit()
        return {"id": cur.lastrowid, "ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Billing engine ────────────────────────────────────────────────────────────

class BillingGenerateBody(BaseModel):
    academic_year_id: int
    class_id:         int | None = None
    term:             int | None = None   # 1/2/3 — filters fee structures by term

@router.post("/billing/generate")
def generate_bills(body: BillingGenerateBody, user: Usr):
    require_permission(user, "finance.billing.generate")
    import uuid
    from backend.core.db import _get_conn
    conn = _get_conn()

    # Fetch fee structures for this year
    fs_where = ["fs.academic_year_id = ?"]
    fs_params: list = [body.academic_year_id]
    if body.class_id:
        fs_where.append("(fs.class_id = ? OR fs.class_id IS NULL)")
        fs_params.append(body.class_id)
    if body.term:
        fs_where.append("(fs.term = ? OR fs.term IS NULL)")
        fs_params.append(body.term)

    structures = conn.execute(
        f"""SELECT fs.* FROM fee_structures fs
            WHERE {' AND '.join(fs_where)}""",
        fs_params,
    ).fetchall()

    if not structures:
        raise HTTPException(400, "No fee structures found for the selected year/class combination.")

    created = 0
    skipped = 0

    for fs in structures:
        # Determine which students get this bill
        if fs["student_id"]:
            students = conn.execute(
                "SELECT id FROM students WHERE id=? AND is_active=1 AND deleted_at IS NULL",
                (fs["student_id"],),
            ).fetchall()
        else:
            st_where = ["is_active=1", "deleted_at IS NULL"]
            st_params: list = []
            target_class = fs["class_id"] or body.class_id
            if target_class:
                st_where.append("class_id=?")
                st_params.append(target_class)
            if fs["student_type"]:
                st_where.append("student_type=?")
                st_params.append(fs["student_type"])
            students = conn.execute(
                f"SELECT id FROM students WHERE {' AND '.join(st_where)}",
                st_params,
            ).fetchall()

        for s in students:
            existing = conn.execute(
                "SELECT id FROM student_bills WHERE student_id=? AND fee_structure_id=?",
                (s["id"], fs["id"]),
            ).fetchone()
            if existing:
                skipped += 1
                continue
            control_no = f"BILL/{body.academic_year_id}/{uuid.uuid4().hex[:8].upper()}"
            conn.execute(
                """INSERT INTO student_bills
                   (student_id, fee_structure_id, academic_year_id, control_number, amount_due, due_date)
                   VALUES (?,?,?,?,?,?)""",
                (s["id"], fs["id"], body.academic_year_id, control_no, fs["amount"], fs["due_date"]),
            )
            created += 1

    conn.commit()
    return {"created": created, "skipped": skipped}


# ── Outstanding debtors ───────────────────────────────────────────────────────

@router.get("/outstanding")
def get_outstanding(
    user: Usr,
    academic_year_id: int = Query(None),
    class_id:         int = Query(None),
):
    require_permission(user, "finance.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    where = ["(sb.amount_due - sb.amount_paid) > 0.01", "s.is_active = 1"]
    params: list = []
    if academic_year_id:
        where.append("sb.academic_year_id = ?")
        params.append(academic_year_id)
    if class_id:
        where.append("s.class_id = ?")
        params.append(class_id)
    rows = conn.execute(
        f"""SELECT
                s.id            AS student_id,
                s.first_name || ' ' || s.last_name AS student_name,
                s.admission_no,
                c.name          AS class_name,
                SUM(sb.amount_due)                                                    AS total_billed,
                COALESCE(SUM(sb.discount_amount), 0)                                  AS total_discount,
                COALESCE(SUM(sb.amount_paid), 0)                                      AS total_paid,
                SUM(sb.amount_due - COALESCE(sb.discount_amount,0) - sb.amount_paid)  AS balance
            FROM student_bills sb
            JOIN students s  ON s.id  = sb.student_id
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE {' AND '.join(where)}
            GROUP BY s.id
            HAVING balance > 0.01
            ORDER BY balance DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


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


# ── Waivers ───────────────────────────────────────────────────────────────────

class WaiverBody(BaseModel):
    student_id:       int
    bill_id:          int | None = None
    academic_year_id: int | None = None
    waiver_type:      str = "other"   # orphan_exemption|scholarship|partial_discount|staff_child|other
    discount_percent: float = 100
    reason:           str | None = None


@router.get("/waivers")
def list_waivers(user: Usr, student_id: int = Query(None)):
    require_permission(user, "finance.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    where = "1=1"
    params: list = []
    if student_id:
        where = "w.student_id = ?"
        params.append(student_id)
    rows = conn.execute(
        f"""SELECT w.*,
                   s.first_name || ' ' || s.last_name AS student_name,
                   s.admission_no,
                   u.username AS approved_by_name,
                   ft.name AS fee_type_name
            FROM fee_waivers w
            JOIN students s ON s.id = w.student_id
            LEFT JOIN users u ON u.id = w.approved_by
            LEFT JOIN student_bills sb ON sb.id = w.bill_id
            LEFT JOIN fee_structures fs ON fs.id = sb.fee_structure_id
            LEFT JOIN fee_types ft ON ft.id = fs.fee_type_id
            WHERE {where}
            ORDER BY w.created_at DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/waivers")
def create_waiver(body: WaiverBody, user: Usr):
    require_permission(user, "finance.waiver.create")
    from backend.core.db import _get_conn
    conn = _get_conn()

    # Insert waiver record
    cur = conn.execute(
        """INSERT INTO fee_waivers
           (student_id, bill_id, academic_year_id, waiver_type, discount_percent, approved_by, reason)
           VALUES (?,?,?,?,?,?,?)""",
        (body.student_id, body.bill_id, body.academic_year_id,
         body.waiver_type, body.discount_percent, user["id"], body.reason),
    )
    waiver_id = cur.lastrowid

    # Apply discount to the specific bill if bill_id given
    if body.bill_id:
        bill = conn.execute("SELECT * FROM student_bills WHERE id=?", (body.bill_id,)).fetchone()
        if bill:
            discount = round(bill["amount_due"] * (body.discount_percent / 100), 2)
            new_discount = min(bill["amount_due"], bill["discount_amount"] + discount)
            effective_outstanding = bill["amount_due"] - new_discount - bill["amount_paid"]
            new_status = "waived" if effective_outstanding <= 0.01 else ("partial" if bill["amount_paid"] > 0 else "unpaid")
            conn.execute(
                "UPDATE student_bills SET discount_amount=?, status=? WHERE id=?",
                (new_discount, new_status, body.bill_id),
            )

    conn.commit()
    return {"id": waiver_id, "ok": True}


@router.delete("/waivers/{waiver_id}")
def delete_waiver(waiver_id: int, user: Usr):
    require_permission(user, "finance.waiver.create")
    from backend.core.db import _get_conn
    conn = _get_conn()
    waiver = conn.execute("SELECT * FROM fee_waivers WHERE id=?", (waiver_id,)).fetchone()
    if not waiver:
        raise HTTPException(404, "Waiver not found")
    # Reverse discount on bill if linked
    if waiver["bill_id"]:
        bill = conn.execute("SELECT * FROM student_bills WHERE id=?", (waiver["bill_id"],)).fetchone()
        if bill:
            discount = round(bill["amount_due"] * (waiver["discount_percent"] / 100), 2)
            new_discount = max(0.0, bill["discount_amount"] - discount)
            effective_outstanding = bill["amount_due"] - new_discount - bill["amount_paid"]
            new_status = "paid" if effective_outstanding <= 0.01 and bill["amount_paid"] > 0 else ("partial" if bill["amount_paid"] > 0 else "unpaid")
            conn.execute(
                "UPDATE student_bills SET discount_amount=?, status=? WHERE id=?",
                (new_discount, new_status, waiver["bill_id"]),
            )
    conn.execute("DELETE FROM fee_waivers WHERE id=?", (waiver_id,))
    conn.commit()
    return {"ok": True}
