from typing import Annotated
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from threading import Lock
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from database.db import fetch_one, execute, ROLES
from auth.session import session as _session
from backend.deps import create_token, require_auth, revoke_token, hydrate_session
from backend.core.authz import compute_effective_permissions

router = APIRouter(tags=["auth"])
Usr = Annotated[dict, Depends(require_auth)]

# ── Rate limiting (in-memory, per username) ────────────────────────────────────
_MAX_ATTEMPTS  = 5          # failures before lockout
_WINDOW_SECS   = 300        # 5-minute window
_LOCKOUT_SECS  = 900        # 15-minute lockout after exceeding limit
_attempts: dict[str, list]  = defaultdict(list)
_lock = Lock()


def _check_rate_limit(identifier: str):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=_WINDOW_SECS)
    with _lock:
        _attempts[identifier] = [t for t in _attempts[identifier] if t > cutoff]
        if len(_attempts[identifier]) >= _MAX_ATTEMPTS:
            oldest = _attempts[identifier][0]
            wait = int((oldest + timedelta(seconds=_LOCKOUT_SECS) - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {max(wait,1)//60+1} minutes.",
            )


def _record_failure(identifier: str):
    with _lock:
        _attempts[identifier].append(datetime.now(timezone.utc))


def _clear_attempts(identifier: str):
    with _lock:
        _attempts.pop(identifier, None)


# ── Helpers ────────────────────────────────────────────────────────────────────

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
    user["role_label"] = role_info.get("label", role) if isinstance(role_info, dict) else str(role_info)
    user["role_color"]  = role_info.get("color", "#94A3B8") if isinstance(role_info, dict) else "#94A3B8"
    # Compute from DB (user_roles → role_permissions → permissions + overrides)
    user["permissions"] = compute_effective_permissions(user["id"])
    if not user.get("full_name"):
        user["full_name"] = user.get("username", "")
    return user


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/login")
def login(body: LoginRequest, request: Request):
    identifier = body.username.strip().lower()
    _check_rate_limit(identifier)

    row = fetch_one(
        "SELECT * FROM users WHERE username=? AND is_active=1",
        (body.username.strip(),),
    )
    if not row or not _verify(row["password_hash"], row["salt"], body.password):
        _record_failure(identifier)
        # Persist failed attempt to DB for audit (best-effort)
        try:
            execute(
                "INSERT INTO login_attempts (identifier, succeeded) VALUES (?,0)",
                (identifier,),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid username or password")

    _clear_attempts(identifier)
    user_dict = _user_to_dict(row)
    token = create_token(user_dict)

    # Log successful login
    try:
        execute(
            "INSERT INTO login_attempts (identifier, succeeded) VALUES (?,1)",
            (identifier,),
        )
        execute(
            "UPDATE users SET last_login=datetime('now') WHERE id=?",
            (user_dict["id"],),
        )
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user_dict["id"], "login", "users", user_dict["id"],
             f"Login from {request.client.host if request.client else 'unknown'}"),
        )
    except Exception:
        pass

    return {
        "token": token,
        "must_change_pw": bool(row["must_change_pw"]),
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


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password:     str


@router.post("/change-password")
def change_password(body: ChangePasswordBody, user: Usr):
    if len(body.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    row = fetch_one("SELECT * FROM users WHERE id=?", (user["id"],))
    if not row or not _verify(row["password_hash"], row["salt"], body.current_password):
        raise HTTPException(400, "Current password is incorrect")
    import hashlib, secrets
    salt     = secrets.token_hex(16)
    pw_hash  = hashlib.sha256((salt + body.new_password).encode()).hexdigest()
    execute(
        "UPDATE users SET password_hash=?, salt=?, must_change_pw=0 WHERE id=?",
        (pw_hash, salt, user["id"]),
    )
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "password_change", "users", user["id"], "Password changed by user"),
        )
    except Exception:
        pass
    return {"ok": True}


@router.post("/logout")
def logout(user: Usr):
    return {"ok": True}


@router.get("/me")
def me(user: Usr):
    row = fetch_one("SELECT must_change_pw FROM users WHERE id=?", (user["id"],))
    # Always re-compute permissions from DB so revocations reflect immediately
    fresh_perms = compute_effective_permissions(user["id"])
    return {
        "id":             user["id"],
        "username":       user["username"],
        "full_name":      user["full_name"],
        "role":           user["role"],
        "role_label":     user["role_label"],
        "role_color":     user["role_color"],
        "permissions":    fresh_perms,
        "must_change_pw": bool(row["must_change_pw"]) if row else False,
    }
