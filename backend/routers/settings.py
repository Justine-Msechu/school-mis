from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.core.db import execute, fetch_all, fetch_one
from backend.deps import require_auth
from backend.core.authz import authorize
from database.db import ROLES, hash_password, sync_user_role

router = APIRouter(tags=["settings"])
Usr = Annotated[dict, Depends(require_auth)]

_TEACHER_ROLES    = {"class_teacher", "subject_teacher"}
_ADMIN_ONLY_ROLES = {"admin"}


# ── School config ─────────────────────────────────────────────────────────────

@router.get("/config")
def get_all_config(user: Usr):
    school_id = user.get("school_id")
    rows = fetch_all(
        "SELECT key, value FROM school_config WHERE school_id=? ORDER BY key",
        (school_id,),
    )
    return {r["key"]: r["value"] for r in rows}


class ConfigBody(BaseModel):
    key:   str
    value: str


@router.post("/config")
def set_config_endpoint(body: ConfigBody, user: Usr):
    school_id = user.get("school_id")
    execute(
        "INSERT INTO school_config(key, value, school_id) VALUES(?,?,?) "
        "ON CONFLICT(key, school_id) DO UPDATE SET value=excluded.value",
        (body.key, body.value, school_id),
    )
    return {"ok": True}


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(user: Usr):
    can_manage_all      = authorize(user, "settings.users.manage")
    can_manage_teachers = authorize(user, "settings.teachers.manage")
    if not can_manage_all and not can_manage_teachers:
        raise HTTPException(403, "Insufficient permissions to list users")

    school_id = user.get("school_id")
    rows = fetch_all(
        "SELECT id, username, full_name, role, is_active, created_at "
        "FROM users WHERE school_id=? ORDER BY full_name",
        (school_id,),
    )
    result = []
    for r in rows:
        d = dict(r)
        if not can_manage_all and d["role"] not in _TEACHER_ROLES:
            continue
        d["role_label"] = ROLES.get(d["role"], {}).get("label", d["role"])
        result.append(d)
    return result


@router.get("/roles")
def get_roles(user: Usr):
    can_manage_all      = authorize(user, "settings.users.manage")
    can_manage_teachers = authorize(user, "settings.teachers.manage")
    rows = fetch_all(
        "SELECT name AS key, label, color FROM roles "
        "WHERE name NOT IN ('student_portal','parent_portal','superadmin') "
        "ORDER BY label",
        (),
    )
    all_roles = [dict(r) for r in rows]
    if can_manage_all:
        return all_roles
    if can_manage_teachers:
        return [r for r in all_roles if r["key"] in _TEACHER_ROLES]
    return []


class UserPayload(BaseModel):
    username:   str
    full_name:  str
    role:       str
    password:   str | None = None
    teacher_id: int | None = None


@router.post("/users")
def create_user(body: UserPayload, user: Usr):
    can_manage_all      = authorize(user, "settings.users.manage")
    can_manage_teachers = authorize(user, "settings.teachers.manage")
    if not can_manage_all and not can_manage_teachers:
        raise HTTPException(403, "Insufficient permissions to create users")
    if not can_manage_all and body.role not in _TEACHER_ROLES:
        raise HTTPException(403, "You may only create class_teacher or subject_teacher accounts")
    if body.role in _ADMIN_ONLY_ROLES and not authorize(user, "*"):
        raise HTTPException(403, "Only administrators may create admin accounts")

    if not body.password:
        raise HTTPException(400, "Password required for new users")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    school_id = user.get("school_id")
    existing = fetch_one(
        "SELECT id FROM users WHERE username=? AND school_id=?",
        (body.username, school_id),
    )
    if existing:
        raise HTTPException(400, f"Username '{body.username}' is already taken")

    pw_hash, salt = hash_password(body.password)
    row_id = execute(
        "INSERT INTO users "
        "(username, password_hash, salt, full_name, role, teacher_id, is_active, must_change_pw, school_id) "
        "VALUES (?,?,?,?,?,?,1,1,?)",
        (body.username, pw_hash, salt, body.full_name, body.role, body.teacher_id, school_id),
    )
    try:
        sync_user_role(row_id, body.role)
    except Exception:
        pass
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "user_create", "users", row_id,
             f"Created user {body.username} with role {body.role}"),
        )
    except Exception:
        pass
    result = dict(fetch_one("SELECT id, username, full_name, role, is_active FROM users WHERE id=?", (row_id,)))
    if body.role in _TEACHER_ROLES and not body.teacher_id:
        result["warning"] = "No teacher record linked. Link a teacher so this user can access class data."
    return result


class EditUserPayload(BaseModel):
    full_name:  str
    role:       str
    password:   str | None = None
    teacher_id: int | None = None


@router.put("/users/{uid}")
def edit_user(uid: int, body: EditUserPayload, user: Usr):
    can_manage_all      = authorize(user, "settings.users.manage")
    can_manage_teachers = authorize(user, "settings.teachers.manage")
    if not can_manage_all and not can_manage_teachers:
        raise HTTPException(403, "Insufficient permissions to edit users")

    school_id = user.get("school_id")
    target = fetch_one("SELECT role FROM users WHERE id=? AND school_id=?", (uid, school_id))
    if not target:
        raise HTTPException(404, "User not found")

    if not can_manage_all and target["role"] not in _TEACHER_ROLES:
        raise HTTPException(403, "You can only edit teacher accounts")
    if not can_manage_all and body.role not in _TEACHER_ROLES:
        raise HTTPException(403, "You may only assign class_teacher or subject_teacher roles")
    if body.role in _ADMIN_ONLY_ROLES and not authorize(user, "*"):
        raise HTTPException(403, "Only administrators may assign the admin role")

    if body.password:
        if len(body.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        pw_hash, salt = hash_password(body.password)
        execute(
            "UPDATE users SET full_name=?, role=?, teacher_id=?, password_hash=?, salt=? WHERE id=?",
            (body.full_name, body.role, body.teacher_id, pw_hash, salt, uid),
        )
    else:
        execute(
            "UPDATE users SET full_name=?, role=?, teacher_id=? WHERE id=?",
            (body.full_name, body.role, body.teacher_id, uid),
        )
    try:
        execute("DELETE FROM user_roles WHERE user_id=?", (uid,))
        sync_user_role(uid, body.role)
    except Exception:
        pass
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "user_edit", "users", uid, f"Edited user id={uid} role→{body.role}"),
        )
    except Exception:
        pass
    return dict(fetch_one("SELECT id, username, full_name, role, is_active FROM users WHERE id=?", (uid,)))


@router.post("/users/{uid}/toggle-active")
def toggle_active(uid: int, user: Usr):
    if uid == user.get("id"):
        raise HTTPException(400, "Cannot deactivate your own account")

    can_manage_all      = authorize(user, "settings.users.manage")
    can_manage_teachers = authorize(user, "settings.teachers.manage")
    if not can_manage_all and not can_manage_teachers:
        raise HTTPException(403, "Insufficient permissions")

    school_id = user.get("school_id")
    target = fetch_one("SELECT role FROM users WHERE id=? AND school_id=?", (uid, school_id))
    if not target:
        raise HTTPException(404, "User not found")
    if not can_manage_all and target["role"] not in _TEACHER_ROLES:
        raise HTTPException(403, "You can only toggle teacher accounts")

    execute("UPDATE users SET is_active = 1 - is_active WHERE id=?", (uid,))
    return {"ok": True}


# ── Academic years ────────────────────────────────────────────────────────────

@router.get("/academic-years")
def list_academic_years(user: Usr):
    school_id = user.get("school_id")
    rows = fetch_all(
        "SELECT * FROM academic_years WHERE school_id=? ORDER BY start_date DESC",
        (school_id,),
    )
    return [dict(r) for r in rows]


class AcademicYearPayload(BaseModel):
    label:      str
    start_date: str
    end_date:   str
    is_current: bool = False


@router.post("/academic-years")
def create_academic_year(body: AcademicYearPayload, user: Usr):
    school_id = user.get("school_id")
    if body.is_current:
        execute("UPDATE academic_years SET is_current=0 WHERE school_id=?", (school_id,))
    row_id = execute(
        "INSERT INTO academic_years (label, start_date, end_date, is_current, school_id) VALUES (?,?,?,?,?)",
        (body.label, body.start_date, body.end_date, int(body.is_current), school_id),
    )
    return dict(fetch_one("SELECT * FROM academic_years WHERE id=?", (row_id,)))


@router.put("/academic-years/{year_id}/set-current")
def set_current_year(year_id: int, user: Usr):
    school_id = user.get("school_id")
    execute("UPDATE academic_years SET is_current=0 WHERE school_id=?", (school_id,))
    execute("UPDATE academic_years SET is_current=1 WHERE id=? AND school_id=?", (year_id, school_id))
    return {"ok": True}


# ── Fee types & structures ────────────────────────────────────────────────────

@router.get("/fee-types")
def list_fee_types(user: Usr):
    rows = fetch_all("SELECT * FROM fee_types ORDER BY name", ())
    return [dict(r) for r in rows]


class FeeTypePayload(BaseModel):
    name:        str
    description: str = ""


@router.post("/fee-types")
def create_fee_type(body: FeeTypePayload, user: Usr):
    row_id = execute(
        "INSERT INTO fee_types (name, description) VALUES (?,?)",
        (body.name, body.description),
    )
    return dict(fetch_one("SELECT * FROM fee_types WHERE id=?", (row_id,)))


@router.get("/fee-structures")
def list_fee_structures(user: Usr):
    rows = fetch_all(
        """SELECT fs.*, ft.name AS fee_type_name, ay.label AS year_label,
                  c.name AS class_name,
                  s.first_name || ' ' || s.last_name AS student_name,
                  s.admission_no AS student_admission_no,
                  RTRIM((SELECT c2.name FROM classes c2
                         WHERE c2.grade_level = fs.grade_level
                         ORDER BY c2.name LIMIT 1),
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ') AS grade_name
           FROM fee_structures fs
           JOIN fee_types ft ON ft.id = fs.fee_type_id
           LEFT JOIN academic_years ay ON ay.id = fs.academic_year_id
           LEFT JOIN classes c ON c.id = fs.class_id
           LEFT JOIN students s ON s.id = fs.student_id
           WHERE fs.deleted_at IS NULL
           ORDER BY ay.label DESC, fs.term NULLS LAST, ft.name""",
        (),
    )
    return [dict(r) for r in rows]


class FeeStructurePayload(BaseModel):
    fee_type_id:      int
    academic_year_id: int
    amount:           float
    due_date:         str = ""
    term:             int | None = None
    grade_level:      int | None = None
    class_id:         int | None = None
    student_id:       int | None = None
    student_type:     str | None = None


@router.post("/fee-structures")
def create_fee_structure(body: FeeStructurePayload, user: Usr):
    row_id = execute(
        """INSERT INTO fee_structures
           (fee_type_id, academic_year_id, amount, due_date, term,
            grade_level, class_id, student_id, student_type)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (body.fee_type_id, body.academic_year_id, body.amount, body.due_date,
         body.term, body.grade_level, body.class_id, body.student_id, body.student_type or None),
    )
    row = fetch_one(
        """SELECT fs.*, ft.name AS fee_type_name, ay.label AS year_label,
                  c.name AS class_name,
                  s.first_name || ' ' || s.last_name AS student_name,
                  s.admission_no AS student_admission_no,
                  RTRIM((SELECT c2.name FROM classes c2
                         WHERE c2.grade_level = fs.grade_level
                         ORDER BY c2.name LIMIT 1),
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ') AS grade_name
           FROM fee_structures fs
           JOIN fee_types ft ON ft.id=fs.fee_type_id
           LEFT JOIN academic_years ay ON ay.id=fs.academic_year_id
           LEFT JOIN classes c ON c.id=fs.class_id
           LEFT JOIN students s ON s.id=fs.student_id
           WHERE fs.id=?""",
        (row_id,),
    )
    return dict(row)
