from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["classes"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("")
def list_classes(user: Usr):
    rows = fetch_all(
        """SELECT c.id, c.name, c.grade_level, c.capacity, c.room,
                  t.first_name || ' ' || t.last_name AS teacher_name,
                  c.teacher_id,
                  COUNT(s.id) AS student_count
           FROM classes c
           LEFT JOIN teachers t ON t.id = c.teacher_id
           LEFT JOIN students s ON s.class_id = c.id AND s.is_active = 1
           GROUP BY c.id
           ORDER BY c.grade_level, c.name"""
    )
    return [dict(r) for r in rows]


class ClassPayload(BaseModel):
    name:        str
    grade_level: int | None = None
    capacity:    int | None = None
    room:        str | None = None
    teacher_id:  int | None = None


@router.post("")
def create_class(body: ClassPayload, user: Usr):
    row_id = execute(
        "INSERT INTO classes (name, grade_level, capacity, room, teacher_id) VALUES (?,?,?,?,?)",
        (body.name, body.grade_level, body.capacity, body.room, body.teacher_id),
    )
    row = fetch_one(
        """SELECT c.id, c.name, c.grade_level, c.capacity, c.room, c.teacher_id,
                  t.first_name || ' ' || t.last_name AS teacher_name,
                  0 AS student_count
           FROM classes c LEFT JOIN teachers t ON t.id=c.teacher_id
           WHERE c.id=?""",
        (row_id,),
    )
    return dict(row)


@router.put("/{class_id}")
def update_class(class_id: int, body: ClassPayload, user: Usr):
    existing = fetch_one("SELECT id FROM classes WHERE id=?", (class_id,))
    if not existing:
        raise HTTPException(404, "Class not found")
    execute(
        "UPDATE classes SET name=?, grade_level=?, capacity=?, room=?, teacher_id=? WHERE id=?",
        (body.name, body.grade_level, body.capacity, body.room, body.teacher_id, class_id),
    )
    row = fetch_one(
        """SELECT c.id, c.name, c.grade_level, c.capacity, c.room, c.teacher_id,
                  t.first_name || ' ' || t.last_name AS teacher_name,
                  COUNT(s.id) AS student_count
           FROM classes c
           LEFT JOIN teachers t ON t.id=c.teacher_id
           LEFT JOIN students s ON s.class_id=c.id AND s.is_active=1
           WHERE c.id=?""",
        (class_id,),
    )
    return dict(row)


@router.get("/{class_id}/students")
def class_students(class_id: int, user: Usr):
    rows = fetch_all(
        """SELECT id, first_name, last_name, admission_no, gender
           FROM students WHERE class_id=? AND is_active=1
           ORDER BY last_name, first_name""",
        (class_id,),
    )
    return [dict(r) for r in rows]
