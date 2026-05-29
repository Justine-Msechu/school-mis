from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from backend.core.security import require_permission
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["accounting"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/expenses")
def get_expenses(user: Usr, limit: int = Query(50)):
    rows = fetch_all(
        "SELECT * FROM expenses ORDER BY expense_date DESC LIMIT ?", (limit,)
    )
    return [dict(r) for r in rows]


class ExpenseBody(BaseModel):
    category:     str
    description:  str
    amount:       float
    expense_date: str
    reference:    str = ""
    vendor:       str = ""


@router.post("/expenses")
def record_expense(body: ExpenseBody, user: Usr):
    require_permission(user, "accounting.expense.record")
    if not body.description.strip():
        raise HTTPException(400, "Description is required.")
    exp_id = execute(
        """INSERT INTO expenses
           (category, description, amount, expense_date, receipt_ref, recorded_by)
           VALUES (?,?,?,?,?,?)""",
        (body.category, body.description.strip(), body.amount, body.expense_date,
         body.reference.strip() or None, user["id"]),
    )
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "expense_recorded", "expenses", exp_id,
             f"{body.category} {body.amount:,.0f} — {body.description.strip()[:60]}"),
        )
    except Exception:
        pass
    return {"id": exp_id, "ok": True}


@router.get("/summary")
def get_summary(user: Usr, period: str = Query("month")):
    try:
        require_permission(user, "accounting.view")
        if period == "month":
            df = "AND strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')"
            ef = "AND strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')"
            wf = "AND strftime('%Y-%m',fw.created_at)=strftime('%Y-%m','now')"
        elif period == "year":
            df = "AND strftime('%Y',payment_date)=strftime('%Y','now')"
            ef = "AND strftime('%Y',expense_date)=strftime('%Y','now')"
            wf = "AND strftime('%Y',fw.created_at)=strftime('%Y','now')"
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
    except Exception:
        return {}


@router.get("/categories")
def get_categories(user: Usr):
    rows = fetch_all("SELECT DISTINCT category FROM expenses WHERE category IS NOT NULL ORDER BY category")
    return [r["category"] for r in rows]
