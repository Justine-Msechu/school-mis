from typing import Annotated
from datetime import date
from fastapi import APIRouter
from backend.deps import require_auth
from database.db import fetch_one, fetch_all

router = APIRouter(tags=["dashboard"])

Usr = Annotated[dict, require_auth]


@router.get("/stats")
def get_stats(user: Usr):
    students = (fetch_one("SELECT COUNT(*) as n FROM students WHERE is_active=1") or {}).get("n", 0)
    teachers = (fetch_one("SELECT COUNT(*) as n FROM users WHERE role IN ('subject_teacher','class_teacher') AND is_active=1") or {}).get("n", 0)
    classes  = (fetch_one("SELECT COUNT(*) as n FROM classes") or {}).get("n", 0)

    # Pending fees — sum of unpaid allocations
    fees_row = fetch_one(
        "SELECT COALESCE(SUM(amount - paid_amount),0) as n FROM fee_allocations WHERE paid_amount < amount"
    )
    pending_fees = int((fees_row or {}).get("n", 0))

    # Attendance today
    today = date.today().isoformat()
    att_row = fetch_one(
        "SELECT COUNT(*) as n FROM attendance WHERE date=? AND status='present'", (today,)
    )
    attendance_today = (att_row or {}).get("n", 0)
    att_rate_row = fetch_one(
        "SELECT COUNT(*) as n FROM attendance WHERE date=?", (today,)
    )
    total_today = (att_rate_row or {}).get("n", 0) or 1
    attendance_rate = round(attendance_today / total_today * 100, 1)

    # Recent audit activity
    try:
        activity_rows = fetch_all(
            """SELECT al.id, al.action, al.module, al.created_at,
                      (u.first_name || ' ' || u.last_name) as user_name
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
