from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from database.db import fetch_one, ROLES
from auth.session import session as _session
from backend.deps import create_token, require_auth, revoke_token, hydrate_session

router = APIRouter(tags=["auth"])
Usr = Annotated[dict, Depends(require_auth)]


class LoginRequest(BaseModel):
    username: str
    password: str


def _verify(stored_hash: str, stored_salt: str, password: str) -> bool:
    import hashlib
    h = hashlib.sha256((stored_salt + password).encode()).hexdigest()
    return h == stored_hash


def _user_to_dict(row) -> dict:
    user = dict(row)
    role = user.get("role", "")
    role_info = ROLES.get(role, {})
    # ROLES values are tuples or dicts depending on db.py version — handle both
    if isinstance(role_info, dict):
        user["role_label"] = role_info.get("label", role)
        user["role_color"]  = role_info.get("color", "#94A3B8")
        user["permissions"] = role_info.get("permissions", [])
    else:
        user["role_label"] = str(role_info)
        user["role_color"]  = "#94A3B8"
        user["permissions"] = []
    # full_name is a direct column; fall back to username if empty
    if not user.get("full_name"):
        user["full_name"] = user.get("username", "")
    return user


@router.post("/login")
def login(body: LoginRequest):
    row = fetch_one(
        "SELECT * FROM users WHERE username=? AND is_active=1",
        (body.username.strip(),)
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    user = dict(row)
    if not _verify(user.get("password_hash", ""), user.get("salt", ""), body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    user_dict = _user_to_dict(row)
    token = create_token(user_dict)

    return {
        "token": token,
        "user": {
            "id":          user_dict["id"],
            "username":    user_dict["username"],
            "full_name":   user_dict["full_name"],
            "role":        user_dict["role"],
            "role_label":  user_dict["role_label"],
            "role_color":  user_dict["role_color"],
            "permissions": user_dict["permissions"],
        },
    }


@router.post("/logout")
def logout(user: Usr):
    return {"ok": True}


@router.get("/me")
def me(user: Usr):
    return {
        "id":          user["id"],
        "username":    user["username"],
        "full_name":   user["full_name"],
        "role":        user["role"],
        "role_label":  user["role_label"],
        "role_color":  user["role_color"],
        "permissions": user["permissions"],
    }
