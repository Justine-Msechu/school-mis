from typing import Annotated
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from database.db import fetch_one, ROLES
from auth.session import session as _session
from backend.deps import create_token, require_auth, revoke_token, hydrate_session

router = APIRouter(tags=["auth"])


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
    user["role_label"] = role_info.get("label", role)
    user["role_color"]  = role_info.get("color", "#94A3B8")
    user["permissions"] = role_info.get("permissions", [])
    user["full_name"] = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or user.get("username", "")
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
def logout(user: Annotated[dict, require_auth]):
    # We'd need the raw token here; client handles clearing it
    return {"ok": True}


@router.get("/me")
def me(user: Annotated[dict, require_auth]):
    return {
        "id":          user["id"],
        "username":    user["username"],
        "full_name":   user["full_name"],
        "role":        user["role"],
        "role_label":  user["role_label"],
        "role_color":  user["role_color"],
        "permissions": user["permissions"],
    }
