"""
Schools router — public registration + superadmin platform management.

Public:
  POST /api/schools/register

Superadmin only:
  GET  /api/superadmin/stats
  GET  /api/superadmin/schools
  PUT  /api/superadmin/schools/{id}/subscription
  POST /api/superadmin/schools/{id}/suspend
  POST /api/superadmin/schools/{id}/activate
  POST /api/superadmin/schools/{id}/reset-admin-password
  GET  /api/superadmin/feature-flags
  PUT  /api/superadmin/feature-flags/{plan}/{module}
  GET  /api/superadmin/users
  GET  /api/superadmin/announcements
  POST /api/superadmin/announcements
  DELETE /api/superadmin/announcements/{id}

School-accessible:
  GET  /api/announcements   — active announcements for current school's plan
"""

import asyncio
import secrets
import string
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from backend.core.db import execute, fetch_all, fetch_one
from backend.deps import require_auth

router = APIRouter()

BCRYPT_COST = 12

VALID_PLANS    = ("basic", "standard", "premium", "trial")
VALID_STATUSES = ("active", "trial", "expired", "cancelled", "suspended")


# ── Auth helpers ───────────────────────────────────────────────────────────────

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
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'trial', 50, 0, 'pending', ?, datetime('now'))""",
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
        _seed_demo_data(school_id, user_id)
        return {
            "ok": True,
            "school_name": body.school_name,
            "trial_ends": trial_ends,
            "message": "Registration successful. You can now log in with your admin account.",
        }

    return await asyncio.to_thread(_db)


def _seed_demo_data(school_id: int, admin_user_id: int) -> None:
    """Insert demo data so a newly registered school has something to show."""
    from datetime import date
    try:
        year = date.today().year
        label = f"{year}/{year + 1}"

        # Academic year
        ay_id = execute(
            """INSERT INTO academic_years (label, start_date, end_date, is_current, school_id)
               VALUES (?, ?, ?, 1, ?)""",
            (label, f"{year}-01-01", f"{year}-12-31", school_id),
        )

        # Two teachers
        t1_id = execute(
            "INSERT INTO teachers (first_name, last_name, gender, phone, role, hire_date) VALUES (?,?,?,?,?,?)",
            ("Amina", "Mwangi", "Female", "+255 712 000 001", "Class Teacher", f"{year}-01-15"),
        )
        t2_id = execute(
            "INSERT INTO teachers (first_name, last_name, gender, phone, role, hire_date) VALUES (?,?,?,?,?,?)",
            ("John", "Ochieng", "Male", "+255 712 000 002", "Subject Teacher", f"{year}-01-15"),
        )

        # Teacher user accounts (must_change_pw=1 so they set their own password)
        import bcrypt
        _pw = bcrypt.hashpw(b"teacher123", bcrypt.gensalt(10)).decode()
        execute(
            "INSERT INTO users (username,password_hash,salt,pw_scheme,full_name,role,is_active,must_change_pw,school_id,teacher_id) VALUES (?,?,'','bcrypt',?,?,1,1,?,?)",
            ("amina.mwangi", _pw, "Amina Mwangi", "class_teacher", school_id, t1_id),
        )
        execute(
            "INSERT INTO users (username,password_hash,salt,pw_scheme,full_name,role,is_active,must_change_pw,school_id,teacher_id) VALUES (?,?,'','bcrypt',?,?,1,1,?,?)",
            ("john.ochieng", _pw, "John Ochieng", "subject_teacher", school_id, t2_id),
        )

        # Two classes
        c1_id = execute(
            "INSERT INTO classes (name, grade_level, academic_year_id, teacher_id, capacity) VALUES (?,?,?,?,?)",
            ("Grade 1A", 1, ay_id, t1_id, 40),
        )
        c2_id = execute(
            "INSERT INTO classes (name, grade_level, academic_year_id, teacher_id, capacity) VALUES (?,?,?,?,?)",
            ("Grade 2B", 2, ay_id, t2_id, 40),
        )

        # Four students (2 per class)
        students_data = [
            ("ADM001", "Fatuma",  "Hassan",   "Female", "2016-03-12", c1_id),
            ("ADM002", "Michael", "Kariuki",  "Male",   "2016-07-04", c1_id),
            ("ADM003", "Grace",   "Mutua",    "Female", "2015-11-20", c2_id),
            ("ADM004", "James",   "Ndirangu", "Male",   "2015-05-18", c2_id),
        ]
        s_ids = []
        for adm, fn, ln, gender, dob, cid in students_data:
            sid = execute(
                """INSERT INTO students
                   (admission_no, first_name, last_name, gender, date_of_birth,
                    class_id, enrollment_date, is_active)
                   VALUES (?,?,?,?,?,?,?,1)""",
                (adm, fn, ln, gender, dob, cid, f"{year}-01-15"),
            )
            s_ids.append((sid, cid))

        # Fee type + structures + bills
        ft_id = execute(
            "INSERT INTO fee_types (name, amount, term) VALUES (?,?,?)",
            ("Tuition Fee", 150000, 1),
        )
        for sid, cid in s_ids:
            fs_id = execute(
                "INSERT INTO fee_structures (academic_year_id, class_id, fee_type_id, amount, term) VALUES (?,?,?,?,?)",
                (ay_id, cid, ft_id, 150000, 1),
            )
            execute(
                """INSERT INTO student_bills
                   (student_id, fee_structure_id, academic_year_id, amount_due, amount_paid, balance, term)
                   VALUES (?,?,?,?,0,?,1)""",
                (sid, fs_id, ay_id, 150000, 150000),
            )

        # Sample attendance (last 5 school days)
        from datetime import timedelta
        today = date.today()
        school_days = []
        d = today
        while len(school_days) < 5:
            if d.weekday() < 5:
                school_days.append(d.isoformat())
            d -= timedelta(days=1)
        for sid, cid in s_ids:
            for i, att_date in enumerate(school_days):
                try:
                    execute(
                        "INSERT INTO attendance (student_id, class_id, date, status, recorded_by) VALUES (?,?,?,?,?)",
                        (sid, cid, att_date, "absent" if i == 4 else "present", admin_user_id),
                    )
                except Exception:
                    pass

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Demo seed failed (non-fatal): %s", e)


# ── Superadmin: platform-wide stats ───────────────────────────────────────────

@router.get("/superadmin/stats")
async def platform_stats(_user: dict = Depends(_require_superadmin)):
    def _db():
        def _n(sql, params=()):
            row = fetch_one(sql, params)
            return row["n"] if row else 0

        total         = _n("SELECT COUNT(*) AS n FROM schools")
        active        = _n("SELECT COUNT(*) AS n FROM schools WHERE subscription_status='active'")
        trial         = _n("SELECT COUNT(*) AS n FROM schools WHERE subscription_status='trial'")
        expired       = _n("SELECT COUNT(*) AS n FROM schools WHERE subscription_status IN ('expired','cancelled')")
        suspended     = _n("SELECT COUNT(*) AS n FROM schools WHERE subscription_status='suspended'")
        new_week      = _n("SELECT COUNT(*) AS n FROM schools WHERE created_at >= datetime('now','-7 days')")
        total_users   = _n("SELECT COUNT(*) AS n FROM users WHERE role != 'superadmin' AND is_active=1")
        total_students = _n("SELECT COUNT(*) AS n FROM students WHERE is_active=1")
        total_teachers = _n("SELECT COUNT(*) AS n FROM teachers WHERE is_active=1")
        expiring_soon = _n(
            "SELECT COUNT(*) AS n FROM schools "
            "WHERE subscription_status='trial' "
            "AND trial_ends BETWEEN date('now') AND date('now','+7 days')"
        )

        plan_rows = fetch_all("SELECT plan, COUNT(*) AS n FROM schools GROUP BY plan", ())
        by_plan   = {r["plan"]: r["n"] for r in plan_rows}

        recent = fetch_all(
            """SELECT s.id, s.name, s.plan, s.subscription_status, s.created_at, s.admin_name
               FROM schools s ORDER BY s.created_at DESC LIMIT 5""",
            (),
        )
        expiring_list = fetch_all(
            """SELECT id, name, plan, subscription_status, trial_ends, admin_name
               FROM schools
               WHERE subscription_status='trial'
               AND trial_ends BETWEEN date('now') AND date('now','+7 days')
               ORDER BY trial_ends ASC""",
            (),
        )
        return {
            "total_schools":   total,
            "active":          active,
            "trial":           trial,
            "expired":         expired,
            "suspended":       suspended,
            "new_this_week":   new_week,
            "total_users":     total_users,
            "total_students":  total_students,
            "total_teachers":  total_teachers,
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


# ── Superadmin: list all users across all schools ──────────────────────────────

@router.get("/superadmin/users")
async def list_all_users(_user: dict = Depends(_require_superadmin)):
    """Return all non-platform users across every school for cross-school RBAC management."""
    def _db():
        return fetch_all(
            """SELECT
                   u.id, u.username, u.full_name, u.role, u.is_active,
                   s.id AS school_id, s.name AS school_name
               FROM users u
               LEFT JOIN schools s ON s.id = u.school_id
               WHERE u.role != 'superadmin'
               ORDER BY s.name, u.full_name""",
            (),
        )

    rows = await asyncio.to_thread(_db)
    return [dict(r) for r in rows]


# ── Superadmin: update a school's subscription ─────────────────────────────────

class SubscriptionUpdate(BaseModel):
    plan:       str
    status:     str
    trial_ends: str | None = None

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in VALID_PLANS:
            raise ValueError("Invalid plan.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
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
        return {"ok": True}

    return await asyncio.to_thread(_db)


# ── Superadmin: suspend / activate school ─────────────────────────────────────

@router.post("/superadmin/schools/{school_id}/suspend")
async def suspend_school(school_id: int, _user: dict = Depends(_require_superadmin)):
    def _db():
        school = fetch_one("SELECT id FROM schools WHERE id=?", (school_id,))
        if not school:
            raise HTTPException(404, "School not found.")
        execute(
            "UPDATE schools SET subscription_status='suspended', is_active=0 WHERE id=?",
            (school_id,),
        )
        return {"ok": True}

    return await asyncio.to_thread(_db)


@router.post("/superadmin/schools/{school_id}/activate")
async def activate_school(school_id: int, _user: dict = Depends(_require_superadmin)):
    def _db():
        school = fetch_one("SELECT id, plan FROM schools WHERE id=?", (school_id,))
        if not school:
            raise HTTPException(404, "School not found.")
        execute(
            "UPDATE schools SET subscription_status='active', is_active=1 WHERE id=?",
            (school_id,),
        )
        return {"ok": True}

    return await asyncio.to_thread(_db)


# ── Superadmin: reset school admin password ────────────────────────────────────

@router.post("/superadmin/schools/{school_id}/reset-admin-password")
async def reset_admin_password(school_id: int, _user: dict = Depends(_require_superadmin)):
    def _db():
        admin = fetch_one(
            "SELECT id FROM users WHERE school_id=? AND role='admin' AND is_active=1 LIMIT 1",
            (school_id,),
        )
        if not admin:
            raise HTTPException(404, "No active admin found for this school.")

        alphabet = string.ascii_letters + string.digits
        new_pw = "".join(secrets.choice(alphabet) for _ in range(12))
        pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt(rounds=BCRYPT_COST)).decode()
        execute(
            "UPDATE users SET password_hash=?, salt='', pw_scheme='bcrypt', must_change_pw=1 WHERE id=?",
            (pw_hash, admin["id"]),
        )
        return {"ok": True, "temp_password": new_pw}

    return await asyncio.to_thread(_db)


# ── Superadmin: feature flags ─────────────────────────────────────────────────

@router.get("/superadmin/feature-flags")
async def get_feature_flags(_user: dict = Depends(_require_superadmin)):
    def _db():
        rows = fetch_all(
            "SELECT plan, module, enabled FROM platform_feature_flags ORDER BY plan, module",
            (),
        )
        result: dict[str, dict[str, bool]] = {}
        for r in rows:
            plan = r["plan"]
            if plan not in result:
                result[plan] = {}
            result[plan][r["module"]] = bool(r["enabled"])
        return result

    return await asyncio.to_thread(_db)


class FlagUpdate(BaseModel):
    enabled: bool


@router.put("/superadmin/feature-flags/{plan}/{module}")
async def set_feature_flag(
    plan: str,
    module: str,
    body: FlagUpdate,
    _user: dict = Depends(_require_superadmin),
):
    def _db():
        if plan not in VALID_PLANS:
            raise HTTPException(400, "Invalid plan.")
        execute(
            """INSERT INTO platform_feature_flags (plan, module, enabled)
               VALUES (?, ?, ?)
               ON CONFLICT(plan, module) DO UPDATE SET enabled=excluded.enabled""",
            (plan, module, 1 if body.enabled else 0),
        )
        return {"ok": True}

    return await asyncio.to_thread(_db)


# ── Superadmin: announcements ─────────────────────────────────────────────────

class AnnouncementPayload(BaseModel):
    title:       str
    body:        str
    priority:    str = "normal"
    target_plan: str = "all"
    expires_at:  str | None = None

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v: str) -> str:
        if v not in ("normal", "warning", "critical"):
            raise ValueError("Invalid priority.")
        return v

    @field_validator("target_plan")
    @classmethod
    def valid_target(cls, v: str) -> str:
        if v not in ("all", *VALID_PLANS):
            raise ValueError("Invalid target plan.")
        return v


@router.get("/superadmin/announcements")
async def list_announcements(_user: dict = Depends(_require_superadmin)):
    def _db():
        rows = fetch_all(
            "SELECT * FROM platform_announcements ORDER BY created_at DESC",
            (),
        )
        return [dict(r) for r in rows]

    return await asyncio.to_thread(_db)


@router.post("/superadmin/announcements")
async def create_announcement(
    body: AnnouncementPayload,
    _user: dict = Depends(_require_superadmin),
):
    def _db():
        ann_id = execute(
            """INSERT INTO platform_announcements
               (title, body, priority, target_plan, expires_at, is_active)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (body.title, body.body, body.priority, body.target_plan, body.expires_at),
        )
        return {"ok": True, "id": ann_id}

    return await asyncio.to_thread(_db)


@router.delete("/superadmin/announcements/{ann_id}")
async def delete_announcement(ann_id: int, _user: dict = Depends(_require_superadmin)):
    def _db():
        row = fetch_one("SELECT id FROM platform_announcements WHERE id=?", (ann_id,))
        if not row:
            raise HTTPException(404, "Announcement not found.")
        execute("DELETE FROM platform_announcements WHERE id=?", (ann_id,))
        return {"ok": True}

    return await asyncio.to_thread(_db)


# ── School-accessible: request plan upgrade ───────────────────────────────────

class UpgradeRequestPayload(BaseModel):
    plan_name: str
    interval:  str = "monthly"

    @field_validator("plan_name")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in VALID_PLANS:
            raise ValueError("Invalid plan.")
        return v


@router.post("/subscriptions/request-upgrade")
async def request_plan_upgrade(body: UpgradeRequestPayload, user: dict = Depends(require_auth)):
    def _db():
        school_id = user.get("school_id")
        if not school_id:
            raise HTTPException(400, "No school associated with this account.")
        if user.get("role") != "admin":
            raise HTTPException(403, "Only school administrators can request plan upgrades.")

        school = fetch_one("SELECT name FROM schools WHERE id=?", (school_id,))
        school_name = school["name"] if school else f"School #{school_id}"

        # Create a platform announcement so the superadmin sees it
        tbl = fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='platform_announcements'", ())
        if tbl:
            execute(
                """INSERT INTO platform_announcements
                   (title, body, priority, target_plan, is_active)
                   VALUES (?, ?, 'warning', 'all', 1)""",
                (
                    f"Upgrade Request: {school_name}",
                    f"{school_name} has requested a plan upgrade to {body.plan_name.title()} "
                    f"({body.interval}). They have confirmed sending payment. "
                    f"Please verify and activate via Platform Admin → Manage Schools.",
                ),
            )
        return {"ok": True, "message": "Your upgrade request has been sent to the platform administrator."}

    return await asyncio.to_thread(_db)


# ── School-accessible: active announcements ───────────────────────────────────

@router.get("/announcements")
async def get_active_announcements(user: dict = Depends(require_auth)):
    def _db():
        school = fetch_one("SELECT plan FROM schools WHERE id=?", (user.get("school_id"),)) if user.get("school_id") else None
        plan = school["plan"] if school else None

        rows = fetch_all(
            """SELECT id, title, body, priority, target_plan, created_at, expires_at
               FROM platform_announcements
               WHERE is_active=1
               AND (expires_at IS NULL OR expires_at >= date('now'))
               ORDER BY created_at DESC""",
            (),
        )
        result = []
        for r in rows:
            tp = r["target_plan"]
            if tp == "all" or tp == plan:
                result.append(dict(r))
        return result

    return await asyncio.to_thread(_db)
