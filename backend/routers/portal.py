"""
Portal router — student and parent self-service.

Student endpoints  (/portal/student/*)  — role: student_portal
Parent endpoints   (/portal/parent/*)   — role: parent_portal
Admin endpoints    (/portal/admin/*)    — role: admin / head_teacher
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core.security import require_permission
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["portal"])
Usr = Annotated[dict, Depends(require_auth)]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_role(user: dict, *roles: str):
    if user.get("role") not in roles:
        raise HTTPException(403, "Portal access denied")


def _student_id(user: dict) -> int:
    row = fetch_one(
        "SELECT student_id FROM student_portal_accounts WHERE user_id=?",
        (user["id"],),
    )
    if not row:
        raise HTTPException(403, "No student linked to this account")
    return row["student_id"]


def _children(user: dict) -> list[dict]:
    rows = fetch_all(
        "SELECT student_id, relation FROM parent_portal_accounts WHERE user_id=?",
        (user["id"],),
    )
    return [dict(r) for r in rows]


def _verify_child(user: dict, student_id: int) -> None:
    row = fetch_one(
        "SELECT id FROM parent_portal_accounts WHERE user_id=? AND student_id=?",
        (user["id"], student_id),
    )
    if not row:
        raise HTTPException(403, "Not linked to this student")


# ── Student portal ────────────────────────────────────────────────────────────

@router.get("/student/profile")
def student_profile(user: Usr):
    _require_role(user, "student_portal")
    sid = _student_id(user)
    row = fetch_one(
        """SELECT s.id, s.first_name, s.last_name, s.admission_no,
                  s.date_of_birth, s.gender, s.photo_path,
                  c.name AS class_name, ay.label AS year_label
           FROM students s
           LEFT JOIN classes c ON c.id = s.class_id
           LEFT JOIN academic_years ay ON ay.is_current = 1
           WHERE s.id = ?""",
        (sid,),
    )
    if not row:
        raise HTTPException(404, "Student record not found")
    return dict(row)


@router.get("/student/grades")
def student_grades(user: Usr):
    _require_role(user, "student_portal")
    sid = _student_id(user)
    rows = fetch_all(
        """SELECT e.name AS exam_name, e.term, ay.label AS year_label,
                  sub.name AS subject_name, sub.code AS subject_code,
                  g.score, g.max_score, g.grade_letter, g.remarks
           FROM grades g
           JOIN exams e         ON e.id  = g.exam_id
           JOIN subjects sub    ON sub.id = g.subject_id
           LEFT JOIN academic_years ay ON ay.id = e.academic_year_id
           WHERE g.student_id = ? AND g.status = 'approved'
           ORDER BY ay.label DESC, e.term, sub.name""",
        (sid,),
    )
    return [dict(r) for r in rows]


@router.get("/student/attendance")
def student_attendance(user: Usr, days: int = 60):
    _require_role(user, "student_portal")
    sid = _student_id(user)
    rows = fetch_all(
        """SELECT date, status, notes
           FROM attendance
           WHERE student_id = ?
             AND date >= date('now', ? || ' days')
           ORDER BY date DESC""",
        (sid, f"-{days}"),
    )
    total   = len(rows)
    present = sum(1 for r in rows if r["status"] == "present")
    return {
        "records": [dict(r) for r in rows],
        "summary": {
            "total":   total,
            "present": present,
            "absent":  sum(1 for r in rows if r["status"] == "absent"),
            "late":    sum(1 for r in rows if r["status"] == "late"),
            "rate":    round(present / total * 100, 1) if total else 0,
        },
    }


@router.get("/student/timetable")
def student_timetable(user: Usr):
    _require_role(user, "student_portal")
    sid = _student_id(user)
    student = fetch_one("SELECT class_id FROM students WHERE id=?", (sid,))
    if not student or not student["class_id"]:
        return {"slots": [], "periods": []}
    class_id = student["class_id"]

    # find active timetable version
    version = fetch_one(
        """SELECT tv.id FROM timetable_versions tv
           WHERE tv.is_active = 1
           ORDER BY tv.created_at DESC LIMIT 1""",
        (),
    )
    if not version:
        return {"slots": [], "periods": []}

    slots = fetch_all(
        """SELECT ts.day_of_week, ts.room,
                  tp.name AS period_name, tp.start_time, tp.end_time, tp.is_break,
                  sub.name AS subject_name, sub.code AS subject_code,
                  t.first_name || ' ' || t.last_name AS teacher_name
           FROM timetable_slots ts
           JOIN timetable_periods tp ON tp.id = ts.period_id
           LEFT JOIN subjects sub    ON sub.id = ts.subject_id
           LEFT JOIN teachers t      ON t.id   = ts.teacher_id
           WHERE ts.version_id = ? AND ts.class_id = ?
           ORDER BY ts.day_of_week, tp.sort_order""",
        (version["id"], class_id),
    )
    periods = fetch_all(
        "SELECT * FROM timetable_periods ORDER BY sort_order",
        (),
    )
    return {
        "slots":   [dict(r) for r in slots],
        "periods": [dict(r) for r in periods],
    }


# ── Parent portal ─────────────────────────────────────────────────────────────

@router.get("/parent/children")
def parent_children(user: Usr):
    _require_role(user, "parent_portal")
    links = _children(user)
    if not links:
        return []
    ids = [l["student_id"] for l in links]
    rel_map = {l["student_id"]: l["relation"] for l in links}
    placeholders = ",".join("?" * len(ids))
    rows = fetch_all(
        f"""SELECT s.id, s.first_name || ' ' || s.last_name AS name,
                   s.admission_no, s.photo_path,
                   c.name AS class_name
            FROM students s
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE s.id IN ({placeholders})""",
        ids,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["relation"] = rel_map.get(r["id"], "Parent")
        result.append(d)
    return result


@router.get("/parent/children/{student_id}/grades")
def parent_child_grades(student_id: int, user: Usr):
    _require_role(user, "parent_portal")
    _verify_child(user, student_id)
    rows = fetch_all(
        """SELECT e.name AS exam_name, e.term, ay.label AS year_label,
                  sub.name AS subject_name,
                  g.score, g.max_score, g.grade_letter, g.remarks
           FROM grades g
           JOIN exams e      ON e.id  = g.exam_id
           JOIN subjects sub ON sub.id = g.subject_id
           LEFT JOIN academic_years ay ON ay.id = e.academic_year_id
           WHERE g.student_id = ? AND g.status = 'approved'
           ORDER BY ay.label DESC, e.term, sub.name""",
        (student_id,),
    )
    return [dict(r) for r in rows]


@router.get("/parent/children/{student_id}/fees")
def parent_child_fees(student_id: int, user: Usr):
    _require_role(user, "parent_portal")
    _verify_child(user, student_id)
    bills = fetch_all(
        """SELECT sb.amount_due, sb.amount_paid, sb.balance,
                  sb.term, ay.label AS year_label, ft.name AS fee_name
           FROM student_bills sb
           JOIN fee_structures fs ON fs.id = sb.fee_structure_id
           JOIN fee_types ft      ON ft.id = fs.fee_type_id
           LEFT JOIN academic_years ay ON ay.id = sb.academic_year_id
           WHERE sb.student_id = ?
           ORDER BY ay.label DESC, sb.term""",
        (student_id,),
    )
    payments = fetch_all(
        """SELECT amount, payment_date, payment_method, reference_no
           FROM fee_payments
           WHERE student_id = ?
           ORDER BY payment_date DESC LIMIT 10""",
        (student_id,),
    )
    bills_list = [dict(r) for r in bills]
    total_due  = sum(r["amount_due"]  or 0 for r in bills_list)
    total_paid = sum(r["amount_paid"] or 0 for r in bills_list)
    return {
        "bills":          bills_list,
        "recent_payments": [dict(r) for r in payments],
        "total_due":      total_due,
        "total_paid":     total_paid,
        "balance":        total_due - total_paid,
    }


@router.get("/parent/children/{student_id}/attendance")
def parent_child_attendance(student_id: int, user: Usr, days: int = 60):
    _require_role(user, "parent_portal")
    _verify_child(user, student_id)
    rows = fetch_all(
        """SELECT date, status, notes
           FROM attendance
           WHERE student_id = ?
             AND date >= date('now', ? || ' days')
           ORDER BY date DESC""",
        (student_id, f"-{days}"),
    )
    total   = len(rows)
    present = sum(1 for r in rows if r["status"] == "present")
    return {
        "records": [dict(r) for r in rows],
        "summary": {
            "total":   total,
            "present": present,
            "absent":  sum(1 for r in rows if r["status"] == "absent"),
            "late":    sum(1 for r in rows if r["status"] == "late"),
            "rate":    round(present / total * 100, 1) if total else 0,
        },
    }


class LeaveRequest(BaseModel):
    date_from: str
    date_to:   str
    reason:    str


@router.post("/parent/children/{student_id}/leave")
def submit_leave(student_id: int, body: LeaveRequest, user: Usr):
    _require_role(user, "parent_portal")
    _verify_child(user, student_id)
    if not body.reason.strip():
        raise HTTPException(400, "Reason is required")
    row_id = execute(
        """INSERT INTO leave_requests
           (student_id, submitted_by, date_from, date_to, reason)
           VALUES (?,?,?,?,?)""",
        (student_id, user["id"], body.date_from, body.date_to, body.reason.strip()),
    )
    return {"id": row_id}


@router.get("/parent/children/{student_id}/leave")
def list_leave(student_id: int, user: Usr):
    _require_role(user, "parent_portal")
    _verify_child(user, student_id)
    rows = fetch_all(
        """SELECT lr.id, lr.date_from, lr.date_to, lr.reason,
                  lr.status, lr.review_note, lr.reviewed_at,
                  u.full_name AS reviewed_by_name
           FROM leave_requests lr
           LEFT JOIN users u ON u.id = lr.reviewed_by
           WHERE lr.student_id = ? AND lr.submitted_by = ?
           ORDER BY lr.created_at DESC""",
        (student_id, user["id"]),
    )
    return [dict(r) for r in rows]


# ── Admin: portal account management ─────────────────────────────────────────

@router.get("/admin/accounts")
def list_portal_accounts(user: Usr):
    require_permission(user, "settings.view")
    students = fetch_all(
        """SELECT spa.user_id, u.username, u.full_name,
                  s.id AS student_id, s.first_name || ' ' || s.last_name AS student_name,
                  s.admission_no
           FROM student_portal_accounts spa
           JOIN users u    ON u.id  = spa.user_id
           JOIN students s ON s.id  = spa.student_id
           ORDER BY s.last_name""",
        (),
    )
    parents = fetch_all(
        """SELECT ppa.id, ppa.user_id, u.username, u.full_name,
                  ppa.student_id, ppa.relation,
                  s.first_name || ' ' || s.last_name AS student_name,
                  s.admission_no
           FROM parent_portal_accounts ppa
           JOIN users u    ON u.id  = ppa.user_id
           JOIN students s ON s.id  = ppa.student_id
           ORDER BY s.last_name""",
        (),
    )
    return {
        "student_accounts": [dict(r) for r in students],
        "parent_accounts":  [dict(r) for r in parents],
    }


class CreateStudentAccount(BaseModel):
    student_id: int
    username:   str
    password:   str
    full_name:  str


class CreateParentAccount(BaseModel):
    student_id: int
    username:   str
    password:   str
    full_name:  str
    relation:   str = "Parent"


@router.post("/admin/accounts/student", status_code=201)
def create_student_account(body: CreateStudentAccount, user: Usr):
    require_permission(user, "settings.users")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    existing = fetch_one("SELECT id FROM users WHERE username=?", (body.username,))
    if existing:
        raise HTTPException(409, "Username already taken")
    import bcrypt
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt(12)).decode()
    school_id = user.get("school_id")
    user_id = execute(
        """INSERT INTO users (username, full_name, password_hash, salt, pw_scheme, role, school_id, is_active)
           VALUES (?,?,?,'','bcrypt','student_portal',?,1)""",
        (body.username, body.full_name, pw_hash, school_id),
    )
    existing_link = fetch_one(
        "SELECT user_id FROM student_portal_accounts WHERE student_id=?",
        (body.student_id,),
    )
    if existing_link:
        raise HTTPException(409, "Student already has a portal account")
    execute(
        "INSERT INTO student_portal_accounts (user_id, student_id) VALUES (?,?)",
        (user_id, body.student_id),
    )
    return {"user_id": user_id}


@router.post("/admin/accounts/parent", status_code=201)
def create_parent_account(body: CreateParentAccount, user: Usr):
    require_permission(user, "settings.users")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    # Parent accounts can be shared — check if username exists first
    existing_user = fetch_one("SELECT id FROM users WHERE username=?", (body.username,))
    if existing_user:
        # Reuse existing user, just add the child link
        parent_user_id = existing_user["id"]
    else:
        import bcrypt
        pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt(12)).decode()
        school_id = user.get("school_id")
        parent_user_id = execute(
            """INSERT INTO users (username, full_name, password_hash, salt, pw_scheme, role, school_id, is_active)
               VALUES (?,?,?,'','bcrypt','parent_portal',?,1)""",
            (body.username, body.full_name, pw_hash, school_id),
        )
    duplicate = fetch_one(
        "SELECT id FROM parent_portal_accounts WHERE user_id=? AND student_id=?",
        (parent_user_id, body.student_id),
    )
    if duplicate:
        raise HTTPException(409, "This parent is already linked to this student")
    execute(
        "INSERT INTO parent_portal_accounts (user_id, student_id, relation) VALUES (?,?,?)",
        (parent_user_id, body.student_id, body.relation),
    )
    return {"user_id": parent_user_id}


@router.delete("/admin/accounts/{account_user_id}")
def delete_portal_account(account_user_id: int, user: Usr):
    require_permission(user, "settings.users")
    row = fetch_one(
        "SELECT role FROM users WHERE id=?", (account_user_id,)
    )
    if not row or row["role"] not in ("student_portal", "parent_portal"):
        raise HTTPException(404, "Portal account not found")
    execute("DELETE FROM users WHERE id=?", (account_user_id,))
    return {"ok": True}
