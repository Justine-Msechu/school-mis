"""Shared FastAPI dependencies — token auth that hydrates the session singleton."""

import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import Header, HTTPException, status

# Simple in-memory token store: {token: user_dict}
# Production: replace with Redis or signed JWT
_TOKEN_STORE: dict[str, dict] = {}
_TOKEN_EXPIRY: dict[str, float] = {}
TOKEN_TTL = 8 * 3600  # 8 hours


def create_token(user_dict: dict) -> str:
    import secrets
    token = secrets.token_hex(32)
    _TOKEN_STORE[token] = user_dict
    _TOKEN_EXPIRY[token] = time.time() + TOKEN_TTL
    return token


def get_user_from_token(token: str) -> dict | None:
    if token not in _TOKEN_STORE:
        return None
    if time.time() > _TOKEN_EXPIRY.get(token, 0):
        _TOKEN_STORE.pop(token, None)
        _TOKEN_EXPIRY.pop(token, None)
        return None
    return _TOKEN_STORE[token]


def revoke_token(token: str):
    _TOKEN_STORE.pop(token, None)
    _TOKEN_EXPIRY.pop(token, None)


def require_auth(authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization[7:]
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
    return user


def hydrate_session(user_dict: dict):
    """Hydrate the auth.session singleton so existing services work without changes."""
    from auth.session import session
    session.login(user_dict)
