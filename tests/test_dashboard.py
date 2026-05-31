"""Tests for the dashboard stats endpoint (/api/dashboard/stats)."""

from tests.conftest import _api


def test_dashboard_stats_requires_auth():
    r = _api("GET", "/dashboard/stats")
    assert r.status_code == 401


def test_dashboard_stats_authenticated(auth):
    r = _api("GET", "/dashboard/stats", headers=auth)
    assert r.status_code == 200
    data = r.json()
    # Admin has wildcard permissions, so all stat keys should be present
    assert "students" in data
    assert "teachers" in data
    assert "classes" in data
    assert isinstance(data["students"], int)
    assert isinstance(data["teachers"], int)
    assert isinstance(data["classes"], int)


def test_dashboard_stats_attendance_fields(auth):
    r = _api("GET", "/dashboard/stats", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert "attendance_today" in data
    assert "attendance_rate" in data
    assert 0.0 <= data["attendance_rate"] <= 100.0


def test_dashboard_stats_recent_activity(auth):
    r = _api("GET", "/dashboard/stats", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert "recent_activity" in data
    assert isinstance(data["recent_activity"], list)
    # At minimum the login action was recorded during setup
    assert len(data["recent_activity"]) >= 1
