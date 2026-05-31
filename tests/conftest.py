"""
Shared fixtures for backend integration tests.

Targets the test stack defined in docker-compose.test.yml:
  docker compose -f docker-compose.test.yml up --build -d --wait

Override the base URL with:
  TEST_BASE_URL=http://myserver:8765 pytest
"""

import os
import time
import pytest
import requests

BASE = os.getenv("TEST_BASE_URL", "http://localhost:18765")

ADMIN_USERNAME = "testadmin"
ADMIN_PASSWORD = "TestPass@1234"
SCHOOL_NAME    = "Pytest School"


def _api(method: str, path: str, **kwargs) -> requests.Response:
    """Thin wrapper so tests don't hard-code the base URL."""
    return requests.request(method, f"{BASE}/api{path}", timeout=15, **kwargs)


# ── Session-level fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def wait_for_backend():
    """Block until the backend is healthy (up to 60 s)."""
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE}/api/health", timeout=5)
            if r.status_code == 200:
                return
        except requests.ConnectionError:
            pass
        time.sleep(2)
    pytest.fail(f"Backend at {BASE} did not become healthy within 60 s")


@pytest.fixture(scope="session")
def initialized(wait_for_backend):
    """
    Run the setup wizard exactly once per test session.
    If the school is already initialized (e.g. leftover data), that's fine too.
    """
    r = _api("POST", "/setup/initialize", json={
        "school_name":    SCHOOL_NAME,
        "school_address": "1 Test Avenue",
        "admin_username": ADMIN_USERNAME,
        "admin_fullname": "Pytest Admin",
        "admin_password": ADMIN_PASSWORD,
        "plan_name":      "premium",
    })
    # 200 = freshly initialised, 400 = already done — both are acceptable
    assert r.status_code in (200, 400), f"Unexpected setup response: {r.status_code} {r.text}"
    return r.status_code == 200


@pytest.fixture  # function-scoped: each test gets a fresh token so session-revoking tests don't bleed into each other
def admin_token(initialized):
    r = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    })
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    return r.json()["token"]


@pytest.fixture  # function-scoped: matches admin_token
def auth(admin_token):
    """Authorization header dict ready to pass as `headers=auth`."""
    return {"Authorization": f"Bearer {admin_token}"}


# ── Helpers re-exported so tests can call _api without importing conftest ─────

@pytest.fixture(scope="session")
def api():
    return _api
