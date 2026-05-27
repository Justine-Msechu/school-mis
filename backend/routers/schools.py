"""
Schools router — public registration + superadmin platform management.

Public:
  POST /api/schools/register   — self-service school + admin creation

Superadmin only:
  GET  /api/superadmin/stats                      — platform-wide stats
  GET  /api/superadmin/schools                    — list all schools
  PUT  /api/superadmin/schools/{id}/subscription  — change plan / status
"""

import asyncio
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from backend.core.db import execute, fetch_all, fetch_one
from backend.deps import require_auth

router = APIRouter()

BCRYPT_COST = 12


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_superadmin(user: dict = Depends(require_auth)) -> dict:
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin access required.")
    return user


# ── Public: school self-registration ──────────────────────────────────────────

class RegisterPayload(BaseModel):
    school_name:          str
    school_type:          str = "primary"
    school_ownership:     str = "private"
    registration_number:  str = ""
    school_email:         str = ""
    contact_phone:        str = ""
    school_address:       str = ""
    school_location:      str = ""
    country:              str = "Tanzania"
    website:              str = ""
    login_header_message: str = ""
    admin_fullname:       str
    admin_username:       str
    admin_password:       str

    @field_validator("school_name", "admin_fullname", "admin_username")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field is required.")
        return v.strip()

    @field_validator("admin_password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


@router.post("/schools/register")
async def register_school(body: RegisterPayload):
    def _db():
        if fetch_one("SELECT id FROM schools WHERE name=?", (body.school_name,)):
            raise HTTPException(400, "A school with that name is already registered.")
        if fetch_one("SELECT id FROM users WHERE username=?", (body.admin_username,)):
            raise HTTPException(400, "That username is already taken.")

        trial_ends = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        school_id = execute(
            """INSERT INTO schools
               (name, email, contact_phone, school_type, school_ownership,
                registration_number, school_address, school_location, country,
                website, login_header_message, admin_name,
                plan, max_users, is_active, subscription_status, trial_ends, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'trial', 50, 1, 'trial', ?, datetime('now'))""",
            (
                body.school_name, body.school_email, body.contact_phone,
                body.school_type, body.school_ownership,
                body.registration_number, body.school_address, body.school_location,
                body.country, body.website, body.login_header_message,
                body.admin_fullname, trial_ends,
            ),
        )
        config_cols = {r["name"] for r in fetch_all("PRAGMA table_info(school_config)", ())}
        if "school_id" in config_cols:
            for key, value in [
                ("school_name",  body.school_name),
                ("school_email", body.school_email),
                ("currency",     "TZS"),
                ("theme",        "light"),
            ]:
                execute(
                    "INSERT OR IGNORE INTO school_config (key, value, school_id) VALUES (?, ?, ?)",
                    (key, value, school_id),
                )

        pw_hash = bcrypt.hashpw(body.admin_password.encode(), bcrypt.gensalt(rounds=BCRYPT_COST)).decode()
        user_id = execute(
            """INSERT INTO users
               (username, password_hash, salt, pw_scheme, full_name, role,
                is_active, must_change_pw, school_id)
               VALUES (?, ?, '', 'bcrypt', ?, 'admin', 1, 0, ?)""",
            (body.admin_username, pw_hash, body.admin_fullname, school_id),
        )
        admin_role = fetch_one("SELECT id FROM roles WHERE name='admin'", ())
        if admin_role:
            execute(
                "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, admin_role["id"]),
            )
        return {"ok": True, "school_name": body.school_name, "trial_ends": trial_ends,
                "message": "Registration successful. You can now log in with your admin account."}

    return await asyncio.to_thread(_db)


# ── Superadmin: platform-wide stats ───────────────────────────────────────────

@router.get("/superadmin/stats")
async def platform_stats(_user: dict = Depends(_require_superadmin)):
    def _db():
        total    = (fetch_one("SELECT COUNT(*) AS n FROM schools", ()) or {}).get("n", 0)
        active   = (fetch_one("SELECT COUNT(*) AS n FROM schools WHERE subscription_status='active'", ()) or {}).get("n", 0)
        trial    = (fetch_one("SELECT COUNT(*) AS n FROM schools WHERE subscription_status='trial'", ()) or {}).get("n", 0)
        expired  = (fetch_one("SELECT COUNT(*) AS n FROM schools WHERE subscription_status IN ('expired','cancelled')", ()) or {}).get("n", 0)
        new_week = (fetch_one("SELECT COUNT(*) AS n FROM schools WHERE created_at >= datetime('now','-7 days')", ()) or {}).get("n", 0)
        total_users = (fetch_one("SELECT COUNT(*) AS n FROM users WHERE role != 'superadmin' AND is_active=1", ()) or {}).get("n", 0)
        expiring_soon = (fetch_one(
            "SELECT COUNT(*) AS n FROM schools "
            "WHERE subscription_status='trial' "
            "AND trial_ends BETWEEN date('now') AND date('now','+7 days')", ()
        ) or {}).get("n", 0)

        plan_rows = fetch_all("SELECT plan, COUNT(*) AS n FROM schools GROUP BY plan", ())
        by_plan   = {r["plan"]: r["n"] for r in plan_rows}

        recent = fetch_all(
            """SELECT s.id, s.name, s.plan, s.subscription_status, s.created_at, s.admin_name
               FROM schools s ORDER BY s.created_at DESC LIMIT 5""", (),
        )
        expiring_list = fetch_all(
            """SELECT id, name, plan, subscription_status, trial_ends, admin_name
               FROM schools
               WHERE subscription_status='trial'
               AND trial_ends BETWEEN date('now') AND date('now','+7 days')
               ORDER BY trial_ends ASC""", (),
        )
        return {
            "total_schools":   total,
            "active":          active,
            "trial":           trial,
            "expired":         expired,
            "new_this_week":   new_week,
            "total_users":     total_users,
            "expiring_soon":   expiring_soon,
            "by_plan":         by_plan,
            "recent_schools":  [dict(r) for r in recent],
            "expiring_list":   [dict(r) for r in expiring_list],
        }

    return await asyncio.to_thread(_db)


# ── Superadmin: list all schools ───────────────────────────────────────────────

@router.get("/superadmin/schools")
async def list_schools(_user: dict = Depends(_require_superadmin)):
    def _db():
        return fetch_all(
            """SELECT
                   s.id, s.name, s.email, s.contact_phone, s.admin_name,
                   s.plan, s.subscription_status, s.trial_ends,
                   s.is_active, s.created_at,
                   (SELECT COUNT(*) FROM users u WHERE u.school_id = s.id AND u.is_active = 1) AS user_count
               FROM schools s
               ORDER BY s.created_at DESC""",
            (),
        )

    rows = await asyncio.to_thread(_db)
    return [dict(r) for r in rows]


# ── Superadmin: update a school's subscription ─────────────────────────────────

class SubscriptionUpdate(BaseModel):
    plan:   str
    status: str
    trial_ends: str | None = None

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in ("basic", "standard", "premium", "trial"):
            raise ValueError("Invalid plan.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ("active", "trial", "expired", "cancelled"):
            raise ValueError("Invalid status.")
        return v


@router.put("/superadmin/schools/{school_id}/subscription")
async def update_school_subscription(
    school_id: int,
    body: SubscriptionUpdate,
    _user: dict = Depends(_require_superadmin),
):
    def _db():
        school = fetch_one("SELECT id FROM schools WHERE id=?", (school_id,))
        if not school:
            raise HTTPException(404, "School not found.")

        is_active = 1 if body.status in ("active", "trial") else 0
        execute(
            """UPDATE schools
               SET plan=?, subscription_status=?, is_active=?,
                   trial_ends=COALESCE(?, trial_ends)
               WHERE id=?""",
            (body.plan, body.status, is_active, body.trial_ends, school_id),
        )
        sv2 = fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions_v2'", ())
        if sv2:
            existing = fetch_one(
                "SELECT id FROM subscriptions_v2 WHERE organization_id=? "
                "AND status NOT IN ('cancelled','expired') ORDER BY created_at DESC LIMIT 1",
                (school_id,),
            )
            if existing:
                execute(
                    "UPDATE subscriptions_v2 SET status=?, cancel_at_period_end=0 WHERE id=?",
                    (body.status, existing["id"]),
                )
        return {"ok": True, "school_id": school_id, "plan": body.plan, "status": body.status}

    return await asyncio.to_thread(_db)
