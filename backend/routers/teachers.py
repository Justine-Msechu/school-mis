from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["teachers"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("")
def list_teachers(user: Usr, search: str = Query("")):
    params: list = []
    where = ""
    if search:
        where = "WHERE (t.first_name || ' ' || t.last_name LIKE ? OR t.employee_no LIKE ? OR t.subject_specialization LIKE ?)"
        params = [f"%{search}%", f"%{search}%", f"%{search}%"]
    rows = fetch_all(
        f"""SELECT t.*, u.username, u.role, u.is_active as user_active
            FROM teachers t
            LEFT JOIN users u ON u.teacher_id = t.id
            {where}
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
    employee_no:            str = ""
    gender:                 str = "M"
    date_of_birth:          str | None = None
    phone:                  str | None = None
    email:                  str | None = None
    subject_specialization: str | None = None
    qualification:          str | None = None
    joining_date:           str | None = None


@router.post("")
def create_teacher(body: TeacherPayload, user: Usr):
    row_id = execute(
        """INSERT INTO teachers (first_name, last_name, employee_no, gender, date_of_birth,
           phone, email, subject_specialization, qualification, joining_date)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (body.first_name, body.last_name, body.employee_no, body.gender, body.date_of_birth,
         body.phone, body.email, body.subject_specialization, body.qualification, body.joining_date),
    )
    return dict(fetch_one("SELECT * FROM teachers WHERE id=?", (row_id,)))


@router.put("/{teacher_id}")
def update_teacher(teacher_id: int, body: TeacherPayload, user: Usr):
    execute(
        """UPDATE teachers SET first_name=?, last_name=?, employee_no=?, gender=?,
           date_of_birth=?, phone=?, email=?, subject_specialization=?, qualification=?, joining_date=?
           WHERE id=?""",
        (body.first_name, body.last_name, body.employee_no, body.gender, body.date_of_birth,
         body.phone, body.email, body.subject_specialization, body.qualification, body.joining_date,
         teacher_id),
    )
    return dict(fetch_one("SELECT * FROM teachers WHERE id=?", (teacher_id,)))


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
