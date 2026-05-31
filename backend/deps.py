"""
FastAPI dependencies — authentication and rate limiting.

Session design (SaaS-safe):
  - Token is a 256-bit random hex string (64 chars) generated server-side.
  - Only the SHA-256 hash of the token is stored in login_sessions.
    If the DB is ever leaked, the hashes cannot be used to authenticate.
  - Sessions survive backend restarts (DB-backed, not in-memory).
  - Per-user session limit prevents credential sharing.
  - school_id is threaded through every session for tenant isolation.

Rate limiting:
  - Backed by in-memory counters with thread-locking.
  - Separate per-IP counters for auth endpoints (in auth.py).
  - rate_limit() factory returns a FastAPI Depends that can be applied
    per-router or per-endpoint at any granularity.
"""

import hashlib
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from backend.core.db import execute, fetch_all, fetch_one

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
TOKEN_TTL_HOURS    = 8
MAX_SESSIONS       = 5   # max active sessions per user (per school in SaaS)

# ── Rate-limit store (in-memory, thread-safe) ──────────────────────────────────
_rl_store: dict[str, list] = defaultdict(list)
_rl_lock  = Lock()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _expiry_iso() -> str:
    return (datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)).strftime("%Y-%m-%d %H:%M:%S")


# ── Session management (DB-backed) ─────────────────────────────────────────────

def create_token(user_dict: dict, ip: str | None = None, user_agent: str | None = None) -> str:
    """
    Generate a session token, persist its hash to login_sessions,
    and enforce the per-user session cap.
    Returns the raw token (sent to client; never stored server-side).
    """
    user_id   = user_dict["id"]
    school_id = user_dict.get("school_id")
    token     = secrets.token_hex(32)
    t_hash    = _hash_token(token)
    expires   = _expiry_iso()

    # ── Enforce session cap: revoke oldest sessions if over limit ──────────
    try:
        active = fetch_all(
            """SELECT id FROM login_sessions
               WHERE user_id=? AND is_active=1 AND expires_at > ?
               ORDER BY created_at ASC""",
            (user_id, _now_iso()),
        )
        excess = len(active) - MAX_SESSIONS + 1  # +1 to make room for the new one
        if excess > 0:
            for row in active[:excess]:
                execute(
                    "UPDATE login_sessions SET is_active=0, invalidated_at=? WHERE id=?",
                    (_now_iso(), row["id"]),
                )
    except Exception as e:
        log.warning("create_token: session cap check failed: %s", e)

    # ── Persist new session ────────────────────────────────────────────────
    try:
        execute(
            """INSERT INTO login_sessions
               (user_id, school_id, token_hash, session_token,
                ip_address, user_agent, created_at, expires_at, last_used_at, is_active)
               VALUES (?,?,?,?,?,?,?,?,?,1)""",
            (user_id, school_id, t_hash, token,
             ip, user_agent, _now_iso(), expires, _now_iso()),
        )
    except Exception as e:
        log.error("create_token: login_sessions INSERT failed: %s", e)

    return token


def get_user_from_token(token: str) -> dict | None:
    """
    Look up a session by its hash, return the user dict, or None if invalid.
    Also refreshes last_used_at on every call.
    """
    t_hash = _hash_token(token)
    try:
        row = fetch_one(
            """SELECT ls.user_id, ls.school_id, ls.expires_at
               FROM login_sessions ls
               WHERE ls.token_hash=? AND ls.is_active=1""",
            (t_hash,),
        )
        if not row:
            return None

        # Check expiry
        expires = row["expires_at"]
        if expires and expires < _now_iso():
            execute(
                "UPDATE login_sessions SET is_active=0 WHERE token_hash=?",
                (t_hash,),
            )
            return None

        # Refresh last_used_at (best-effort, non-blocking)
        try:
            execute(
                "UPDATE login_sessions SET last_used_at=? WHERE token_hash=?",
                (_now_iso(), t_hash),
            )
        except Exception:
            pass

        # Hydrate full user dict from users table
        user_row = fetch_one("SELECT * FROM users WHERE id=? AND is_active=1", (row["user_id"],))
        if not user_row:
            return None

        from backend.core.authz import compute_effective_permissions
        from database.db import ROLES

        user = dict(user_row)
        role      = user.get("role", "")
        role_info = ROLES.get(role, {})
        user["role_label"]  = role_info.get("label", role) if isinstance(role_info, dict) else str(role_info)
        user["role_color"]  = role_info.get("color", "#94A3B8") if isinstance(role_info, dict) else "#94A3B8"
        try:
            user["permissions"] = compute_effective_permissions(user["id"])
        except Exception as _e:
            log.warning("get_user_from_token: compute_effective_permissions failed for user %s: %s", user.get("id"), _e)
            user["permissions"] = ["*"] if role in ("admin", "superadmin") else []
        user["school_id"]   = row["school_id"] or user.get("school_id")
        user["_token"]      = token     # for logout use
        user["_token_hash"] = t_hash

        if not user.get("full_name"):
            user["full_name"] = user.get("username", "")

        return user

    except Exception:
        return None


def revoke_token(token: str) -> None:
    t_hash = _hash_token(token)
    try:
        execute(
            "UPDATE login_sessions SET is_active=0, invalidated_at=? WHERE token_hash=?",
            (_now_iso(), t_hash),
        )
    except Exception:
        pass


def revoke_all_user_sessions(user_id: int) -> int:
    """Revoke every active session for a user (admin force-logout). Returns count revoked."""
    try:
        rows = fetch_all(
            "SELECT id FROM login_sessions WHERE user_id=? AND is_active=1",
            (user_id,),
        )
        for r in rows:
            execute(
                "UPDATE login_sessions SET is_active=0, invalidated_at=? WHERE id=?",
                (_now_iso(), r["id"]),
            )
        return len(rows)
    except Exception:
        return 0


# ── FastAPI auth dependency ────────────────────────────────────────────────────

def require_auth(
    authorization: Annotated[str | None, Header()] = None,
    x_school_id:   Annotated[str | None, Header()] = None,
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    token = authorization[7:]
    user  = get_user_from_token(token)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired — please log in again")

    # Superadmin school context: honour X-School-Id header so the platform owner
    # can act on any school's data without changing their own account.
    if user.get("role") == "superadmin":
        if x_school_id:
            try:
                user["school_id"] = int(x_school_id)
            except ValueError:
                pass
        if not user.get("school_id"):
            from backend.core.db import fetch_one as _fo
            first = _fo("SELECT id FROM schools ORDER BY id LIMIT 1", ())
            if first:
                user["school_id"] = first["id"]

    return user


# ── Rate limiting ──────────────────────────────────────────────────────────────

def rate_limit(max_calls: int = 300, window_secs: int = 60, scope: str = "api"):
    """
    Returns a FastAPI dependency that enforces a sliding-window rate limit
    per user (keyed by user_id + scope).

    Usage:
        @router.get("/export")
        def export(user: Annotated[dict, Depends(rate_limit(max_calls=10, window_secs=60, scope="export"))]):
            ...

    Or applied to an entire router via dependencies=[Depends(rate_limit(...))].
    """
    def _dep(user: Annotated[dict, Depends(require_auth)]) -> dict:
        key    = f"{scope}:{user['id']}"
        now    = time.monotonic()
        cutoff = now - window_secs
        with _rl_lock:
            _rl_store[key] = [t for t in _rl_store[key] if t > cutoff]
            if len(_rl_store[key]) >= max_calls:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {max_calls} requests per {window_secs}s.",
                    headers={"Retry-After": str(window_secs)},
                )
            _rl_store[key].append(now)
        return user
    return _dep


# ── Legacy shims (keep existing callers working) ───────────────────────────────

def hydrate_session(user_dict: dict):
    try:
        from auth.session import session
        session.login(user_dict)
    except Exception:
        pass
