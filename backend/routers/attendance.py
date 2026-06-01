from typing import Annotated
from datetime import date as Date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from backend.deps import require_auth
from backend.core.events import event_bus, Events
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["attendance"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/sheet")
def get_sheet(user: Usr, class_id: int, date: str = Query(default="")):
    d = date or Date.today().isoformat()
    students = fetch_all(
        "SELECT id, first_name, last_name, admission_no FROM students WHERE class_id=? AND is_active=1 ORDER BY last_name, first_name",
        (class_id,),
    )
    existing = fetch_all(
        "SELECT student_id, status, notes FROM attendance WHERE class_id=? AND date=?",
        (class_id, d),
    )
    att_map = {r["student_id"]: dict(r) for r in existing}
    return {
        "date": d,
        "class_id": class_id,
        "rows": [
            {
                **dict(s),
                "status": (att_map.get(s["id"], {}).get("status", "") or "").lower(),
                "notes":  att_map.get(s["id"], {}).get("notes", "") or "",
            }
            for s in students
        ],
    }


class AttendanceEntry(BaseModel):
    student_id: int
    status:     str   # Present | Absent | Late | Excused
    notes:      str = ""


class SaveAttendanceBody(BaseModel):
    class_id: int
    date:     str
    entries:  list[AttendanceEntry]


@router.post("/save")
def save_attendance(body: SaveAttendanceBody, user: Usr):
    for e in body.entries:
        status = e.status.capitalize()  # normalize: present→Present, ABSENT→Absent
        existing = fetch_one(
            "SELECT id FROM attendance WHERE student_id=? AND date=?",
            (e.student_id, body.date),
        )
        if existing:
            execute(
                "UPDATE attendance SET status=?, notes=?, class_id=?, recorded_by=? WHERE id=?",
                (status, e.notes, body.class_id, user.get("id"), existing["id"]),
            )
        else:
            execute(
                "INSERT INTO attendance (student_id, class_id, date, status, notes, recorded_by) VALUES (?,?,?,?,?,?)",
                (e.student_id, body.class_id, body.date, status, e.notes, user.get("id")),
            )
    return {"saved": len(body.entries)}


@router.get("/summary")
def get_summary(user: Usr, class_id: int = Query(None), days: int = Query(30)):
    import datetime
    # Compute cutoff as a text string so TEXT column comparison works in both
    # SQLite and PostgreSQL (avoids TEXT >= DATE type mismatch in PG).
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    where = "WHERE a.date >= ?"
    params: list = [cutoff]
    if class_id:
        where += " AND a.class_id=?"
        params.append(class_id)
    rows = fetch_all(
        f"""SELECT a.date,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
                   SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) as absent,
                   SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) as late,
                   COUNT(*) as total
            FROM attendance a {where}
            GROUP BY a.date ORDER BY a.date DESC""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/leave-requests")
def get_leave_requests(user: Usr, status: str = Query("pending")):
    rows = fetch_all(
        """SELECT lr.*, s.first_name || ' ' || s.last_name as student_name, s.admission_no
           FROM leave_requests lr
           JOIN students s ON s.id = lr.student_id
           WHERE lr.status=?
           ORDER BY lr.created_at DESC""",
        (status,),
    )
    return [dict(r) for r in rows]


class LeaveReviewBody(BaseModel):
    status: str   # approved | rejected
    note:   str = ""


@router.post("/leave-requests/{lr_id}/review")
def review_leave(lr_id: int, body: LeaveReviewBody, user: Usr):
    lr = fetch_one("SELECT * FROM leave_requests WHERE id=?", (lr_id,))
    execute(
        "UPDATE leave_requests SET status=?, review_note=?, reviewed_by=? WHERE id=?",
        (body.status, body.note, user.get("id"), lr_id),
    )
    if lr:
        event_bus.emit(Events.LEAVE_REVIEWED, {
            "student_id":   lr["student_id"],
            "submitted_by": lr["submitted_by"],
            "approved":     body.status == "approved",
            "review_note":  body.note,
            "date_from":    lr["date_from"],
            "date_to":      lr["date_to"],
        }, actor_id=user.get("id"))
    return {"ok": True}
