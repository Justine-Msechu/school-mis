from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute, get_config, set_config, ROLES, hash_password

router = APIRouter(tags=["settings"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/config")
def get_all_config(user: Usr):
    rows = fetch_all("SELECT key, value FROM school_config ORDER BY key")
    return {r["key"]: r["value"] for r in rows}


class ConfigBody(BaseModel):
    key:   str
    value: str


@router.post("/config")
def set_config_endpoint(body: ConfigBody, user: Usr):
    set_config(body.key, body.value)
    return {"ok": True}


@router.get("/users")
def list_users(user: Usr):
    actor_role = user.get("role", "")
    rows = fetch_all(
        "SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY full_name"
    )
    result = []
    for r in rows:
        d = dict(r)
        if actor_role == "head_teacher" and d["role"] in _ELEVATED_ROLES:
            continue
        d["role_label"] = ROLES.get(d["role"], {}).get("label", d["role"])
        result.append(d)
    return result


_ELEVATED_ROLES = {"admin", "head_teacher", "academic", "accountant", "welfare_officer"}
_HEAD_TEACHER_ASSIGNABLE = {"class_teacher", "subject_teacher"}


@router.get("/roles")
def get_roles(user: Usr):
    actor_role = user.get("role", "")
    all_roles = [
        {"key": k, "label": v["label"], "color": v.get("color", "#94A3B8")}
        for k, v in ROLES.items()
        if k not in ("student_portal", "parent_portal")
    ]
    if actor_role == "head_teacher":
        return [r for r in all_roles if r["key"] in _HEAD_TEACHER_ASSIGNABLE]
    return all_roles


class UserPayload(BaseModel):
    username:  str
    full_name: str
    role:      str
    password:  str | None = None


@router.post("/users")
def create_user(body: UserPayload, user: Usr):
    actor_role = user.get("role", "")
    if actor_role == "head_teacher" and body.role not in _HEAD_TEACHER_ASSIGNABLE:
        raise HTTPException(403, "Head teachers may only create class_teacher or subject_teacher accounts")
    if actor_role not in ("admin", "head_teacher"):
        raise HTTPException(403, "Only admin or head teacher can create users")
    if not body.password:
        raise HTTPException(400, "Password required for new users")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    # Warn if class/subject teacher has no teacher_id link
    teacher_id = getattr(body, "teacher_id", None)
    pw_hash, salt = hash_password(body.password)
    row_id = execute(
        "INSERT INTO users (username, password_hash, salt, full_name, role, is_active, must_change_pw) VALUES (?,?,?,?,?,1,1)",
        (body.username, pw_hash, salt, body.full_name, body.role),
    )
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "user_create", "users", row_id,
             f"Created user {body.username} with role {body.role}"),
        )
    except Exception:
        pass
    result = dict(fetch_one("SELECT id, username, full_name, role, is_active FROM users WHERE id=?", (row_id,)))
    if body.role in ("class_teacher", "subject_teacher") and not teacher_id:
        result["warning"] = "No teacher record linked. This user will see no class data until linked to a teacher."
    return result


class EditUserPayload(BaseModel):
    full_name: str
    role:      str
    password:  str | None = None


@router.put("/users/{uid}")
def edit_user(uid: int, body: EditUserPayload, user: Usr):
    actor_role = user.get("role", "")
    actor_id = user.get("id")
    target = fetch_one("SELECT role FROM users WHERE id=?", (uid,))
    if not target:
        raise HTTPException(404, "User not found")
    target_role = target["role"]
    if actor_role == "head_teacher":
        if target_role in _ELEVATED_ROLES:
            raise HTTPException(403, "Head teachers cannot edit elevated accounts")
        if body.role not in _HEAD_TEACHER_ASSIGNABLE:
            raise HTTPException(403, "Head teachers may only assign class_teacher or subject_teacher roles")
    elif actor_role != "admin":
        raise HTTPException(403, "Only admin or head teacher can edit users")
    if body.password:
        if len(body.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        pw_hash, salt = hash_password(body.password)
        execute(
            "UPDATE users SET full_name=?, role=?, password_hash=?, salt=? WHERE id=?",
            (body.full_name, body.role, pw_hash, salt, uid),
        )
    else:
        execute("UPDATE users SET full_name=?, role=? WHERE id=?", (body.full_name, body.role, uid))
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "user_edit", "users", uid,
             f"Edited user id={uid} role→{body.role}"),
        )
    except Exception:
        pass
    return dict(fetch_one("SELECT id, username, full_name, role, is_active FROM users WHERE id=?", (uid,)))


@router.post("/users/{uid}/toggle-active")
def toggle_active(uid: int, user: Usr):
    actor_role = user.get("role", "")
    actor_id = user.get("id")
    if uid == actor_id:
        raise HTTPException(400, "Cannot deactivate your own account")
    target = fetch_one("SELECT role FROM users WHERE id=?", (uid,))
    if not target:
        raise HTTPException(404, "User not found")
    if actor_role == "head_teacher" and target["role"] in _ELEVATED_ROLES:
        raise HTTPException(403, "Head teachers cannot deactivate elevated accounts")
    if actor_role not in ("admin", "head_teacher"):
        raise HTTPException(403, "Insufficient permissions")
    execute("UPDATE users SET is_active = 1 - is_active WHERE id=?", (uid,))
    return {"ok": True}


# ── Academic years ──────────────────────────────────────────────────────────

@router.get("/academic-years")
def list_academic_years(user: Usr):
    rows = fetch_all("SELECT * FROM academic_years ORDER BY start_date DESC")
    return [dict(r) for r in rows]


class AcademicYearPayload(BaseModel):
    label:      str
    start_date: str
    end_date:   str
    is_current: bool = False


@router.post("/academic-years")
def create_academic_year(body: AcademicYearPayload, user: Usr):
    if body.is_current:
        execute("UPDATE academic_years SET is_current=0")
    row_id = execute(
        "INSERT INTO academic_years (label, start_date, end_date, is_current) VALUES (?,?,?,?)",
        (body.label, body.start_date, body.end_date, int(body.is_current)),
    )
    return dict(fetch_one("SELECT * FROM academic_years WHERE id=?", (row_id,)))


@router.put("/academic-years/{year_id}/set-current")
def set_current_year(year_id: int, user: Usr):
    execute("UPDATE academic_years SET is_current=0")
    execute("UPDATE academic_years SET is_current=1 WHERE id=?", (year_id,))
    return {"ok": True}


# ── Fee types & structures ──────────────────────────────────────────────────

@router.get("/fee-types")
def list_fee_types(user: Usr):
    rows = fetch_all("SELECT * FROM fee_types ORDER BY name")
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
        """SELECT fs.*, ft.name AS fee_type_name, ay.label AS year_label
           FROM fee_structures fs
           JOIN fee_types ft ON ft.id = fs.fee_type_id
           LEFT JOIN academic_years ay ON ay.id = fs.academic_year_id
           ORDER BY ay.label DESC, ft.name"""
    )
    return [dict(r) for r in rows]


class FeeStructurePayload(BaseModel):
    fee_type_id:      int
    academic_year_id: int
    amount:           float
    due_date:         str = ""
    term:             int | None = None


@router.post("/fee-structures")
def create_fee_structure(body: FeeStructurePayload, user: Usr):
    row_id = execute(
        "INSERT INTO fee_structures (fee_type_id, academic_year_id, amount, due_date, term) VALUES (?,?,?,?,?)",
        (body.fee_type_id, body.academic_year_id, body.amount, body.due_date, body.term),
    )
    row = fetch_one(
        """SELECT fs.*, ft.name AS fee_type_name, ay.label AS year_label
           FROM fee_structures fs
           JOIN fee_types ft ON ft.id=fs.fee_type_id
           LEFT JOIN academic_years ay ON ay.id=fs.academic_year_id
           WHERE fs.id=?""",
        (row_id,),
    )
    return dict(row)
