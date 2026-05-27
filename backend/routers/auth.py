"""
Authentication router.

Password scheme:
  Legacy users: SHA-256(salt + password) — pw_scheme = 'sha256'
  New / upgraded users: bcrypt — pw_scheme = 'bcrypt'

Auto-upgrade: when a SHA-256 user logs in successfully, their hash is
silently upgraded to bcrypt. The next login uses bcrypt.

Why bcrypt over SHA-256?
  SHA-256 runs at ~1 billion guesses/second on a GPU.
  bcrypt (cost 12) runs at ~300 guesses/second — 3 million× slower.
"""

import hashlib
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.core.authz import compute_effective_permissions
from backend.core.db import execute, fetch_all, fetch_one
from backend.deps import (
    create_token, require_auth, revoke_token,
    revoke_all_user_sessions, hydrate_session, rate_limit,
)
from database.db import ROLES

router = APIRouter(tags=["auth"])
Usr = Annotated[dict, Depends(require_auth)]

BCRYPT_COST = 12   # ~300ms per hash — strong against brute force

# ── Login brute-force protection ──────────────────────────────────────────────
# NOTE: also persisted to login_attempts table so it survives restarts.
_MAX_ATTEMPTS = 5
_WINDOW_SECS  = 300    # 5-minute sliding window
_LOCKOUT_SECS = 900    # 15-minute lockout
_attempts: dict[str, list] = defaultdict(list)
_lock = Lock()


def _check_rate_limit(identifier: str):
    # Check DB first (survives restarts, guards distributed deployments)
    try:
        cutoff = (datetime.utcnow() - timedelta(seconds=_WINDOW_SECS)).strftime("%Y-%m-%d %H:%M:%S")
        row = fetch_one(
            "SELECT COUNT(*) as n FROM login_attempts WHERE identifier=? AND succeeded=0 AND created_at >= ?",
            (identifier, cutoff),
        )
        if row and row["n"] >= _MAX_ATTEMPTS:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many failed login attempts. Try again in 15 minutes.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # DB not available — fall through to in-memory check

    # In-memory check (fast path, same-process)
    now    = datetime.now(timezone.utc)
    cutoff_dt = now - timedelta(seconds=_WINDOW_SECS)
    with _lock:
        _attempts[identifier] = [t for t in _attempts[identifier] if t > cutoff_dt]
        if len(_attempts[identifier]) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many failed login attempts. Try again in 15 minutes.",
            )


def _record_failure(identifier: str):
    with _lock:
        _attempts[identifier].append(datetime.now(timezone.utc))
    try:
        execute("INSERT INTO login_attempts (identifier, succeeded) VALUES (?,0)", (identifier,))
    except Exception:
        pass


def _clear_attempts(identifier: str):
    with _lock:
        _attempts.pop(identifier, None)


# ── Password helpers ──────────────────────────────────────────────────────────

def _verify_sha256(stored_hash: str, salt: str, password: str) -> bool:
    return hashlib.sha256((salt + password).encode()).hexdigest() == stored_hash


def _verify_bcrypt(stored_hash: str, password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except Exception:
        return False


def _hash_bcrypt(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_COST)).decode()


def _verify(row, password: str) -> bool:
    d = dict(row)
    scheme = d.get("pw_scheme", "sha256")
    if scheme == "bcrypt":
        return _verify_bcrypt(d["password_hash"], password)
    # Legacy SHA-256
    return _verify_sha256(d["password_hash"], d.get("salt", ""), password)


def _upgrade_to_bcrypt(user_id: int, password: str):
    """Silently upgrade a SHA-256 password to bcrypt after successful login."""
    try:
        new_hash = _hash_bcrypt(password)
        execute(
            "UPDATE users SET password_hash=?, pw_scheme='bcrypt', salt='' WHERE id=?",
            (new_hash, user_id),
        )
    except Exception:
        pass  # non-critical — upgrade on next login


def _user_to_dict(row) -> dict:
    user      = dict(row)
    role      = user.get("role", "")
    role_info = ROLES.get(role, {})
    user["role_label"]  = role_info.get("label", role) if isinstance(role_info, dict) else str(role_info)
    user["role_color"]  = role_info.get("color", "#94A3B8") if isinstance(role_info, dict) else "#94A3B8"
    user["permissions"] = compute_effective_permissions(user["id"])
    if not user.get("full_name"):
        user["full_name"] = user.get("username", "")
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, request: Request):
    identifier = body.username.strip().lower()
    _check_rate_limit(identifier)

    row = fetch_one(
        "SELECT * FROM users WHERE username=? AND is_active=1",
        (body.username.strip(),),
    )

    if not row or not _verify(row, body.password):
        _record_failure(identifier)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    _clear_attempts(identifier)

    # Auto-upgrade SHA-256 → bcrypt on successful login
    row_dict = dict(row)
    if row_dict.get("pw_scheme", "sha256") == "sha256":
        _upgrade_to_bcrypt(row_dict["id"], body.password)

    # Ensure user_roles is in sync (fixes users created before this was enforced)
    from database.db import sync_user_role
    sync_user_role(row_dict["id"], row_dict.get("role", ""))

    user_dict = _user_to_dict(row)
    ip        = request.client.host if request.client else None
    ua        = request.headers.get("user-agent", "")[:200]
    token     = create_token(user_dict, ip=ip, user_agent=ua)

    try:
        execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user_dict["id"],))
        execute(
            "INSERT INTO login_attempts (identifier, succeeded) VALUES (?,1)",
            (identifier,),
        )
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user_dict["id"], "login", "users", user_dict["id"],
             f"Login from {ip or 'unknown'} ({row_dict.get('pw_scheme','sha256')})"),
        )
    except Exception:
        pass

    return {
        "token":        token,
        "must_change_pw": bool(row_dict["must_change_pw"]),
        "user": {
            "id":          user_dict["id"],
            "username":    user_dict["username"],
            "full_name":   user_dict["full_name"],
            "role":        user_dict["role"],
            "role_label":  user_dict["role_label"],
            "role_color":  user_dict["role_color"],
            "permissions": user_dict["permissions"],
            "school_id":   user_dict.get("school_id"),
        },
    }


@router.post("/logout")
def logout(user: Usr):
    revoke_token(user.get("_token", ""))
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "logout", "users", user["id"], "User logged out"),
        )
    except Exception:
        pass
    return {"ok": True}


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password:     str


@router.post("/change-password")
def change_password(body: ChangePasswordBody, user: Usr):
    if len(body.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    row = fetch_one("SELECT * FROM users WHERE id=?", (user["id"],))
    if not row or not _verify(row, body.current_password):
        raise HTTPException(400, "Current password is incorrect")

    new_hash = _hash_bcrypt(body.new_password)
    execute(
        "UPDATE users SET password_hash=?, pw_scheme='bcrypt', salt='', must_change_pw=0 WHERE id=?",
        (new_hash, user["id"]),
    )
    # Revoke all other sessions after password change (security best practice)
    revoke_all_user_sessions(user["id"])
    # Re-issue a new token for this session so user isn't logged out
    ip    = None
    token = create_token(user, ip=ip)
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "password_change", "users", user["id"],
             "Password changed — all other sessions revoked"),
        )
    except Exception:
        pass
    return {"ok": True, "token": token}


@router.get("/me")
def me(user: Usr):
    row = fetch_one("SELECT must_change_pw FROM users WHERE id=?", (user["id"],))
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
        "school_id":      user.get("school_id"),
    }


@router.get("/sessions")
def list_sessions(user: Usr):
    """Return a user's active sessions (for a 'Manage devices' UI)."""
    rows = fetch_all(
        """SELECT id, ip_address, user_agent, created_at, last_used_at, expires_at
           FROM login_sessions
           WHERE user_id=? AND is_active=1 AND expires_at > datetime('now')
           ORDER BY last_used_at DESC""",
        (user["id"],),
    )
    current_hash = user.get("_token_hash", "")
    result = []
    for r in rows:
        d = dict(r)
        # Don't expose token_hash — just indicate which is current
        _sh = fetch_one("SELECT token_hash FROM login_sessions WHERE id=?", (r["id"],))
        d["is_current"] = (dict(_sh).get("token_hash") if _sh else None) == current_hash
        result.append(d)
    return result


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: int, user: Usr):
    """Revoke a specific session (e.g. 'log out of phone')."""
    row = fetch_one(
        "SELECT id FROM login_sessions WHERE id=? AND user_id=?",
        (session_id, user["id"]),
    )
    if not row:
        raise HTTPException(404, "Session not found")
    execute(
        "UPDATE login_sessions SET is_active=0, invalidated_at=datetime('now') WHERE id=?",
        (session_id,),
    )
    return {"ok": True}


@router.post("/sessions/revoke-all")
def revoke_all_sessions(user: Usr):
    """Log out of all devices (keep current session alive)."""
    current_hash = user.get("_token_hash", "")
    execute(
        """UPDATE login_sessions SET is_active=0, invalidated_at=datetime('now')
           WHERE user_id=? AND is_active=1 AND token_hash != ?""",
        (user["id"], current_hash),
    )
    return {"ok": True}
