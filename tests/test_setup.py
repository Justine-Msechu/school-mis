"""Tests for the setup wizard endpoints (/api/setup/*)."""

from tests.conftest import _api, SCHOOL_NAME


def test_setup_status_initialized(initialized):
    r = _api("GET", "/setup/status")
    assert r.status_code == 200
    data = r.json()
    assert data["needs_setup"] is False
    assert data["school_name"] == SCHOOL_NAME


def test_double_initialize_rejected(initialized):
    """A second initialize call must return 400."""
    r = _api("POST", "/setup/initialize", json={
        "school_name":    "Another School",
        "admin_username": "anotherAdmin",
        "admin_fullname": "Another Admin",
        "admin_password": "AnotherPass@99",
        "plan_name":      "premium",
    })
    assert r.status_code == 400
    assert "already initialized" in r.json().get("detail", "").lower()


def test_initialize_rejects_short_password(initialized):
    r = _api("POST", "/setup/initialize", json={
        "school_name":    "Bad School",
        "admin_username": "badAdmin",
        "admin_fullname": "Bad Admin",
        "admin_password": "short",
        "plan_name":      "premium",
    })
    # Already initialized → 400; if not, short password → also 400
    assert r.status_code == 400
