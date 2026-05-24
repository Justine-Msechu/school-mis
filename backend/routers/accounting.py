from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.accounting_service import accounting_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all

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
    hydrate_session(user)
    try:
        exp_id = accounting_service.record_expense(body.model_dump())
        return {"id": exp_id, "ok": True}
    except (ServiceError, PolicyViolation) as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.get("/summary")
def get_summary(user: Usr, period: str = Query("month")):
    hydrate_session(user)
    try:
        return accounting_service.get_summary(period)
    except Exception:
        return {}


@router.get("/categories")
def get_categories(user: Usr):
    rows = fetch_all("SELECT DISTINCT category FROM expenses WHERE category IS NOT NULL ORDER BY category")
    return [r["category"] for r in rows]
