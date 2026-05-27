"""
Schools router — public registration + superadmin management.

Public:
  POST /api/schools/register   — self-service school + admin creation

Superadmin only:
  GET  /api/superadmin/schools                    — list all schools
  PUT  /api/superadmin/schools/{id}/subscription  — activate / change plan
"""

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
    # School info
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
    # Admin account
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
def register_school(body: RegisterPayload):
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

    return {
        "ok": True,
        "school_name": body.school_name,
        "trial_ends": trial_ends,
        "message": "Registration successful. You can now log in with your admin account.",
    }


# ── Superadmin: list all schools ───────────────────────────────────────────────

@router.get("/superadmin/schools")
def list_schools(_user: dict = Depends(_require_superadmin)):
    rows = fetch_all(
        """SELECT
               s.id, s.name, s.email, s.contact_phone, s.admin_name,
               s.plan, s.subscription_status, s.trial_ends,
               s.is_active, s.created_at,
               (SELECT COUNT(*) FROM users u WHERE u.school_id = s.id AND u.is_active = 1) AS user_count
           FROM schools s
           ORDER BY s.created_at DESC""",
        (),
    )
    return [dict(r) for r in rows]


# ── Superadmin: update a school's subscription ─────────────────────────────────

class SubscriptionUpdate(BaseModel):
    plan:   str   # basic | standard | premium | trial
    status: str   # active | trial | expired | cancelled
    trial_ends: str | None = None   # YYYY-MM-DD

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
def update_school_subscription(
    school_id: int,
    body: SubscriptionUpdate,
    _user: dict = Depends(_require_superadmin),
):
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

    # Mirror to subscriptions_v2 if that table exists
    sv2 = fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions_v2'", ())
    if sv2:
        existing = fetch_one(
            "SELECT id FROM subscriptions_v2 WHERE organization_id=? AND status NOT IN ('cancelled','expired') ORDER BY created_at DESC LIMIT 1",
            (school_id,),
        )
        if existing:
            execute(
                """UPDATE subscriptions_v2
                   SET status=?, cancel_at_period_end=0
                   WHERE id=?""",
                (body.status, existing["id"]),
            )

    return {"ok": True, "school_id": school_id, "plan": body.plan, "status": body.status}
