"""
Subscription management.

Plans:
  trial    — 30-day free trial, max 50 users
  standard — paid, max 150 users
  premium  — paid, unlimited users
  lifetime — one-time purchase, unlimited

Status is checked on every /api/auth/me call and surfaced in the response
so the frontend can show warnings without an extra round trip.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import require_auth
from database.db import execute, fetch_one

router = APIRouter(tags=["subscription"])
Usr = Annotated[dict, Depends(require_auth)]

PLANS = {
    "trial":    {"label": "Free Trial",   "max_users": 50,   "color": "#F59E0B"},
    "standard": {"label": "Standard",     "max_users": 150,  "color": "#0891B2"},
    "premium":  {"label": "Premium",      "max_users": 500,  "color": "#7C3AED"},
    "lifetime": {"label": "Lifetime",     "max_users": 9999, "color": "#059669"},
}


def get_subscription_info(school_id: int | None = None) -> dict:
    """Return subscription status dict for the given school (or global if no school_id)."""
    row = None
    if school_id:
        row = fetch_one(
            "SELECT * FROM schools WHERE id=?", (school_id,)
        )
    if not row:
        row = fetch_one("SELECT * FROM schools LIMIT 1")

    # Auto-seed school record for legacy single-tenant installs
    if not row:
        name_row = fetch_one("SELECT value FROM school_config WHERE key='school_name'")
        school_name = (name_row["value"] if name_row else None) or "School"
        try:
            sid = execute(
                "INSERT OR IGNORE INTO schools (name, plan, max_users, is_active, subscription_status) VALUES (?, 'trial', 50, 1, 'trial')",
                (school_name,),
            )
            if sid:
                row = fetch_one("SELECT * FROM schools WHERE id=?", (sid,))
        except Exception:
            pass

    if not row:
        return {
            "plan": "trial",
            "plan_label": "Free Trial",
            "plan_color": "#F59E0B",
            "status": "trial",
            "trial_ends": None,
            "days_left": None,
            "is_active": True,
            "max_users": 50,
            "warning": None,
        }

    school = dict(row)
    plan    = school.get("plan", "trial")
    plan_info = PLANS.get(plan, PLANS["trial"])
    status  = school.get("subscription_status", "trial")
    trial_ends = school.get("trial_ends")

    days_left = None
    warning   = None
    if trial_ends:
        try:
            delta = (datetime.strptime(trial_ends, "%Y-%m-%d") - datetime.utcnow()).days
            days_left = max(delta, 0)
            if plan == "trial":
                if delta <= 0:
                    status  = "expired"
                    warning = "Your trial has expired. Please upgrade to continue using the system."
                elif delta <= 7:
                    warning = f"Trial expires in {delta} day{'s' if delta != 1 else ''}. Upgrade to avoid interruption."
        except ValueError:
            pass

    return {
        "plan":       plan,
        "plan_label": plan_info["label"],
        "plan_color": plan_info["color"],
        "status":     status,
        "trial_ends": trial_ends,
        "days_left":  days_left,
        "is_active":  school.get("is_active", 1) == 1 and status != "expired",
        "max_users":  plan_info["max_users"],
        "warning":    warning,
        "school_name": school.get("name", ""),
    }


@router.get("/status")
def subscription_status(user: Usr):
    return get_subscription_info(user.get("school_id"))


class ActivatePayload(BaseModel):
    school_id: int | None = None   # None = current school
    plan:      str                  # trial | standard | premium | lifetime
    trial_ends: str | None = None  # YYYY-MM-DD, only for trial extension


@router.post("/activate")
def activate_subscription(body: ActivatePayload, user: Usr):
    """Admin-only: set or change a school's subscription plan."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Only admins can manage subscriptions.")
    if body.plan not in PLANS:
        raise HTTPException(400, f"Unknown plan '{body.plan}'. Valid: {list(PLANS)}")

    school_id = body.school_id or user.get("school_id")
    school = fetch_one("SELECT id FROM schools WHERE id=?", (school_id,)) if school_id else \
             fetch_one("SELECT id FROM schools LIMIT 1")

    if not school:
        # Auto-create school record from school_config for existing single-tenant installations
        name_row = fetch_one("SELECT value FROM school_config WHERE key='school_name'")
        school_name = (name_row["value"] if name_row else "School") or "School"
        sid = execute(
            "INSERT INTO schools (name, plan, max_users, is_active, subscription_status) VALUES (?, 'trial', 50, 1, 'trial')",
            (school_name,),
        )
        school = fetch_one("SELECT id FROM schools WHERE id=?", (sid,))

    if not school:
        raise HTTPException(404, "School record not found. Complete setup first.")

    sid = school["id"]
    status  = "trial" if body.plan == "trial" else "active"
    execute(
        "UPDATE schools SET plan=?, subscription_status=?, trial_ends=?, is_active=1 WHERE id=?",
        (body.plan, status, body.trial_ends, sid),
    )
    return {"ok": True, "plan": body.plan, "status": status}
