from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["finance"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/fee-structures")
def get_fee_structures(user: Usr):
    rows = fetch_all(
        """SELECT fs.*, ft.name as fee_type_name, ay.label as year_label
           FROM fee_structures fs
           JOIN fee_types ft ON ft.id = fs.fee_type_id
           LEFT JOIN academic_years ay ON ay.id = fs.academic_year_id
           ORDER BY ay.label DESC, ft.name""",
    )
    return [dict(r) for r in rows]


@router.get("/student-bill")
def get_student_bill(user: Usr, student_id: int = Query(None), admission_no: str = Query(None)):
    if student_id:
        student = fetch_one("SELECT id, admission_no FROM students WHERE id=?", (student_id,))
    elif admission_no:
        student = fetch_one("SELECT id, admission_no FROM students WHERE admission_no=?", (admission_no,))
    else:
        raise HTTPException(400, "Provide student_id or admission_no")
    if not student:
        raise HTTPException(404, "Student not found")

    bills = fetch_all(
        """SELECT sb.*, ft.name as fee_type_name
           FROM student_bills sb
           JOIN fee_structures fs ON fs.id = sb.fee_structure_id
           JOIN fee_types ft ON ft.id = fs.fee_type_id
           WHERE sb.student_id=?
           ORDER BY sb.due_date DESC""",
        (student["id"],),
    )
    payments = fetch_all(
        "SELECT * FROM fee_payments WHERE student_id=? ORDER BY payment_date DESC",
        (student["id"],),
    )
    total_billed = sum(b["amount"] for b in bills)
    total_paid   = sum(p["amount"] for p in payments)
    return {
        "student_id":   student["id"],
        "bills":        [dict(b) for b in bills],
        "payments":     [dict(p) for p in payments],
        "total_billed": total_billed,
        "total_paid":   total_paid,
        "balance":      total_billed - total_paid,
    }


@router.get("/payments")
def get_payments(user: Usr, limit: int = Query(50)):
    rows = fetch_all(
        """SELECT fp.*, s.first_name || ' ' || s.last_name as student_name, s.admission_no
           FROM fee_payments fp
           JOIN students s ON s.id = fp.student_id
           ORDER BY fp.payment_date DESC LIMIT ?""",
        (limit,),
    )
    return [dict(r) for r in rows]


class PaymentBody(BaseModel):
    student_id:   int
    amount:       float
    payment_date: str
    method:       str = "cash"
    reference:    str = ""
    notes:        str = ""


@router.post("/payment")
def record_payment(body: PaymentBody, user: Usr):
    row_id = execute(
        """INSERT INTO fee_payments (student_id, amount, payment_date, method, reference, notes, recorded_by)
           VALUES (?,?,?,?,?,?,?)""",
        (body.student_id, body.amount, body.payment_date, body.method,
         body.reference, body.notes, user.get("id")),
    )
    return {"id": row_id, "ok": True}


@router.get("/summary")
def get_summary(user: Usr):
    total_billed = dict(fetch_one("SELECT COALESCE(SUM(amount),0) as n FROM student_bills") or {}).get("n", 0)
    total_paid   = dict(fetch_one("SELECT COALESCE(SUM(amount),0) as n FROM fee_payments") or {}).get("n", 0)
    recent_payments = fetch_all(
        """SELECT fp.*, s.first_name || ' ' || s.last_name as student_name
           FROM fee_payments fp JOIN students s ON s.id=fp.student_id
           ORDER BY fp.payment_date DESC LIMIT 10"""
    )
    return {
        "total_billed":    total_billed,
        "total_collected": total_paid,
        "balance":         total_billed - total_paid,
        "recent_payments": [dict(r) for r in recent_payments],
    }
