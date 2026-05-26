"""
Invoices router — secure invoice lifecycle with state machine.

States:  draft → approved → (partially_paid →) paid
                         ↘ voided (at any non-paid state)
                         ↘ cancelled (draft only)

Control numbers are issued only after approval and are cryptographically
tied to the invoice ID via HMAC-SHA256.  Payments are only accepted for
invoices with an active control number.
"""

import json
import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from backend.deps import require_auth
from backend.core.security import require_permission
from backend.core.control_number import generate_control_number, verify_control_number

router = APIRouter(tags=["invoices"])
Usr = Annotated[dict, Depends(require_auth)]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conn():
    from backend.core.db import _get_conn
    return _get_conn()


def _audit(conn, entity_type: str, entity_id: int, action: str,
           actor: dict, detail: str = "", before=None, after=None):
    conn.execute(
        """INSERT INTO finance_audit_log
           (entity_type, entity_id, action, actor_id, actor_name,
            before_json, after_json, detail)
           VALUES (?,?,?,?,?,?,?,?)""",
        (entity_type, entity_id, action,
         actor["id"], actor.get("username", actor.get("full_name", "")),
         json.dumps(before) if before is not None else None,
         json.dumps(after)  if after  is not None else None,
         detail),
    )


def _get_invoice_or_404(conn, invoice_id: int) -> dict:
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Invoice not found")
    return dict(row)


def _invoice_no(conn, invoice_id: int) -> str:
    yr = datetime.date.today().year
    return f"INV-{yr}-{invoice_id:05d}"


# ── Create invoice ─────────────────────────────────────────────────────────────

class InvoiceItemIn(BaseModel):
    bill_id:         int | None = None
    fee_type_id:     int | None = None
    description:     str
    amount:          float = Field(gt=0)
    discount_amount: float = 0
    quantity:        int   = 1


class CreateInvoiceBody(BaseModel):
    student_id:       int
    academic_year_id: int | None = None
    term:             int | None = None
    items:            list[InvoiceItemIn] = Field(min_length=1)
    notes:            str | None = None


@router.post("")
def create_invoice(body: CreateInvoiceBody, user: Usr):
    require_permission(user, "finance.payment.record")
    if not body.items:
        raise HTTPException(400, "At least one line item is required")

    conn = _conn()
    student = conn.execute(
        "SELECT id, first_name || ' ' || last_name AS name FROM students WHERE id=? AND is_active=1",
        (body.student_id,),
    ).fetchone()
    if not student:
        raise HTTPException(404, "Student not found or inactive")

    total = sum(
        round((item.amount - item.discount_amount) * item.quantity, 2)
        for item in body.items
    )
    discount_total = sum(
        round(item.discount_amount * item.quantity, 2)
        for item in body.items
    )

    cur = conn.execute(
        """INSERT INTO invoices
           (invoice_no, student_id, academic_year_id, term,
            total_amount, discount_amount, notes, created_by)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("PENDING", body.student_id, body.academic_year_id, body.term,
         total, discount_total, body.notes, user["id"]),
    )
    inv_id = cur.lastrowid
    inv_no = _invoice_no(conn, inv_id)
    conn.execute("UPDATE invoices SET invoice_no=? WHERE id=?", (inv_no, inv_id))

    for item in body.items:
        line_total = round((item.amount - item.discount_amount) * item.quantity, 2)
        conn.execute(
            """INSERT INTO invoice_items
               (invoice_id, bill_id, fee_type_id, description,
                amount, discount_amount, quantity, line_total)
               VALUES (?,?,?,?,?,?,?,?)""",
            (inv_id, item.bill_id, item.fee_type_id, item.description,
             item.amount, item.discount_amount, item.quantity, line_total),
        )

    _audit(conn, "invoice", inv_id, "created", user,
           detail=f"Invoice {inv_no} created for student {student['name']}",
           after={"invoice_no": inv_no, "total": total, "student_id": body.student_id})
    conn.commit()
    return {"id": inv_id, "invoice_no": inv_no, "total_amount": total, "status": "draft"}


# ── List invoices ──────────────────────────────────────────────────────────────

@router.get("")
def list_invoices(
    user: Usr,
    student_id:       int = Query(None),
    academic_year_id: int = Query(None),
    status:           str = Query(None),
    limit:            int = Query(100),
):
    require_permission(user, "finance.view")
    conn = _conn()
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("i.student_id=?"); params.append(student_id)
    if academic_year_id:
        where.append("i.academic_year_id=?"); params.append(academic_year_id)
    if status:
        where.append("i.status=?"); params.append(status)

    rows = conn.execute(
        f"""SELECT i.*,
                   s.first_name || ' ' || s.last_name AS student_name,
                   s.admission_no,
                   c.name AS class_name,
                   creator.username AS created_by_name,
                   approver.username AS approved_by_name
            FROM invoices i
            JOIN students s ON s.id = i.student_id
            LEFT JOIN classes c ON c.id = s.class_id
            LEFT JOIN users creator  ON creator.id  = i.created_by
            LEFT JOIN users approver ON approver.id = i.approved_by
            WHERE {' AND '.join(where)}
            ORDER BY i.created_at DESC
            LIMIT ?""",
        params + [limit],
    ).fetchall()
    return [dict(r) for r in rows]


# ── Get single invoice ─────────────────────────────────────────────────────────

@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, user: Usr):
    require_permission(user, "finance.view")
    conn = _conn()
    inv = conn.execute(
        """SELECT i.*,
                  s.first_name || ' ' || s.last_name AS student_name,
                  s.admission_no,
                  c.name AS class_name,
                  creator.username AS created_by_name,
                  approver.username AS approved_by_name
           FROM invoices i
           JOIN students s ON s.id = i.student_id
           LEFT JOIN classes c ON c.id = s.class_id
           LEFT JOIN users creator  ON creator.id  = i.created_by
           LEFT JOIN users approver ON approver.id = i.approved_by
           WHERE i.id=?""",
        (invoice_id,),
    ).fetchone()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    items = conn.execute(
        """SELECT ii.*, ft.name AS fee_type_name
           FROM invoice_items ii
           LEFT JOIN fee_types ft ON ft.id = ii.fee_type_id
           WHERE ii.invoice_id=?
           ORDER BY ii.id""",
        (invoice_id,),
    ).fetchall()

    audit = conn.execute(
        """SELECT fal.*, u.username AS actor_name_db
           FROM finance_audit_log fal
           LEFT JOIN users u ON u.id = fal.actor_id
           WHERE fal.entity_type='invoice' AND fal.entity_id=?
           ORDER BY fal.created_at""",
        (invoice_id,),
    ).fetchall()

    return {
        **dict(inv),
        "items": [dict(r) for r in items],
        "audit": [dict(r) for r in audit],
    }


# ── Approve invoice ────────────────────────────────────────────────────────────

@router.post("/{invoice_id}/approve")
def approve_invoice(invoice_id: int, user: Usr):
    """Approve a draft invoice.  Approver must be different from creator."""
    require_permission(user, "finance.waiver.approve")
    conn = _conn()
    inv = _get_invoice_or_404(conn, invoice_id)

    if inv["status"] != "draft":
        raise HTTPException(400, f"Invoice is {inv['status']} — only draft invoices can be approved")
    if inv["created_by"] == user["id"]:
        raise HTTPException(403, "Maker/checker rule: you cannot approve your own invoice")

    before = {"status": inv["status"]}
    conn.execute(
        "UPDATE invoices SET status='approved', approved_by=?, approved_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
        (user["id"], invoice_id),
    )
    _audit(conn, "invoice", invoice_id, "approved", user,
           detail=f"Invoice {inv['invoice_no']} approved",
           before=before, after={"status": "approved"})
    conn.commit()
    return {"ok": True, "status": "approved"}


# ── Issue control number ───────────────────────────────────────────────────────

class IssueControlBody(BaseModel):
    expires_days: int = 30   # how many days the control number stays valid

@router.post("/{invoice_id}/issue-control-number")
def issue_control_number(invoice_id: int, body: IssueControlBody, user: Usr):
    """Generate a cryptographically secure control number for an approved invoice."""
    require_permission(user, "finance.payment.record")
    conn = _conn()
    inv = _get_invoice_or_404(conn, invoice_id)

    if inv["status"] not in ("approved", "partially_paid"):
        raise HTTPException(400, "Control numbers can only be issued for approved or partially-paid invoices")
    if inv["control_number"]:
        return {
            "ok": True,
            "control_number": inv["control_number"],
            "expires_at": inv["control_number_expires_at"],
            "already_issued": True,
        }

    ctrl = generate_control_number(invoice_id)
    expires_at = (
        datetime.date.today() + datetime.timedelta(days=body.expires_days)
    ).isoformat()

    conn.execute(
        """UPDATE invoices
           SET control_number=?, control_number_expires_at=?,
               control_number_issued_at=datetime('now'), updated_at=datetime('now')
           WHERE id=?""",
        (ctrl, expires_at, invoice_id),
    )
    _audit(conn, "invoice", invoice_id, "control_number_issued", user,
           detail=f"Control number issued, expires {expires_at}",
           after={"control_number": ctrl, "expires_at": expires_at})
    conn.commit()
    return {"ok": True, "control_number": ctrl, "expires_at": expires_at}


# ── Record payment against invoice ────────────────────────────────────────────

class InvoicePaymentBody(BaseModel):
    control_number:  str
    amount:          float = Field(gt=0)
    payment_date:    str
    method:          str = "Cash"
    reference_no:    str = ""
    notes:           str = ""

@router.post("/{invoice_id}/pay")
def pay_invoice(invoice_id: int, body: InvoicePaymentBody, user: Usr):
    """Record a payment against an invoice.  Control number must match and be unexpired."""
    require_permission(user, "finance.payment.record")
    conn = _conn()
    inv = _get_invoice_or_404(conn, invoice_id)

    if inv["status"] not in ("approved", "partially_paid"):
        raise HTTPException(400, f"Cannot pay a {inv['status']} invoice")
    if not inv["control_number"]:
        raise HTTPException(400, "No control number issued for this invoice — issue one first")
    if inv["control_number"] != body.control_number:
        raise HTTPException(400, "Control number does not match this invoice")
    if not verify_control_number(body.control_number, invoice_id):
        raise HTTPException(400, "Control number failed integrity check — possible forgery")

    expires = inv.get("control_number_expires_at")
    if expires and body.payment_date > expires:
        raise HTTPException(400, f"Control number expired on {expires} — please issue a new one")

    net_due = round(inv["total_amount"] - inv["discount_amount"] - inv["paid_amount"], 2)
    if body.amount > net_due + 0.01:
        raise HTTPException(400, f"Payment amount {body.amount:,.2f} exceeds remaining balance {net_due:,.2f}")

    # Record fee_payment row for full audit trail
    try:
        conn.execute(
            """INSERT INTO fee_payments
               (student_id, amount_paid, payment_date, payment_method,
                reference_no, notes, control_number, recorded_by, status)
               VALUES (?,?,?,?,?,?,?,?,'confirmed')""",
            (inv["student_id"], body.amount, body.payment_date, body.method,
             body.reference_no or None, body.notes or None,
             body.control_number, user["id"]),
        )
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(409, f"Duplicate transaction reference: {body.reference_no}")
        raise HTTPException(400, str(e))

    new_paid = round(inv["paid_amount"] + body.amount, 2)
    new_status = "paid" if new_paid >= net_due - 0.01 else "partially_paid"

    before = {"paid_amount": inv["paid_amount"], "status": inv["status"]}
    conn.execute(
        "UPDATE invoices SET paid_amount=?, status=?, updated_at=datetime('now') WHERE id=?",
        (new_paid, new_status, invoice_id),
    )
    _audit(conn, "invoice", invoice_id, "payment_recorded", user,
           detail=f"Payment of {body.amount:,.2f} via {body.method} (ref: {body.reference_no or '-'})",
           before=before, after={"paid_amount": new_paid, "status": new_status})
    conn.commit()
    return {
        "ok": True,
        "paid_amount": new_paid,
        "remaining_balance": round(net_due - body.amount, 2),
        "status": new_status,
    }


# ── Void invoice ───────────────────────────────────────────────────────────────

class VoidBody(BaseModel):
    reason: str = Field(min_length=5)

@router.post("/{invoice_id}/void")
def void_invoice(invoice_id: int, body: VoidBody, user: Usr):
    """Void an invoice.  Paid invoices cannot be voided."""
    require_permission(user, "finance.payment.void")
    conn = _conn()
    inv = _get_invoice_or_404(conn, invoice_id)

    if inv["status"] == "paid":
        raise HTTPException(400, "Paid invoices cannot be voided — request a reversal instead")
    if inv["status"] == "voided":
        raise HTTPException(400, "Invoice is already voided")
    if inv["created_by"] == user["id"] and inv["status"] != "draft":
        raise HTTPException(403, "Maker/checker rule: you cannot void an approved invoice you created")

    before = {"status": inv["status"]}
    conn.execute(
        """UPDATE invoices
           SET status='voided', voided_by=?, voided_at=datetime('now'),
               void_reason=?, updated_at=datetime('now')
           WHERE id=?""",
        (user["id"], body.reason, invoice_id),
    )
    _audit(conn, "invoice", invoice_id, "voided", user,
           detail=f"Invoice voided: {body.reason}",
           before=before, after={"status": "voided"})
    conn.commit()
    return {"ok": True, "status": "voided"}


# ── Audit trail ────────────────────────────────────────────────────────────────

@router.get("/{invoice_id}/audit")
def get_invoice_audit(invoice_id: int, user: Usr):
    require_permission(user, "finance.view")
    conn = _conn()
    # Confirm invoice exists
    if not conn.execute("SELECT id FROM invoices WHERE id=?", (invoice_id,)).fetchone():
        raise HTTPException(404, "Invoice not found")
    rows = conn.execute(
        """SELECT fal.*, u.username AS actor_username
           FROM finance_audit_log fal
           LEFT JOIN users u ON u.id = fal.actor_id
           WHERE fal.entity_type='invoice' AND fal.entity_id=?
           ORDER BY fal.created_at""",
        (invoice_id,),
    ).fetchall()
    return [dict(r) for r in rows]
