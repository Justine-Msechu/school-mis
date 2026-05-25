from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["welfare"])
Usr = Annotated[dict, Depends(require_auth)]

_CATEGORIES = ("orphan", "half_orphan", "sponsored", "vulnerable")
_SUPPORT_TYPES = ("full_fees", "partial", "non_financial")


@router.get("/records")
def get_records(
    user: Usr,
    student_id: int  = Query(None),
    category:   str  = Query(None),
    verified:   bool = Query(None),
    limit:      int  = Query(50),
):
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("wr.student_id=?"); params.append(student_id)
    if category:
        where.append("wr.category=?"); params.append(category)
    if verified is not None:
        where.append("wr.verified=?"); params.append(1 if verified else 0)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT wr.*, (s.first_name || ' ' || s.last_name) AS student_name, s.admission_no
            FROM welfare_records wr
            JOIN students s ON s.id = wr.student_id
            WHERE {' AND '.join(where)}
            ORDER BY wr.created_at DESC LIMIT ?""",
        params,
    )
    return [dict(r) for r in rows]


class WelfarePayload(BaseModel):
    student_id:   int
    category:     str    # orphan | half_orphan | sponsored | vulnerable
    support_type: str = "non_financial"   # full_fees | partial | non_financial
    sponsor_name: str = ""
    sponsor_org:  str = ""
    notes:        str = ""


def _sync_student_category(student_id: int, welfare_category: str):
    mapped = "orphan" if welfare_category in ("orphan", "half_orphan") else \
             "sponsored" if welfare_category == "sponsored" else "regular"
    execute("UPDATE students SET student_category=? WHERE id=?", (mapped, student_id))


@router.post("/records")
def register_record(body: WelfarePayload, user: Usr):
    if body.category not in _CATEGORIES:
        raise HTTPException(400, f"category must be one of {_CATEGORIES}")
    student = fetch_one("SELECT id FROM students WHERE id=? AND deleted_at IS NULL", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    existing = fetch_one(
        "SELECT id FROM welfare_records WHERE student_id=? AND is_current=1",
        (body.student_id,),
    )
    if existing:
        # Supersede old record and create new history entry
        execute(
            "UPDATE welfare_records SET is_current=0, superseded_at=datetime('now') WHERE id=?",
            (existing["id"],),
        )
    wr_id = execute(
        """INSERT INTO welfare_records
           (student_id, category, is_current, support_type, sponsor_name, sponsor_org, notes)
           VALUES (?,?,1,?,?,?,?)""",
        (body.student_id, body.category, body.support_type,
         body.sponsor_name, body.sponsor_org, body.notes),
    )
    _sync_student_category(body.student_id, body.category)
    return {"id": wr_id, "ok": True}


@router.post("/records/{wr_id}/verify")
def verify_record(wr_id: int, user: Usr):
    row = fetch_one("SELECT id FROM welfare_records WHERE id=?", (wr_id,))
    if not row:
        raise HTTPException(404, "Welfare record not found")
    execute(
        "UPDATE welfare_records SET verified=1, verified_by=?, verified_date=date('now') WHERE id=?",
        (user.get("id"), wr_id),
    )
    return {"ok": True}


@router.get("/categories")
def get_categories(user: Usr):
    return list(_CATEGORIES)
