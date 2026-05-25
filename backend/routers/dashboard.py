from typing import Annotated
from datetime import date
from fastapi import APIRouter, Depends
from backend.deps import require_auth
from backend.core.authz import compute_effective_permissions
from database.db import fetch_one, fetch_all

router = APIRouter(tags=["dashboard"])

Usr = Annotated[dict, Depends(require_auth)]


def _n(row) -> int:
    if row is None:
        return 0
    return dict(row).get("n", 0)


@router.get("/stats")
def get_stats(user: Usr):
    user_id = user["id"]
    role    = user.get("role", "")
    perms   = compute_effective_permissions(user_id)
    is_all  = "*" in perms

    def can(p: str) -> bool:
        return is_all or p in perms

    result: dict = {}
    today = date.today().isoformat()

    # ── School-wide counts ────────────────────────────────────────────────────
    if can("student.view"):
        result["students"] = _n(fetch_one(
            "SELECT COUNT(*) as n FROM students WHERE is_active=1"
        ))

    if can("teachers.view"):
        result["teachers"] = _n(fetch_one(
            "SELECT COUNT(*) as n FROM users "
            "WHERE role IN ('subject_teacher','class_teacher') AND is_active=1"
        ))

    if can("classes.view"):
        result["classes"] = _n(fetch_one("SELECT COUNT(*) as n FROM classes"))

    # ── Finance ───────────────────────────────────────────────────────────────
    if can("finance.view"):
        try:
            result["pending_fees"] = int(_n(fetch_one(
                "SELECT COALESCE(SUM(amount - paid_amount),0) as n "
                "FROM fee_allocations WHERE paid_amount < amount"
            )))
        except Exception:
            result["pending_fees"] = 0

    # ── Attendance ────────────────────────────────────────────────────────────
    if can("attendance.view"):
        is_teacher_role = role in ("class_teacher", "subject_teacher")
        if is_all or not is_teacher_role:
            # School-wide
            try:
                att = _n(fetch_one(
                    "SELECT COUNT(*) as n FROM attendance WHERE date=? AND status='present'",
                    (today,)
                ))
                tot = _n(fetch_one(
                    "SELECT COUNT(*) as n FROM attendance WHERE date=?", (today,)
                )) or 1
                result["attendance_today"] = att
                result["attendance_rate"]  = round(att / tot * 100, 1)
            except Exception:
                result["attendance_today"] = 0
                result["attendance_rate"]  = 0.0
        else:
            # Scoped to teacher's own classes
            try:
                class_filter = (
                    "s.class_id IN ("
                    "  SELECT class_id FROM class_teacher_assignments WHERE user_id=? AND is_active=1"
                    "  UNION"
                    "  SELECT class_id FROM teacher_assignments WHERE user_id=? AND is_active=1"
                    ")"
                )
                att = _n(fetch_one(
                    f"SELECT COUNT(*) as n FROM attendance a "
                    f"JOIN students s ON s.id=a.student_id "
                    f"WHERE a.date=? AND a.status='present' AND {class_filter}",
                    (today, user_id, user_id)
                ))
                tot = _n(fetch_one(
                    f"SELECT COUNT(*) as n FROM attendance a "
                    f"JOIN students s ON s.id=a.student_id "
                    f"WHERE a.date=? AND {class_filter}",
                    (today, user_id, user_id)
                )) or 1
                result["attendance_today"] = att
                result["attendance_rate"]  = round(att / tot * 100, 1)
            except Exception:
                result["attendance_today"] = 0
                result["attendance_rate"]  = 0.0

    # ── Welfare ───────────────────────────────────────────────────────────────
    if can("welfare.view"):
        try:
            result["welfare_cases"] = _n(fetch_one(
                "SELECT COUNT(*) as n FROM welfare_cases WHERE status='active'"
            ))
        except Exception:
            result["welfare_cases"] = 0

    # ── Health ────────────────────────────────────────────────────────────────
    if can("health.view"):
        try:
            result["health_visits_today"] = _n(fetch_one(
                "SELECT COUNT(*) as n FROM health_visits WHERE date=?", (today,)
            ))
        except Exception:
            result["health_visits_today"] = 0

    # ── Audit / Recent Activity ───────────────────────────────────────────────
    if can("audit.view"):
        try:
            rows = fetch_all(
                """SELECT al.id, al.action, al.module, al.created_at,
                          u.full_name as user_name
                   FROM audit_log al
                   LEFT JOIN users u ON u.id = al.user_id
                   ORDER BY al.id DESC LIMIT 20"""
            )
            result["recent_activity"] = [dict(r) for r in rows]
        except Exception:
            result["recent_activity"] = []

    return result
