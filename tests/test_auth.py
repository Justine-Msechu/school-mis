"""Tests for authentication endpoints (/api/auth/*)."""

import pytest
from tests.conftest import _api, ADMIN_USERNAME, ADMIN_PASSWORD


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(initialized):
    r = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    })
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["must_change_pw"] is False
    user = data["user"]
    assert user["username"] == ADMIN_USERNAME
    assert user["role"] == "admin"
    assert "*" in user["permissions"]


def test_login_wrong_password(initialized):
    r = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME,
        "password": "totally-wrong",
    })
    assert r.status_code == 401


def test_login_unknown_user(initialized):
    r = _api("POST", "/auth/login", json={
        "username": "nobody_exists",
        "password": "whatever",
    })
    assert r.status_code == 401


def test_login_response_has_no_password_fields(initialized):
    r = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    })
    body = r.text
    assert "password_hash" not in body
    assert "salt" not in body


# ── /me ───────────────────────────────────────────────────────────────────────

def test_me_authenticated(auth):
    r = _api("GET", "/auth/me", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == ADMIN_USERNAME
    assert data["role"] == "admin"
    assert isinstance(data["permissions"], list)
    assert "*" in data["permissions"]


def test_me_unauthenticated():
    r = _api("GET", "/auth/me")
    assert r.status_code == 401


def test_me_invalid_token():
    r = _api("GET", "/auth/me", headers={"Authorization": "Bearer deadbeef"})
    assert r.status_code == 401


def test_me_malformed_header():
    r = _api("GET", "/auth/me", headers={"Authorization": "Token abc"})
    assert r.status_code == 401


# ── Sessions ──────────────────────────────────────────────────────────────────

def test_sessions_list_non_empty(auth):
    r = _api("GET", "/auth/sessions", headers=auth)
    assert r.status_code == 200
    sessions = r.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1
    current = [s for s in sessions if s.get("is_current")]
    assert len(current) == 1


def test_revoke_specific_session(initialized):
    """Log in to get a new session, then revoke it."""
    login = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    })
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    sessions = _api("GET", "/auth/sessions", headers=headers).json()
    own_session = next((s for s in sessions if s.get("is_current")), None)
    assert own_session is not None
    session_id = own_session["id"]

    r = _api("DELETE", f"/auth/sessions/{session_id}", headers=headers)
    assert r.status_code == 200

    # Token should now be rejected
    r2 = _api("GET", "/auth/me", headers=headers)
    assert r2.status_code == 401


def test_revoke_all_sessions_keeps_current(initialized):
    tok1 = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    }).json()["token"]
    tok2 = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    }).json()["token"]

    h2 = {"Authorization": f"Bearer {tok2}"}
    r = _api("POST", "/auth/sessions/revoke-all", headers=h2)
    assert r.status_code == 200

    # tok2 (current) is still valid
    assert _api("GET", "/auth/me", headers=h2).status_code == 200

    # tok1 (other) is revoked
    h1 = {"Authorization": f"Bearer {tok1}"}
    assert _api("GET", "/auth/me", headers=h1).status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout_invalidates_token(initialized):
    login = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    })
    token = login.json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    r = _api("POST", "/auth/logout", headers=h)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r2 = _api("GET", "/auth/me", headers=h)
    assert r2.status_code == 401


def test_logout_requires_auth():
    r = _api("POST", "/auth/logout")
    assert r.status_code == 401


# ── Change password ───────────────────────────────────────────────────────────

def test_change_password_wrong_current(auth):
    r = _api("POST", "/auth/change-password", headers=auth, json={
        "current_password": "wrong_old_password",
        "new_password":     "NewPass@9999",
    })
    assert r.status_code == 400


def test_change_password_too_short(auth):
    r = _api("POST", "/auth/change-password", headers=auth, json={
        "current_password": ADMIN_PASSWORD,
        "new_password":     "short",
    })
    assert r.status_code == 400


def test_change_password_full_flow(initialized):
    """Change password on a dedicated session so the session-scoped token is unaffected."""
    tmp_token = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    }).json()["token"]
    h = {"Authorization": f"Bearer {tmp_token}"}

    new_pass = "Changed@Pass999"

    r = _api("POST", "/auth/change-password", headers=h, json={
        "current_password": ADMIN_PASSWORD,
        "new_password":     new_pass,
    })
    assert r.status_code == 200
    new_token = r.json()["token"]
    assert new_token  # a fresh token is returned immediately

    # Old token is now invalid
    assert _api("GET", "/auth/me", headers=h).status_code == 401

    # New token works
    assert _api("GET", "/auth/me", headers={
        "Authorization": f"Bearer {new_token}"
    }).status_code == 200

    # Restore original password so subsequent tests still work
    _api("POST", "/auth/change-password",
         headers={"Authorization": f"Bearer {new_token}"},
         json={"current_password": new_pass, "new_password": ADMIN_PASSWORD})
