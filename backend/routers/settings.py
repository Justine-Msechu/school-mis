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
    rows = fetch_all(
        "SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY full_name"
    )
    result = []
    for r in rows:
        d = dict(r)
        d["role_label"] = ROLES.get(d["role"], {}).get("label", d["role"])
        result.append(d)
    return result


@router.get("/roles")
def get_roles(user: Usr):
    return [
        {"key": k, "label": v["label"], "color": v.get("color", "#94A3B8")}
        for k, v in ROLES.items()
        if k not in ("student_portal", "parent_portal")
    ]


class UserPayload(BaseModel):
    username:  str
    full_name: str
    role:      str
    password:  str | None = None


@router.post("/users")
def create_user(body: UserPayload, user: Usr):
    if not body.password:
        raise HTTPException(400, "Password required for new users")
    pw_hash, salt = hash_password(body.password)
    row_id = execute(
        "INSERT INTO users (username, password_hash, salt, full_name, role, is_active, must_change_pw) VALUES (?,?,?,?,?,1,1)",
        (body.username, pw_hash, salt, body.full_name, body.role),
    )
    return dict(fetch_one("SELECT id, username, full_name, role, is_active FROM users WHERE id=?", (row_id,)))


class EditUserPayload(BaseModel):
    full_name: str
    role:      str
    password:  str | None = None


@router.put("/users/{uid}")
def edit_user(uid: int, body: EditUserPayload, user: Usr):
    if body.password:
        pw_hash, salt = hash_password(body.password)
        execute(
            "UPDATE users SET full_name=?, role=?, password_hash=?, salt=? WHERE id=?",
            (body.full_name, body.role, pw_hash, salt, uid),
        )
    else:
        execute("UPDATE users SET full_name=?, role=? WHERE id=?", (body.full_name, body.role, uid))
    return dict(fetch_one("SELECT id, username, full_name, role, is_active FROM users WHERE id=?", (uid,)))


@router.post("/users/{uid}/toggle-active")
def toggle_active(uid: int, user: Usr):
    execute("UPDATE users SET is_active = 1 - is_active WHERE id=?", (uid,))
    return {"ok": True}
