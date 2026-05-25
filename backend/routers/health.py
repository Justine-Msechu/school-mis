from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["health"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/visits")
def get_visits(
    user: Usr,
    student_id: int = Query(None),
    date_from:  str = Query(None),
    date_to:    str = Query(None),
    limit:      int = Query(50),
):
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("hv.student_id=?"); params.append(student_id)
    if date_from:
        where.append("hv.visit_date>=?"); params.append(date_from)
    if date_to:
        where.append("hv.visit_date<=?"); params.append(date_to)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT hv.*, (s.first_name || ' ' || s.last_name) AS student_name, s.admission_no
            FROM health_visits hv
            JOIN students s ON s.id = hv.student_id
            WHERE {' AND '.join(where)}
            ORDER BY hv.visit_date DESC, hv.created_at DESC
            LIMIT ?""",
        params,
    )
    return [dict(r) for r in rows]


class VisitPayload(BaseModel):
    student_id:               int
    visit_date:               str
    symptoms:                 str = ""
    diagnosis:                str = ""
    treatment:                str = ""
    action_taken:             str = "treated"   # treated|referred|sent_home|rest|other
    referred_to:              str = ""
    parent_notified:          bool = False
    parent_notification_note: str = ""
    nurse_name:               str = ""


@router.post("/visits")
def record_visit(body: VisitPayload, user: Usr):
    student = fetch_one("SELECT id FROM students WHERE id=? AND deleted_at IS NULL", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    visit_id = execute(
        """INSERT INTO health_visits
           (student_id, visit_date, symptoms, diagnosis, treatment,
            action_taken, referred_to, parent_notified, parent_notification_note,
            nurse_name, created_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (body.student_id, body.visit_date, body.symptoms, body.diagnosis,
         body.treatment, body.action_taken, body.referred_to,
         1 if body.parent_notified else 0, body.parent_notification_note,
         body.nurse_name, user.get("id")),
    )
    return {"id": visit_id, "ok": True}


@router.get("/visits/{visit_id}")
def get_visit(visit_id: int, user: Usr):
    row = fetch_one(
        """SELECT hv.*, (s.first_name || ' ' || s.last_name) AS student_name
           FROM health_visits hv
           JOIN students s ON s.id = hv.student_id
           WHERE hv.id=?""",
        (visit_id,),
    )
    if not row:
        raise HTTPException(404, "Visit not found")
    return dict(row)


@router.get("/student/{student_id}/history")
def student_history(student_id: int, user: Usr):
    rows = fetch_all(
        "SELECT * FROM health_visits WHERE student_id=? ORDER BY visit_date DESC",
        (student_id,),
    )
    return [dict(r) for r in rows]


@router.get("/stats")
def get_stats(user: Usr):
    total      = dict(fetch_one("SELECT COUNT(*) as n FROM health_visits") or {}).get("n", 0)
    this_month = dict(fetch_one(
        "SELECT COUNT(*) as n FROM health_visits WHERE strftime('%Y-%m', visit_date)=strftime('%Y-%m','now')"
    ) or {}).get("n", 0)
    referred   = dict(fetch_one(
        "SELECT COUNT(*) as n FROM health_visits WHERE action_taken='referred'"
    ) or {}).get("n", 0)
    return {"total_visits": total, "this_month": this_month, "referred": referred}
