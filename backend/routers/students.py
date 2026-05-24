from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["students"])

Usr = Annotated[dict, Depends(require_auth)]


@router.get("")
def list_students(
    user: Usr,
    search:    str  = Query(""),
    class_id:  int  = Query(None),
    is_active: bool = Query(True),
    page:      int  = Query(1, ge=1),
    per_page:  int  = Query(30, ge=1, le=100),
):
    where = ["s.is_active = ?"]
    params: list = [1 if is_active else 0]

    if search:
        where.append("(s.first_name || ' ' || s.last_name LIKE ? OR s.admission_no LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if class_id:
        where.append("s.class_id = ?")
        params.append(class_id)

    where_clause = " AND ".join(where)
    total_row = fetch_one(f"SELECT COUNT(*) as n FROM students s WHERE {where_clause}", params)
    total = dict(total_row).get("n", 0) if total_row else 0

    offset = (page - 1) * per_page
    rows = fetch_all(
        f"""SELECT s.*, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE {where_clause}
            ORDER BY s.last_name, s.first_name
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    )
    import math
    return {
        "items":    [dict(r) for r in rows],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    math.ceil(total / per_page) if total else 1,
    }


class StudentPayload(BaseModel):
    first_name:     str
    last_name:      str
    admission_no:   str
    gender:         str = "M"
    class_id:       int | None = None
    date_of_birth:  str | None = None
    guardian_name:  str | None = None
    guardian_phone: str | None = None


@router.post("")
def create_student(body: StudentPayload, user: Usr):
    row_id = execute(
        """INSERT INTO students (first_name, last_name, admission_no, gender, class_id,
           date_of_birth, guardian_name, guardian_phone, is_active)
           VALUES (?,?,?,?,?,?,?,?,1)""",
        (body.first_name, body.last_name, body.admission_no, body.gender, body.class_id,
         body.date_of_birth, body.guardian_name, body.guardian_phone),
    )
    row = fetch_one("SELECT * FROM students WHERE id=?", (row_id,))
    return dict(row)


@router.put("/{student_id}")
def update_student(student_id: int, body: StudentPayload, user: Usr):
    execute(
        """UPDATE students SET first_name=?, last_name=?, admission_no=?, gender=?,
           class_id=?, date_of_birth=?, guardian_name=?, guardian_phone=? WHERE id=?""",
        (body.first_name, body.last_name, body.admission_no, body.gender, body.class_id,
         body.date_of_birth, body.guardian_name, body.guardian_phone, student_id),
    )
    row = fetch_one("SELECT * FROM students WHERE id=?", (student_id,))
    return dict(row)


@router.delete("/{student_id}")
def deactivate_student(student_id: int, user: Usr):
    execute("UPDATE students SET is_active=0 WHERE id=?", (student_id,))
    return {"ok": True}
