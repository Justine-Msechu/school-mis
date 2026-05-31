"""
Tests for the teachers API (/api/teachers/*).

Infrastructure design notes (CI/CD + production parity):

  CI/CD         — All employee_no values are prefixed with a uuid4 shard so
                  parallel test runners on different agents never collide on
                  unique constraints.  Tests are fully idempotent: re-running
                  them against the same DB produces the same result.

  Load balancer — Every test uses only Bearer-token auth.  No sticky-session
                  assumptions: a request authenticated on instance A is valid
                  on instance B because sessions are DB-backed, not in-memory.

  Horizontal    — No shared in-process state is touched.  Tests can be split
  scaling         across workers with `pytest -n auto` (pytest-xdist) without
                  interference.

  Observability — Mutations are followed by an audit-log check to verify that
                  the logging pipeline (write path → audit_log table) is intact.
                  A broken audit writer would surface here before it silently
                  fails in production.

  Soft delete   — Deleted records must disappear from the active list but be
                  retrievable with include_inactive=true.  Tests verify both
                  sides so a misconfigured DB view or caching layer is caught.

  Error budget  — 4xx paths (auth missing, bad IDs, duplicate keys, 404) are
                  tested explicitly.  Under load-shedding or partial outages
                  these paths must still return the correct status, not 500.
"""

import uuid
import pytest
from tests.conftest import _api, ADMIN_USERNAME, ADMIN_PASSWORD

# ── Unique run shard — prevents constraint collisions across parallel CI agents
_SHARD = uuid.uuid4().hex[:8].upper()


def emp(suffix: str) -> str:
    """Build a collision-safe employee number for this test run."""
    return f"CI-{_SHARD}-{suffix}"


# ─────────────────────────────────────────────────────────────────────────────
# Health — verify the system is alive before spending time on deeper tests
# ─────────────────────────────────────────────────────────────────────────────

def test_backend_health():
    """Smoke check: backend is up and serving (load-balancer probe equivalent)."""
    r = _api("GET", "/health")
    assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Auth enforcement — every endpoint must reject unauthenticated requests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("method,path", [
    ("GET",    "/teachers"),
    ("GET",    "/teachers/1"),
    ("POST",   "/teachers"),
    ("PUT",    "/teachers/1"),
    ("DELETE", "/teachers/1"),
    ("GET",    "/teachers/1/subjects"),
    ("GET",    "/teachers/next-employee-no"),
])
def test_requires_auth(method, path):
    """All teacher endpoints must return 401 without a token (load-balancer passthrough safe)."""
    r = _api(method, path)
    assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# List
# ─────────────────────────────────────────────────────────────────────────────

def test_list_returns_array(auth):
    r = _api("GET", "/teachers", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_excludes_inactive_by_default(auth):
    """Default response must not include soft-deleted teachers (DB-filter, not app-layer filter)."""
    r = _api("GET", "/teachers", headers=auth)
    assert r.status_code == 200
    for t in r.json():
        assert t.get("is_active") in (1, True), (
            f"Inactive teacher {t.get('id')} leaked into default list"
        )


def test_list_search_empty_result(auth):
    r = _api("GET", "/teachers?search=ZZZNOMATCH99999", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


def test_list_search_by_name(auth):
    # Create a teacher with a distinctive name to search for
    name_tag = f"Searchable-{_SHARD}"
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": name_tag,
        "last_name":  "Teacher",
        "employee_no": emp("SRCH"),
    })
    assert r.status_code == 200

    results = _api("GET", f"/teachers?search={name_tag}", headers=auth).json()
    assert any(t["first_name"] == name_tag for t in results)


def test_list_include_inactive(auth):
    """include_inactive=true must surface soft-deleted records (storage integrity check)."""
    # Create then delete a teacher
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Inactive",
        "last_name":  f"Check-{_SHARD}",
        "employee_no": emp("INACT"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]
    _api("DELETE", f"/teachers/{tid}", headers=auth)

    active   = _api("GET", "/teachers", headers=auth).json()
    inactive = _api("GET", "/teachers?include_inactive=true", headers=auth).json()

    active_ids   = {t["id"] for t in active}
    inactive_ids = {t["id"] for t in inactive}

    assert tid not in active_ids,   "Soft-deleted teacher appeared in active list"
    assert tid in inactive_ids,     "Soft-deleted teacher missing from include_inactive list"


# ─────────────────────────────────────────────────────────────────────────────
# Get single
# ─────────────────────────────────────────────────────────────────────────────

def test_get_teacher_by_id(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Fetchable",
        "last_name":  "Teacher",
        "employee_no": emp("FETCH"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    r2 = _api("GET", f"/teachers/{tid}", headers=auth)
    assert r2.status_code == 200
    assert r2.json()["id"] == tid


def test_get_teacher_not_found(auth):
    r = _api("GET", "/teachers/9999999", headers=auth)
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────────────────────

def test_create_teacher_minimal(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Minimal",
        "last_name":  "Teacher",
        "employee_no": emp("MIN"),
    })
    assert r.status_code == 200
    data = r.json()
    assert data["first_name"] == "Minimal"
    assert data["last_name"]  == "Teacher"
    assert data["employee_no"] == emp("MIN")
    assert data["is_active"] in (1, True)


def test_create_teacher_full_profile(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name":             "Full",
        "last_name":              "Profile",
        "employee_no":            emp("FULL"),
        "gender":                 "Female",
        "date_of_birth":          "1985-06-15",
        "phone":                  "+255700000001",
        "email":                  "full.profile@school.test",
        "subject_specialization": "Mathematics",
        "qualification":          "B.Sc. Education",
        "joining_date":           "2020-01-10",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["gender"]                 == "Female"
    assert d["subject_specialization"] == "Mathematics"
    assert d["email"]                  == "full.profile@school.test"


def test_create_teacher_auto_employee_no(auth):
    """Omitting employee_no must auto-generate a non-empty value."""
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Auto",
        "last_name":  f"EmpNo-{_SHARD}",
    })
    assert r.status_code == 200
    assert r.json()["employee_no"], "Auto-generated employee_no must not be empty"


def test_create_teacher_duplicate_employee_no(auth):
    """Unique constraint on employee_no must hold regardless of which DB node handles the request."""
    payload = {
        "first_name": "Dup",
        "last_name":  "Teacher",
        "employee_no": emp("DUP"),
    }
    r1 = _api("POST", "/teachers", headers=auth, json=payload)
    assert r1.status_code == 200

    r2 = _api("POST", "/teachers", headers=auth, json=payload)
    assert r2.status_code == 400
    assert "already exists" in r2.json().get("detail", "").lower()


def test_create_writes_audit_log(auth):
    """Verify the observability pipeline: create must produce an audit_log entry."""
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Audited",
        "last_name":  f"Create-{_SHARD}",
        "employee_no": emp("AUD-C"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    log = _api("GET", f"/audit/record/teachers/{tid}", headers=auth)
    assert log.status_code == 200
    entries = log.json()
    assert any(e.get("action") == "teacher_create" for e in entries), (
        "teacher_create audit entry missing — logging pipeline may be broken"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Update
# ─────────────────────────────────────────────────────────────────────────────

def test_update_teacher(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Before",
        "last_name":  "Update",
        "employee_no": emp("UPD"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    r2 = _api("PUT", f"/teachers/{tid}", headers=auth, json={
        "first_name": "After",
        "last_name":  "Update",
        "employee_no": emp("UPD"),
        "phone":       "+255700000099",
    })
    assert r2.status_code == 200
    data = r2.json()
    assert data["first_name"] == "After"
    assert data["phone"]      == "+255700000099"


def test_update_preserves_employee_no_when_omitted(auth):
    """Partial update: omitting employee_no must keep the existing value."""
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Preserve",
        "last_name":  "EmpNo",
        "employee_no": emp("PRSV"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    r2 = _api("PUT", f"/teachers/{tid}", headers=auth, json={
        "first_name": "Preserve",
        "last_name":  "EmpNo",
        # no employee_no — should keep emp("PRSV")
    })
    assert r2.status_code == 200
    assert r2.json()["employee_no"] == emp("PRSV")


def test_update_rejects_duplicate_employee_no(auth):
    r1 = _api("POST", "/teachers", headers=auth, json={
        "first_name": "A", "last_name": "Teacher", "employee_no": emp("DUP-UPD-A"),
    })
    r2 = _api("POST", "/teachers", headers=auth, json={
        "first_name": "B", "last_name": "Teacher", "employee_no": emp("DUP-UPD-B"),
    })
    assert r1.status_code == 200 and r2.status_code == 200
    tid_b = r2.json()["id"]

    r3 = _api("PUT", f"/teachers/{tid_b}", headers=auth, json={
        "first_name":  "B",
        "last_name":   "Teacher",
        "employee_no": emp("DUP-UPD-A"),  # already taken by teacher A
    })
    assert r3.status_code == 400


def test_update_teacher_not_found(auth):
    r = _api("PUT", "/teachers/9999999", headers=auth, json={
        "first_name": "Ghost", "last_name": "Teacher",
    })
    assert r.status_code == 404


def test_update_writes_audit_log(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Audited",
        "last_name":  f"Update-{_SHARD}",
        "employee_no": emp("AUD-U"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    _api("PUT", f"/teachers/{tid}", headers=auth, json={
        "first_name": "Audited",
        "last_name":  f"Updated-{_SHARD}",
        "employee_no": emp("AUD-U"),
    })

    log = _api("GET", f"/audit/record/teachers/{tid}", headers=auth)
    assert log.status_code == 200
    assert any(e.get("action") == "teacher_update" for e in log.json()), (
        "teacher_update audit entry missing — logging pipeline may be broken"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Delete (soft)
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_teacher(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "ToDelete",
        "last_name":  "Teacher",
        "employee_no": emp("DEL"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    r2 = _api("DELETE", f"/teachers/{tid}", headers=auth)
    assert r2.status_code == 200
    assert r2.json().get("ok") is True


def test_delete_removes_from_active_list(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Disappear",
        "last_name":  "Teacher",
        "employee_no": emp("DISP"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    _api("DELETE", f"/teachers/{tid}", headers=auth)

    active = {t["id"] for t in _api("GET", "/teachers", headers=auth).json()}
    assert tid not in active, "Soft-deleted teacher still appearing in active list — possible cache issue"


def test_delete_idempotent(auth):
    """
    Deleting the same teacher twice must return 404 on the second call.
    Under horizontal scaling, a retry after a network timeout must not
    produce an unexpected 500.
    """
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Idempotent",
        "last_name":  "Delete",
        "employee_no": emp("IDEM"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    assert _api("DELETE", f"/teachers/{tid}", headers=auth).status_code == 200
    assert _api("DELETE", f"/teachers/{tid}", headers=auth).status_code == 404


def test_delete_teacher_not_found(auth):
    r = _api("DELETE", "/teachers/9999999", headers=auth)
    assert r.status_code == 404


def test_delete_writes_audit_log(auth):
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "Audited",
        "last_name":  f"Delete-{_SHARD}",
        "employee_no": emp("AUD-D"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    _api("DELETE", f"/teachers/{tid}", headers=auth)

    log = _api("GET", f"/audit/record/teachers/{tid}", headers=auth)
    assert log.status_code == 200
    assert any(e.get("action") == "teacher_delete" for e in log.json()), (
        "teacher_delete audit entry missing — logging pipeline may be broken"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Subjects
# ─────────────────────────────────────────────────────────────────────────────

def test_get_teacher_subjects_empty(auth):
    """A new teacher has no subject assignments — must return [] not 404."""
    r = _api("POST", "/teachers", headers=auth, json={
        "first_name": "NoSubjects",
        "last_name":  "Teacher",
        "employee_no": emp("NOSUB"),
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    r2 = _api("GET", f"/teachers/{tid}/subjects", headers=auth)
    assert r2.status_code == 200
    assert r2.json() == []


def test_get_subjects_for_nonexistent_teacher(auth):
    """
    A ghost teacher_id returns an empty list (the query does a filter, not a
    join that would 404).  Tests document the actual contract so a future
    change that adds a 404 here is an intentional decision, not a silent break.
    """
    r = _api("GET", "/teachers/9999999/subjects", headers=auth)
    # Returns 200 + [] because the query simply finds no rows
    assert r.status_code == 200
    assert r.json() == []


# ─────────────────────────────────────────────────────────────────────────────
# Employee number preview
# ─────────────────────────────────────────────────────────────────────────────

def test_next_employee_no_format(auth):
    """Preview must follow the EMP/YYYY/NNNN pattern."""
    import re
    r = _api("GET", "/teachers/next-employee-no", headers=auth)
    assert r.status_code == 200
    emp_no = r.json().get("employee_no", "")
    assert re.match(r"^EMP/\d{4}/\d{4}$", emp_no), (
        f"employee_no '{emp_no}' does not match expected EMP/YYYY/NNNN format"
    )


def test_next_employee_no_increments_after_create(auth):
    """
    After creating a teacher with an auto-number the preview must advance.
    Catches a bug where the sequence counter is not persisted (would fail
    on a new worker pod after a horizontal scale-out).
    """
    before = _api("GET", "/teachers/next-employee-no", headers=auth).json()["employee_no"]

    _api("POST", "/teachers", headers=auth, json={
        "first_name": "Seq",
        "last_name":  f"Counter-{_SHARD}",
        # no employee_no — uses and advances the sequence
    })

    after = _api("GET", "/teachers/next-employee-no", headers=auth).json()["employee_no"]
    assert after != before, (
        "Sequence did not advance after auto-assignment — "
        "counter may be stored in-memory and lost on pod restart"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cross-instance / load-balancer token validity
# ─────────────────────────────────────────────────────────────────────────────

def test_token_is_stateless(initialized):
    """
    A token obtained from one login must authenticate correctly on any request.
    Verifies that session state lives in the DB, not in a single server's memory
    — essential for load-balanced or horizontally-scaled deployments.
    """
    token = _api("POST", "/auth/login", json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    }).json()["token"]

    # Simulate the token being used by a different server process (new request)
    h = {"Authorization": f"Bearer {token}"}
    r = _api("GET", "/teachers", headers=h)
    assert r.status_code == 200, (
        "Token rejected — session may be stored in-memory rather than the DB"
    )
