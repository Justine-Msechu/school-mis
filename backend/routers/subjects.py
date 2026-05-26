from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database.db import fetch_all, fetch_one, execute
from backend.deps import require_auth

router = APIRouter(tags=["subjects"])
Usr = dict


def _ensure_is_active():
    """Add is_active column to subjects if it doesn't exist yet."""
    try:
        execute("ALTER TABLE subjects ADD COLUMN is_active INTEGER DEFAULT 1")
        execute("UPDATE subjects SET is_active=1 WHERE is_active IS NULL")
    except Exception:
        pass


@router.get("")
def list_subjects(include_inactive: bool = False, user: Usr = Depends(require_auth)):
    _ensure_is_active()
    if include_inactive:
        rows = fetch_all("SELECT * FROM subjects ORDER BY name")
    else:
        rows = fetch_all("SELECT * FROM subjects WHERE is_active=1 ORDER BY name")
    return [dict(r) for r in rows]


class SubjectPayload(BaseModel):
    name: str
    code: Optional[str] = None
    grade_level: Optional[int] = None
    subject_type: Optional[str] = "compulsory"
    credit_hours: Optional[int] = 1


@router.post("")
def create_subject(body: SubjectPayload, user: Usr = Depends(require_auth)):
    _ensure_is_active()
    if not body.name.strip():
        raise HTTPException(400, "Subject name is required.")
    if body.code:
        existing = fetch_one("SELECT id FROM subjects WHERE code=?", (body.code.strip().upper(),))
        if existing:
            raise HTTPException(400, "A subject with that code already exists.")
    sid = execute(
        """INSERT INTO subjects (name, code, grade_level, subject_type, credit_hours, is_active)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (
            body.name.strip(),
            body.code.strip().upper() if body.code else None,
            body.grade_level,
            body.subject_type or "compulsory",
            body.credit_hours or 1,
        ),
    )
    return fetch_one("SELECT * FROM subjects WHERE id=?", (sid,))


@router.put("/{sid}")
def update_subject(sid: int, body: SubjectPayload, user: Usr = Depends(require_auth)):
    if not fetch_one("SELECT id FROM subjects WHERE id=?", (sid,)):
        raise HTTPException(404, "Subject not found.")
    if not body.name.strip():
        raise HTTPException(400, "Subject name is required.")
    if body.code:
        conflict = fetch_one(
            "SELECT id FROM subjects WHERE code=? AND id!=?",
            (body.code.strip().upper(), sid),
        )
        if conflict:
            raise HTTPException(400, "A subject with that code already exists.")
    execute(
        """UPDATE subjects SET name=?, code=?, grade_level=?, subject_type=?, credit_hours=?
           WHERE id=?""",
        (
            body.name.strip(),
            body.code.strip().upper() if body.code else None,
            body.grade_level,
            body.subject_type or "compulsory",
            body.credit_hours or 1,
            sid,
        ),
    )
    return fetch_one("SELECT * FROM subjects WHERE id=?", (sid,))


@router.patch("/{sid}/toggle")
def toggle_subject(sid: int, user: Usr = Depends(require_auth)):
    row = fetch_one("SELECT id, is_active FROM subjects WHERE id=?", (sid,))
    if not row:
        raise HTTPException(404, "Subject not found.")
    new_state = 0 if row["is_active"] else 1
    execute("UPDATE subjects SET is_active=? WHERE id=?", (new_state, sid))
    return {"id": sid, "is_active": new_state}
