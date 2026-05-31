"""Tests for student CRUD endpoints (/api/students/*)."""

import pytest
from tests.conftest import _api


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_students_requires_auth():
    r = _api("GET", "/students")
    assert r.status_code == 401


def test_list_students_returns_paginated(auth):
    r = _api("GET", "/students", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert isinstance(data["items"], list)


def test_list_students_pagination_params(auth):
    r = _api("GET", "/students?page=1&per_page=5", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert data["per_page"] == 5
    assert len(data["items"]) <= 5


def test_list_students_search(auth):
    r = _api("GET", "/students?search=XXXNONEXISTENT999", headers=auth)
    assert r.status_code == 200
    assert r.json()["total"] == 0


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_student_success(auth):
    r = _api("POST", "/students", headers=auth, json={
        "first_name":  "Jane",
        "last_name":   "Doe",
        "gender":      "Female",
        "admission_no": "TEST-ADM-001",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert data["admission_no"] == "TEST-ADM-001"


def test_create_student_requires_auth():
    r = _api("POST", "/students", json={
        "first_name": "Jane",
        "last_name":  "Doe",
        "gender":     "Female",
    })
    assert r.status_code == 401


def test_create_student_duplicate_admission_no(auth):
    payload = {
        "first_name":  "Dup",
        "last_name":   "Student",
        "gender":      "Male",
        "admission_no": "TEST-ADM-DUP-001",
    }
    r1 = _api("POST", "/students", headers=auth, json=payload)
    assert r1.status_code == 200

    r2 = _api("POST", "/students", headers=auth, json=payload)
    assert r2.status_code == 400
    assert "already exists" in r2.json().get("detail", "").lower()


def test_create_student_auto_admission_no(auth):
    """Omitting admission_no should auto-generate one."""
    r = _api("POST", "/students", headers=auth, json={
        "first_name": "Auto",
        "last_name":  "Number",
        "gender":     "Male",
    })
    assert r.status_code == 200
    assert r.json()["admission_no"]  # non-empty


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_student(auth):
    # Create a student to update
    create = _api("POST", "/students", headers=auth, json={
        "first_name":  "Update",
        "last_name":   "Me",
        "gender":      "Male",
        "admission_no": "TEST-ADM-UPD-001",
    })
    assert create.status_code == 200
    student_id = create.json()["id"]

    r = _api("PUT", f"/students/{student_id}", headers=auth, json={
        "first_name":  "Updated",
        "last_name":   "Name",
        "gender":      "Male",
        "admission_no": "TEST-ADM-UPD-001",
    })
    assert r.status_code == 200
    assert r.json()["first_name"] == "Updated"


def test_update_student_requires_auth():
    r = _api("PUT", "/students/9999", json={"first_name": "X", "last_name": "Y", "gender": "Male"})
    assert r.status_code == 401


# ── Delete (soft) ─────────────────────────────────────────────────────────────

def test_delete_student(auth):
    create = _api("POST", "/students", headers=auth, json={
        "first_name":  "Delete",
        "last_name":   "Me",
        "gender":      "Female",
        "admission_no": "TEST-ADM-DEL-001",
    })
    assert create.status_code == 200
    student_id = create.json()["id"]

    r = _api("DELETE", f"/students/{student_id}", headers=auth)
    assert r.status_code == 200

    # Should no longer appear in the active list
    listing = _api("GET", f"/students?search=TEST-ADM-DEL-001", headers=auth)
    assert listing.json()["total"] == 0


def test_delete_nonexistent_student(auth):
    r = _api("DELETE", "/students/9999999", headers=auth)
    assert r.status_code == 404


# ── Next admission number preview ─────────────────────────────────────────────

def test_next_admission_no(auth):
    r = _api("GET", "/students/next-admission-no", headers=auth)
    assert r.status_code == 200
    assert "admission_no" in r.json()
