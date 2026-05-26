"""
Finance router — thin HTTP controller.

All business logic lives in backend.services.finance_service.FinanceService.
This module: validates input schemas, checks permissions, calls service, returns JSON.
"""

import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from backend.deps import require_auth, rate_limit
from backend.core.db import get_db
from backend.core.security import require_permission
from backend.core.exceptions import AppError
from backend.services.finance_service import FinanceService

from fastapi import Depends
router = APIRouter(tags=["finance"], dependencies=[Depends(rate_limit(max_calls=120, window_secs=60, scope="finance"))])
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
    from backend.core.db import _get_conn
    from backend.core.control_number import generate_control_number
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
            st_where = ["s.is_active=1", "s.deleted_at IS NULL"]
            st_params: list = []
            if fs["grade_level"]:
                # All students whose class shares this grade level (covers all sections)
                st_where.append(
                    "s.class_id IN (SELECT id FROM classes WHERE grade_level=?)"
                )
                st_params.append(fs["grade_level"])
            else:
                target_class = fs["class_id"] or body.class_id
                if target_class:
                    st_where.append("s.class_id=?")
                    st_params.append(target_class)
            if fs["student_type"]:
                st_where.append("s.student_type=?")
                st_params.append(fs["student_type"])
            students = conn.execute(
                f"SELECT s.id FROM students s WHERE {' AND '.join(st_where)}",
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
            import secrets as _sec
            # Unique temp value avoids UNIQUE constraint collision while we get the rowid
            temp_ctrl = f"TMP-{_sec.token_hex(12)}"
            cur2 = conn.execute(
                """INSERT INTO student_bills
                   (student_id, fee_structure_id, academic_year_id, control_number, amount_due, due_date)
                   VALUES (?,?,?,?,?,?)""",
                (s["id"], fs["id"], body.academic_year_id, temp_ctrl, fs["amount"], fs["due_date"]),
            )
            bill_id = cur2.lastrowid
            control_no = generate_control_number(bill_id, datetime.date.today().year)
            conn.execute("UPDATE student_bills SET control_number=? WHERE id=?", (control_no, bill_id))
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


# ── Carry-forward balances ─────────────────────────────────────────────────────

class CarryForwardBody(BaseModel):
    from_year_id: int
    to_year_id:   int
    term:         int | None = None   # carry only specific term; None = all

@router.post("/carry-forward")
def carry_forward(body: CarryForwardBody, user: Usr):
    require_permission(user, "finance.billing.generate")
    from backend.core.db import _get_conn
    from backend.core.control_number import generate_control_number
    conn = _get_conn()

    # Ensure "Balance B/F" fee type exists
    bf = conn.execute("SELECT id FROM fee_types WHERE name='Balance B/F'").fetchone()
    if not bf:
        conn.execute("INSERT INTO fee_types (name, amount, description) VALUES ('Balance B/F', 0, 'Carried-forward balance from previous period')")
        conn.commit()
        bf = conn.execute("SELECT id FROM fee_types WHERE name='Balance B/F'").fetchone()
    bf_fee_type_id = bf["id"]

    # Ensure a B/F fee structure exists for the target year
    fs = conn.execute(
        "SELECT id FROM fee_structures WHERE fee_type_id=? AND academic_year_id=? AND class_id IS NULL AND student_id IS NULL",
        (bf_fee_type_id, body.to_year_id),
    ).fetchone()
    if not fs:
        conn.execute(
            "INSERT INTO fee_structures (fee_type_id, academic_year_id, amount, due_date) VALUES (?,?,0,NULL)",
            (bf_fee_type_id, body.to_year_id),
        )
        conn.commit()
        fs = conn.execute(
            "SELECT id FROM fee_structures WHERE fee_type_id=? AND academic_year_id=?",
            (bf_fee_type_id, body.to_year_id),
        ).fetchone()
    bf_fs_id = fs["id"]

    # Find outstanding bills in the source year
    where = ["sb.academic_year_id = ?", "(sb.amount_due - COALESCE(sb.discount_amount,0) - sb.amount_paid) > 0.01"]
    params: list = [body.from_year_id]
    if body.term:
        where.append("fs.term = ?")
        params.append(body.term)

    rows = conn.execute(
        f"""SELECT sb.student_id,
                   SUM(sb.amount_due - COALESCE(sb.discount_amount,0) - sb.amount_paid) AS balance
            FROM student_bills sb
            LEFT JOIN fee_structures fs ON fs.id = sb.fee_structure_id
            WHERE {' AND '.join(where)}
            GROUP BY sb.student_id
            HAVING balance > 0.01""",
        params,
    ).fetchall()

    created = 0
    skipped = 0
    for r in rows:
        existing = conn.execute(
            "SELECT id FROM student_bills WHERE student_id=? AND fee_structure_id=?",
            (r["student_id"], bf_fs_id),
        ).fetchone()
        if existing:
            skipped += 1
            continue
        import secrets as _sec2
        temp_ctrl = f"TMP-{_sec2.token_hex(12)}"
        cur2 = conn.execute(
            "INSERT INTO student_bills (student_id, fee_structure_id, academic_year_id, control_number, amount_due) VALUES (?,?,?,?,?)",
            (r["student_id"], bf_fs_id, body.to_year_id, temp_ctrl, round(r["balance"], 2)),
        )
        ctrl = generate_control_number(cur2.lastrowid, body.to_year_id)
        conn.execute("UPDATE student_bills SET control_number=? WHERE id=?", (ctrl, cur2.lastrowid))
        created += 1

    conn.commit()
    return {"created": created, "skipped": skipped}


# ── Locked periods ─────────────────────────────────────────────────────────────

@router.get("/locked-periods")
def list_locked_periods(user: Usr):
    require_permission(user, "finance.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    rows = conn.execute(
        """SELECT lp.*, ay.label AS year_label, u.username AS locked_by_name
           FROM locked_periods lp
           JOIN academic_years ay ON ay.id = lp.academic_year_id
           LEFT JOIN users u ON u.id = lp.locked_by
           ORDER BY lp.locked_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


class LockPeriodBody(BaseModel):
    academic_year_id: int
    term:             int | None = None
    note:             str | None = None

@router.post("/lock-period")
def lock_period(body: LockPeriodBody, user: Usr):
    require_permission(user, "finance.structure.manage")
    from backend.core.db import _get_conn
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO locked_periods (academic_year_id, term, locked_by, note) VALUES (?,?,?,?)",
            (body.academic_year_id, body.term, user["id"], body.note),
        )
        conn.commit()
        return {"id": cur.lastrowid, "ok": True}
    except Exception:
        raise HTTPException(400, "This period is already locked.")

@router.delete("/locked-periods/{period_id}")
def unlock_period(period_id: int, user: Usr):
    require_permission(user, "finance.structure.manage")
    from backend.core.db import _get_conn
    conn = _get_conn()
    conn.execute("DELETE FROM locked_periods WHERE id=?", (period_id,))
    conn.commit()
    return {"ok": True}


def _check_period_locked(conn, academic_year_id: int, term: int | None):
    row = conn.execute(
        "SELECT id FROM locked_periods WHERE academic_year_id=? AND (term=? OR term IS NULL)",
        (academic_year_id, term),
    ).fetchone()
    if row:
        label = f"Term {term}" if term else "this year"
        raise HTTPException(423, f"Accounting period for {label} is locked. Unlock it before making changes.")


# ── Late fee rules ─────────────────────────────────────────────────────────────

@router.get("/late-fee-rules")
def list_late_fee_rules(user: Usr):
    require_permission(user, "finance.structure.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    rows = conn.execute(
        """SELECT r.*, ft.name AS fee_type_name
           FROM late_fee_rules r
           LEFT JOIN fee_types ft ON ft.id = r.fee_type_id
           ORDER BY r.days_after_due"""
    ).fetchall()
    return [dict(r) for r in rows]


class LateFeeRuleBody(BaseModel):
    fee_type_id:    int | None = None
    days_after_due: int = 7
    charge_type:    str = "percent"
    charge_amount:  float
    max_charge:     float | None = None

@router.post("/late-fee-rules")
def create_late_fee_rule(body: LateFeeRuleBody, user: Usr):
    require_permission(user, "finance.structure.manage")
    from backend.core.db import _get_conn
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO late_fee_rules (fee_type_id, days_after_due, charge_type, charge_amount, max_charge) VALUES (?,?,?,?,?)",
        (body.fee_type_id, body.days_after_due, body.charge_type, body.charge_amount, body.max_charge),
    )
    conn.commit()
    return {"id": cur.lastrowid, "ok": True}

@router.delete("/late-fee-rules/{rule_id}")
def delete_late_fee_rule(rule_id: int, user: Usr):
    require_permission(user, "finance.structure.manage")
    from backend.core.db import _get_conn
    conn = _get_conn()
    conn.execute("DELETE FROM late_fee_rules WHERE id=?", (rule_id,))
    conn.commit()
    return {"ok": True}

@router.post("/apply-late-fees")
def apply_late_fees(user: Usr, academic_year_id: int = Query(None), dry_run: bool = Query(False)):
    require_permission(user, "finance.billing.generate")
    import uuid, datetime
    from backend.core.db import _get_conn
    conn = _get_conn()
    today = datetime.date.today().isoformat()

    rules = conn.execute("SELECT * FROM late_fee_rules WHERE is_active=1").fetchall()
    if not rules:
        return {"applied": 0, "message": "No active late fee rules found."}

    where = ["sb.status NOT IN ('paid','waived')", "sb.due_date IS NOT NULL", "sb.due_date < ?"]
    params: list = [today]
    if academic_year_id:
        where.append("sb.academic_year_id = ?")
        params.append(academic_year_id)

    overdue_bills = conn.execute(
        f"""SELECT sb.*, fs.fee_type_id, fs.term
            FROM student_bills sb
            JOIN fee_structures fs ON fs.id = sb.fee_structure_id
            WHERE {' AND '.join(where)}""",
        params,
    ).fetchall()

    applied = 0
    for bill in overdue_bills:
        for rule in rules:
            if rule["fee_type_id"] and rule["fee_type_id"] != bill["fee_type_id"]:
                continue
            import datetime as dt
            due = dt.date.fromisoformat(bill["due_date"])
            days_late = (dt.date.today() - due).days
            if days_late < rule["days_after_due"]:
                continue
            outstanding = bill["amount_due"] - (bill["discount_amount"] or 0) - bill["amount_paid"]
            if outstanding <= 0:
                continue
            if rule["charge_type"] == "percent":
                late_amt = round(outstanding * (rule["charge_amount"] / 100), 2)
                if rule["max_charge"]:
                    late_amt = min(late_amt, rule["max_charge"])
            else:
                late_amt = rule["charge_amount"]

            # Check if late fee already applied for this bill+rule combo using a
            # stable idempotency key stored in notes (not in control_number)
            idempotency_key = f"LATE:{bill['id']}:{rule['id']}"
            existing = conn.execute(
                "SELECT id FROM student_bills WHERE notes=? AND student_id=?",
                (idempotency_key, bill["student_id"]),
            ).fetchone()
            if existing:
                continue

            # Ensure "Late Fee" fee type / structure exists
            lf_ft = conn.execute("SELECT id FROM fee_types WHERE name='Late Fee'").fetchone()
            if not lf_ft:
                conn.execute("INSERT INTO fee_types (name, amount) VALUES ('Late Fee', 0)")
                conn.commit()
                lf_ft = conn.execute("SELECT id FROM fee_types WHERE name='Late Fee'").fetchone()
            lf_fs = conn.execute(
                "SELECT id FROM fee_structures WHERE fee_type_id=? AND academic_year_id=?",
                (lf_ft["id"], bill["academic_year_id"]),
            ).fetchone()
            if not lf_fs:
                conn.execute(
                    "INSERT INTO fee_structures (fee_type_id, academic_year_id, amount) VALUES (?,?,0)",
                    (lf_ft["id"], bill["academic_year_id"]),
                )
                conn.commit()
                lf_fs = conn.execute(
                    "SELECT id FROM fee_structures WHERE fee_type_id=? AND academic_year_id=?",
                    (lf_ft["id"], bill["academic_year_id"]),
                ).fetchone()

            if not dry_run:
                from backend.core.control_number import generate_control_number as _gcn
                cur_lf = conn.execute(
                    "INSERT INTO student_bills (student_id, fee_structure_id, academic_year_id, control_number, amount_due, notes) VALUES (?,?,?,?,?,?)",
                    (bill["student_id"], lf_fs["id"], bill["academic_year_id"], "PENDING", late_amt, idempotency_key),
                )
                ctrl_lf = _gcn(cur_lf.lastrowid)
                conn.execute("UPDATE student_bills SET control_number=? WHERE id=?", (ctrl_lf, cur_lf.lastrowid))
            applied += 1

    if not dry_run:
        conn.commit()
    return {"applied": applied, "dry_run": dry_run}


# ── Installment schedules ──────────────────────────────────────────────────────

@router.get("/installments")
def list_installments(user: Usr, student_id: int = Query(None), bill_id: int = Query(None)):
    require_permission(user, "finance.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("ps.student_id=?")
        params.append(student_id)
    if bill_id:
        where.append("ps.bill_id=?")
        params.append(bill_id)
    rows = conn.execute(
        f"""SELECT ps.*, ft.name AS fee_type_name
            FROM payment_schedules ps
            JOIN student_bills sb ON sb.id = ps.bill_id
            JOIN fee_structures fs ON fs.id = sb.fee_structure_id
            JOIN fee_types ft ON ft.id = fs.fee_type_id
            WHERE {' AND '.join(where)}
            ORDER BY ps.bill_id, ps.installment_no""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


class InstallmentPlanBody(BaseModel):
    bill_id:     int
    installments: list[dict]  # [{due_date, amount}]

@router.post("/installments")
def create_installment_plan(body: InstallmentPlanBody, user: Usr):
    require_permission(user, "finance.billing.generate")
    from backend.core.db import _get_conn
    conn = _get_conn()
    bill = conn.execute("SELECT * FROM student_bills WHERE id=?", (body.bill_id,)).fetchone()
    if not bill:
        raise HTTPException(404, "Bill not found")
    total = sum(i.get("amount", 0) for i in body.installments)
    net = bill["amount_due"] - (bill["discount_amount"] or 0)
    if abs(total - net) > 0.5:
        raise HTTPException(400, f"Installment amounts ({total:,.0f}) must equal net bill amount ({net:,.0f})")
    # Delete existing schedule for this bill
    conn.execute("DELETE FROM payment_schedules WHERE bill_id=?", (body.bill_id,))
    for i, inst in enumerate(body.installments, 1):
        conn.execute(
            "INSERT INTO payment_schedules (student_id, bill_id, installment_no, due_date, amount_due) VALUES (?,?,?,?,?)",
            (bill["student_id"], body.bill_id, i, inst["due_date"], inst["amount"]),
        )
    conn.commit()
    return {"ok": True, "installments": len(body.installments)}


# ── Pending approvals (maker/checker) ─────────────────────────────────────────

@router.get("/pending-approvals")
def list_pending_approvals(user: Usr):
    require_permission(user, "finance.view")
    from backend.core.db import _get_conn
    conn = _get_conn()
    rows = conn.execute(
        """SELECT pa.*, u.username AS requester_name
           FROM pending_approvals pa
           LEFT JOIN users u ON u.id = pa.requested_by
           WHERE pa.status = 'pending'
           ORDER BY pa.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


class ApprovalActionBody(BaseModel):
    note: str | None = None

@router.post("/pending-approvals/{approval_id}/approve")
def approve_action(approval_id: int, body: ApprovalActionBody, user: Usr):
    require_permission(user, "finance.waiver.approve")
    import json
    from backend.core.db import _get_conn
    conn = _get_conn()
    pa = conn.execute("SELECT * FROM pending_approvals WHERE id=? AND status='pending'", (approval_id,)).fetchone()
    if not pa:
        raise HTTPException(404, "Approval request not found or already resolved")
    if pa["requested_by"] == user["id"]:
        raise HTTPException(403, "You cannot approve your own request (maker/checker rule)")

    payload = json.loads(pa["payload"])
    action  = pa["action_type"]

    if action == "waiver":
        wbody = WaiverBody(**payload)
        conn.execute(
            """INSERT INTO fee_waivers
               (student_id, bill_id, academic_year_id, waiver_type, discount_percent, approved_by, reason)
               VALUES (?,?,?,?,?,?,?)""",
            (wbody.student_id, wbody.bill_id, wbody.academic_year_id,
             wbody.waiver_type, wbody.discount_percent, user["id"], wbody.reason),
        )
        if wbody.bill_id:
            bill = conn.execute("SELECT * FROM student_bills WHERE id=?", (wbody.bill_id,)).fetchone()
            if bill:
                discount = round(bill["amount_due"] * (wbody.discount_percent / 100), 2)
                new_disc = min(bill["amount_due"], (bill["discount_amount"] or 0) + discount)
                eff_out  = bill["amount_due"] - new_disc - bill["amount_paid"]
                status   = "waived" if eff_out <= 0.01 else ("partial" if bill["amount_paid"] > 0 else "unpaid")
                conn.execute("UPDATE student_bills SET discount_amount=?, status=? WHERE id=?", (new_disc, status, wbody.bill_id))

    elif action == "payment_reversal":
        payment_id = payload.get("payment_id")
        reason     = payload.get("reason", "")
        payment = conn.execute("SELECT * FROM fee_payments WHERE id=?", (payment_id,)).fetchone()
        if payment:
            conn.execute("UPDATE fee_payments SET status='reversed', notes=? WHERE id=?", (f"Reversed: {reason}", payment_id))
            if payment.get("bill_id"):
                bill = conn.execute("SELECT * FROM student_bills WHERE id=?", (payment["bill_id"],)).fetchone()
                if bill:
                    new_paid = max(0.0, bill["amount_paid"] - payment["amount_paid"])
                    eff_out  = bill["amount_due"] - (bill["discount_amount"] or 0) - new_paid
                    status   = "paid" if eff_out <= 0.01 and new_paid > 0 else ("partial" if new_paid > 0 else "unpaid")
                    conn.execute("UPDATE student_bills SET amount_paid=?, status=? WHERE id=?", (new_paid, status, payment["bill_id"]))

    conn.execute(
        "UPDATE pending_approvals SET status='approved', approved_by=?, note=?, resolved_at=datetime('now') WHERE id=?",
        (user["id"], body.note, approval_id),
    )
    conn.commit()
    return {"ok": True}


@router.post("/pending-approvals/{approval_id}/reject")
def reject_action(approval_id: int, body: ApprovalActionBody, user: Usr):
    require_permission(user, "finance.waiver.approve")
    from backend.core.db import _get_conn
    conn = _get_conn()
    conn.execute(
        "UPDATE pending_approvals SET status='rejected', approved_by=?, note=?, resolved_at=datetime('now') WHERE id=?",
        (user["id"], body.note, approval_id),
    )
    conn.commit()
    return {"ok": True}


@router.post("/request-reversal")
def request_reversal(user: Usr, payment_id: int = Query(...), reason: str = Query("")):
    """Submit a payment reversal for maker/checker approval."""
    require_permission(user, "finance.payment.void")
    import json
    from backend.core.db import _get_conn
    conn = _get_conn()
    payment = conn.execute("SELECT * FROM fee_payments WHERE id=?", (payment_id,)).fetchone()
    if not payment:
        raise HTTPException(404, "Payment not found")
    cur = conn.execute(
        "INSERT INTO pending_approvals (action_type, payload, description, requested_by) VALUES (?,?,?,?)",
        ("payment_reversal", json.dumps({"payment_id": payment_id, "reason": reason}),
         f"Reversal of payment #{payment_id} — {reason}", user["id"]),
    )
    conn.commit()
    return {"id": cur.lastrowid, "ok": True, "message": "Reversal request submitted for approval"}


# ── Mobile money confirmation ──────────────────────────────────────────────────

@router.post("/payment/{payment_id}/confirm")
def confirm_mobile_payment(payment_id: int, user: Usr):
    """Confirm a pending mobile money payment after manual verification."""
    require_permission(user, "finance.payment.record")
    from backend.core.db import _get_conn
    conn = _get_conn()
    payment = conn.execute("SELECT * FROM fee_payments WHERE id=? AND status='pending'", (payment_id,)).fetchone()
    if not payment:
        raise HTTPException(404, "Pending payment not found")
    conn.execute(
        "UPDATE fee_payments SET status='confirmed', confirmed_by=?, confirmed_at=datetime('now') WHERE id=?",
        (user["id"], payment_id),
    )
    if payment["bill_id"]:
        bill = conn.execute("SELECT * FROM student_bills WHERE id=?", (payment["bill_id"],)).fetchone()
        if bill:
            new_paid = bill["amount_paid"] + payment["amount_paid"]
            eff_out  = bill["amount_due"] - (bill["discount_amount"] or 0) - new_paid
            status   = "paid" if eff_out <= 0.01 else "partial"
            conn.execute("UPDATE student_bills SET amount_paid=?, status=? WHERE id=?", (new_paid, status, payment["bill_id"]))
    conn.commit()
    return {"ok": True}


# ── Parent balance view ────────────────────────────────────────────────────────

@router.get("/parent-balance")
def get_parent_balance(user: Usr, academic_year_id: int = Query(None)):
    """Returns balances for all children linked to the logged-in parent account."""
    from backend.core.db import _get_conn
    conn = _get_conn()
    children = conn.execute(
        "SELECT pa.student_id, pa.relation FROM parent_portal_accounts pa WHERE pa.user_id=?",
        (user["id"],),
    ).fetchall()
    if not children:
        raise HTTPException(404, "No children linked to this account")

    result = []
    for child in children:
        student = conn.execute("SELECT * FROM students WHERE id=?", (child["student_id"],)).fetchone()
        if not student:
            continue
        where = ["sb.student_id=?"]
        params: list = [child["student_id"]]
        if academic_year_id:
            where.append("sb.academic_year_id=?")
            params.append(academic_year_id)
        bills = conn.execute(
            f"""SELECT sb.*, ft.name AS fee_type_name, ay.label AS year_label
                FROM student_bills sb
                JOIN fee_structures fs ON fs.id = sb.fee_structure_id
                JOIN fee_types ft ON ft.id = fs.fee_type_id
                JOIN academic_years ay ON ay.id = sb.academic_year_id
                WHERE {' AND '.join(where)}
                ORDER BY sb.created_at DESC""",
            params,
        ).fetchall()
        total_billed   = sum(b["amount_due"] for b in bills)
        total_discount = sum((b["discount_amount"] or 0) for b in bills)
        total_paid     = sum(b["amount_paid"] for b in bills)
        result.append({
            "student_id":    student["id"],
            "student_name":  f"{student['first_name']} {student['last_name']}",
            "admission_no":  student["admission_no"],
            "relation":      child["relation"],
            "bills":         [dict(b) for b in bills],
            "total_billed":  total_billed,
            "total_discount":total_discount,
            "total_paid":    total_paid,
            "balance":       total_billed - total_discount - total_paid,
        })
    return result
