"""
Setup wizard — public endpoints (no auth required).

These are only usable when the system has not been initialized yet
(no admin user exists). Once setup is complete they become no-ops.
"""

from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.db import execute, fetch_one

router = APIRouter(tags=["setup"])

BCRYPT_COST = 12


def _is_initialized() -> bool:
    """Return True if an admin user already exists."""
    row = fetch_one("SELECT id FROM users WHERE role='admin' AND is_active=1 LIMIT 1")
    return row is not None


@router.get("/status")
def setup_status():
    """Check whether first-time setup is still needed."""
    initialized = _is_initialized()
    school = fetch_one("SELECT value FROM school_config WHERE key='school_name'")
    return {
        "needs_setup": not initialized,
        "school_name": school["value"] if school else "",
    }


class SetupPayload(BaseModel):
    school_name:    str
    school_address: str = ""
    school_phone:   str = ""
    school_email:   str = ""
    school_type:    str = "primary"     # primary | secondary | mixed
    admin_username: str
    admin_fullname: str
    admin_password: str


@router.post("/initialize")
def initialize(body: SetupPayload):
    """
    Run first-time setup.
    Creates the school record, seeds school_config, and creates the first admin user.
    Rejected if an admin already exists.
    """
    if _is_initialized():
        raise HTTPException(400, "System is already initialized. Log in with your admin account.")

    if len(body.admin_password) < 8:
        raise HTTPException(400, "Admin password must be at least 8 characters.")
    if not body.school_name.strip():
        raise HTTPException(400, "School name is required.")
    if not body.admin_username.strip():
        raise HTTPException(400, "Admin username is required.")

    # Check username not already taken
    if fetch_one("SELECT id FROM users WHERE username=?", (body.admin_username.strip(),)):
        raise HTTPException(400, "That username is already taken.")

    # 1. Create the school record
    trial_ends = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    school_id = execute(
        """INSERT INTO schools (name, plan, max_users, is_active, subscription_status, trial_ends)
           VALUES (?, 'trial', 50, 1, 'trial', ?)""",
        (body.school_name.strip(), trial_ends),
    )

    # 2. Seed school_config
    config_rows = [
        ("school_name",    body.school_name.strip()),
        ("school_address", body.school_address.strip()),
        ("school_phone",   body.school_phone.strip()),
        ("school_email",   body.school_email.strip()),
        ("school_type",    body.school_type),
        ("currency",       "TZS"),
        ("theme",          "light"),
    ]
    for key, value in config_rows:
        execute(
            "INSERT OR REPLACE INTO school_config (key, value) VALUES (?, ?)",
            (key, value),
        )

    # 3. Create admin user (bcrypt from day one)
    pw_hash = bcrypt.hashpw(body.admin_password.encode(), bcrypt.gensalt(rounds=BCRYPT_COST)).decode()
    execute(
        """INSERT INTO users (username, password_hash, salt, pw_scheme, full_name, role, is_active, must_change_pw, school_id)
           VALUES (?, ?, '', 'bcrypt', ?, 'admin', 1, 0, ?)""",
        (body.admin_username.strip(), pw_hash, body.admin_fullname.strip() or body.admin_username.strip(), school_id),
    )

    return {
        "ok": True,
        "school_name": body.school_name.strip(),
        "trial_ends": trial_ends,
        "message": "Setup complete. Please log in with your admin account.",
    }
