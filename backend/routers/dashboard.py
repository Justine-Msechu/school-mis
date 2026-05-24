from typing import Annotated
from datetime import date
from fastapi import APIRouter, Depends
from backend.deps import require_auth
from database.db import fetch_one, fetch_all

router = APIRouter(tags=["dashboard"])

Usr = Annotated[dict, Depends(require_auth)]


def _n(row) -> int:
    if row is None: return 0
    return dict(row).get("n", 0)

@router.get("/stats")
def get_stats(user: Usr):
    students = _n(fetch_one("SELECT COUNT(*) as n FROM students WHERE is_active=1"))
    teachers = _n(fetch_one("SELECT COUNT(*) as n FROM users WHERE role IN ('subject_teacher','class_teacher') AND is_active=1"))
    classes  = _n(fetch_one("SELECT COUNT(*) as n FROM classes"))

    try:
        pending_fees = int(_n(fetch_one(
            "SELECT COALESCE(SUM(amount - paid_amount),0) as n FROM fee_allocations WHERE paid_amount < amount"
        )))
    except Exception:
        pending_fees = 0

    today = date.today().isoformat()
    try:
        attendance_today = _n(fetch_one(
            "SELECT COUNT(*) as n FROM attendance WHERE date=? AND status='present'", (today,)
        ))
        total_today = _n(fetch_one("SELECT COUNT(*) as n FROM attendance WHERE date=?", (today,))) or 1
        attendance_rate = round(attendance_today / total_today * 100, 1)
    except Exception:
        attendance_today, attendance_rate = 0, 0.0

    try:
        activity_rows = fetch_all(
            """SELECT al.id, al.action, al.module, al.created_at,
                      u.full_name as user_name
               FROM audit_log al
               LEFT JOIN users u ON u.id = al.user_id
               ORDER BY al.id DESC LIMIT 20"""
        )
        activity = [dict(r) for r in activity_rows]
    except Exception:
        activity = []

    return {
        "students":         students,
        "teachers":         teachers,
        "classes":          classes,
        "pending_fees":     pending_fees,
        "attendance_today": attendance_today,
        "attendance_rate":  attendance_rate,
        "recent_activity":  activity,
    }
