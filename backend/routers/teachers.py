from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from backend.core.id_generator import next_employee_no
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["teachers"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/next-employee-no")
def preview_employee_no(user: Usr):
    """Return what the next auto-generated employee number will look like."""
    from database.db import fetch_one as _fo
    row = _fo("SELECT value FROM school_config WHERE key='teacher_emp_seq'")
    import datetime
    seq = (int(row["value"]) if row else 0) + 1
    year = datetime.date.today().year
    return {"employee_no": f"EMP/{year}/{seq:04d}"}


def _audit(user_id: int, action: str, record_id: int, detail: str):
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user_id, action, "teachers", record_id, detail),
        )
    except Exception:
        pass


@router.get("")
def list_teachers(user: Usr, search: str = Query(""), include_inactive: bool = Query(False)):
    where = []
    params: list = []
    if not include_inactive:
        # Exclude soft-deleted and deactivated teachers from the default list
        where.append("t.deleted_at IS NULL")
        where.append("t.is_active = 1")
    if search:
        where.append("(t.first_name || ' ' || t.last_name LIKE ? OR t.employee_no LIKE ? OR t.subject_specialization LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    where_clause = " AND ".join(where) if where else "1=1"
    rows = fetch_all(
        f"""SELECT t.*, u.id as user_id, u.username, u.role, u.is_active as user_active
            FROM teachers t
            LEFT JOIN users u ON u.teacher_id = t.id
            WHERE {where_clause}
            ORDER BY t.last_name, t.first_name""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/{teacher_id}")
def get_teacher(teacher_id: int, user: Usr):
    row = fetch_one("SELECT * FROM teachers WHERE id=?", (teacher_id,))
    if not row:
        raise HTTPException(404, "Teacher not found")
    return dict(row)


class TeacherPayload(BaseModel):
    first_name:             str
    last_name:              str
    employee_no:            str | None = None   # auto-generated if omitted
    gender:                 str = "Male"
    date_of_birth:          str | None = None
    phone:                  str | None = None
    email:                  str | None = None
    subject_specialization: str | None = None
    qualification:          str | None = None
    joining_date:           str | None = None


@router.post("")
def create_teacher(body: TeacherPayload, user: Usr):
    emp_no = (body.employee_no or "").strip() or next_employee_no()
    existing = fetch_one("SELECT id FROM teachers WHERE employee_no=?", (emp_no,))
    if existing:
        raise HTTPException(400, f"Employee number '{emp_no}' already exists")
    row_id = execute(
        """INSERT INTO teachers (first_name, last_name, employee_no, gender, date_of_birth,
           phone, email, subject_specialization, qualification, joining_date)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (body.first_name, body.last_name, emp_no, body.gender, body.date_of_birth,
         body.phone, body.email, body.subject_specialization, body.qualification, body.joining_date),
    )
    _audit(user["id"], "teacher_create", row_id, f"Created teacher {body.first_name} {body.last_name} ({emp_no})")
    return dict(fetch_one("SELECT * FROM teachers WHERE id=?", (row_id,)))


@router.put("/{teacher_id}")
def update_teacher(teacher_id: int, body: TeacherPayload, user: Usr):
    before = fetch_one("SELECT * FROM teachers WHERE id=?", (teacher_id,))
    if not before:
        raise HTTPException(404, "Teacher not found")
    emp_no = (body.employee_no or "").strip() or before["employee_no"]
    dup = fetch_one(
        "SELECT id FROM teachers WHERE employee_no=? AND id != ?",
        (emp_no, teacher_id),
    )
    if dup:
        raise HTTPException(400, f"Employee number '{emp_no}' already used by another teacher")
    execute(
        """UPDATE teachers SET first_name=?, last_name=?, employee_no=?, gender=?,
           date_of_birth=?, phone=?, email=?, subject_specialization=?, qualification=?, joining_date=?
           WHERE id=?""",
        (body.first_name, body.last_name, emp_no, body.gender, body.date_of_birth,
         body.phone, body.email, body.subject_specialization, body.qualification, body.joining_date,
         teacher_id),
    )
    _audit(user["id"], "teacher_update", teacher_id, f"Updated teacher {body.first_name} {body.last_name}")
    return dict(fetch_one("SELECT * FROM teachers WHERE id=?", (teacher_id,)))


@router.delete("/{teacher_id}")
def deactivate_teacher(teacher_id: int, user: Usr):
    row = fetch_one("SELECT id, first_name, last_name FROM teachers WHERE id=? AND deleted_at IS NULL", (teacher_id,))
    if not row:
        raise HTTPException(404, "Teacher not found")
    execute(
        "UPDATE teachers SET is_active=0, deleted_at=datetime('now') WHERE id=?",
        (teacher_id,),
    )
    _audit(user["id"], "teacher_delete", teacher_id,
           f"Deactivated {row['first_name']} {row['last_name']}")
    return {"ok": True}


@router.get("/{teacher_id}/subjects")
def get_teacher_subjects(teacher_id: int, user: Usr):
    rows = fetch_all(
        """SELECT ts.*, c.name as class_name, s.name as subject_name
           FROM teacher_subjects ts
           JOIN classes c ON c.id = ts.class_id
           JOIN subjects s ON s.id = ts.subject_id
           WHERE ts.teacher_id=?""",
        (teacher_id,),
    )
    return [dict(r) for r in rows]
