from typing import Annotated
from datetime import date
from fastapi import APIRouter, Depends
from backend.deps import require_auth
from backend.core.authz import compute_effective_permissions
from backend.core.cache import cache_get, cache_set
from database.db import fetch_one, fetch_all

router = APIRouter(tags=["dashboard"])

Usr = Annotated[dict, Depends(require_auth)]


def _n(row) -> int:
    if row is None:
        return 0
    return dict(row).get("n", 0)


@router.get("/stats")
def get_stats(user: Usr):
    user_id   = user["id"]
    school_id = user.get("school_id", 0)
    role      = user.get("role", "")

    cache_key = f"school:{school_id}:dash:stats:{user_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    perms  = compute_effective_permissions(user_id)
    is_all = "*" in perms

    def can(p: str) -> bool:
        return is_all or p in perms

    result: dict = {}
    today = date.today().isoformat()

    # ── School-wide counts ────────────────────────────────────────────────────
    if can("student.view"):
        try:
            result["students"] = _n(fetch_one(
                "SELECT COUNT(*) as n FROM students WHERE is_active=1"
            ))
        except Exception:
            result["students"] = 0

    if can("teachers.view"):
        try:
            result["teachers"] = _n(fetch_one(
                "SELECT COUNT(*) as n FROM users "
                "WHERE role IN ('subject_teacher','class_teacher') AND is_active=1"
            ))
        except Exception:
            result["teachers"] = 0

    if can("classes.view"):
        try:
            result["classes"] = _n(fetch_one("SELECT COUNT(*) as n FROM classes"))
        except Exception:
            result["classes"] = 0

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

    # ── Inventory ─────────────────────────────────────────────────────────────
    if can("inventory.view"):
        try:
            result["inventory_items"]    = _n(fetch_one("SELECT COUNT(*) as n FROM inventory_items WHERE is_active=1"))
            result["inventory_low_stock"] = _n(fetch_one("SELECT COUNT(*) as n FROM inventory_items WHERE is_active=1 AND stock_qty <= reorder_qty"))
            result["inventory_requests"]  = _n(fetch_one("SELECT COUNT(*) as n FROM inventory_requests WHERE status='pending'"))
            sv = fetch_one("SELECT COALESCE(SUM(stock_qty * unit_price),0) as n FROM inventory_items WHERE is_active=1")
            result["inventory_value"] = int(dict(sv)["n"]) if sv else 0
        except Exception:
            result["inventory_items"] = 0

    # ── Audit / Recent Activity ───────────────────────────────────────────────
    if can("audit.view"):
        try:
            rows = fetch_all(
                """SELECT al.id, al.action, al.table_name AS module,
                          al.ts AS created_at,
                          u.full_name as user_name
                   FROM audit_log al
                   LEFT JOIN users u ON u.id = al.user_id
                   ORDER BY al.id DESC LIMIT 20"""
            )
            result["recent_activity"] = [dict(r) for r in rows]
        except Exception:
            result["recent_activity"] = []

    cache_set(cache_key, result, ttl=60)
    return result
