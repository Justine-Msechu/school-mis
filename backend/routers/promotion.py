from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["promotion"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/class-status")
def class_status(class_id: int, academic_year_id: int, user: Usr):
    rows = fetch_all(
        """SELECT s.id,
                  s.first_name,
                  s.last_name,
                  s.admission_no,
                  CASE WHEN sp.action IS NOT NULL THEN 1 ELSE 0 END AS promoted,
                  sp.to_class_id AS promoted_to_class_id
           FROM students s
           JOIN enrollments e ON e.student_id=s.id
                             AND e.class_id=? AND e.academic_year_id=?
           LEFT JOIN student_promotions sp ON sp.student_id=s.id
                                          AND sp.academic_year_id=?
           WHERE s.deleted_at IS NULL
           ORDER BY s.first_name, s.last_name""",
        (class_id, academic_year_id, academic_year_id),
    )
    return [dict(r) for r in rows]


class PromoteBatchBody(BaseModel):
    class_id:         int
    academic_year_id: int
    to_class_id:      int
    student_ids:      list[int]
    action:           str = "promote"   # promote | hold_back | graduate
    notes:            str = ""


@router.post("/promote")
def promote_batch(body: PromoteBatchBody, user: Usr):
    if body.action not in ("promote", "hold_back", "graduate"):
        raise HTTPException(400, "action must be promote, hold_back, or graduate")

    # Find next academic year for new enrollment
    next_year = fetch_one(
        "SELECT id FROM academic_years WHERE start_date > (SELECT start_date FROM academic_years WHERE id=?) ORDER BY start_date LIMIT 1",
        (body.academic_year_id,),
    )
    next_year_id = next_year["id"] if next_year else None

    promoted = 0
    for sid in body.student_ids:
        # Upsert promotion record
        existing = fetch_one(
            "SELECT id FROM student_promotions WHERE student_id=? AND academic_year_id=?",
            (sid, body.academic_year_id),
        )
        if existing:
            execute(
                "UPDATE student_promotions SET action=?, to_class_id=?, notes=?, promoted_by=? WHERE id=?",
                (body.action, body.to_class_id, body.notes, user.get("id"), existing["id"]),
            )
        else:
            execute(
                """INSERT INTO student_promotions
                   (student_id, from_class_id, to_class_id, academic_year_id, action, notes, promoted_by)
                   VALUES (?,?,?,?,?,?,?)""",
                (sid, body.class_id, body.to_class_id, body.academic_year_id,
                 body.action, body.notes, user.get("id")),
            )

        # Mark old enrollment as graduated/held-back
        old_status = "graduated" if body.action == "graduate" else "transferred"
        execute(
            """UPDATE enrollments SET status=?, exit_date=date('now'), updated_at=datetime('now')
               WHERE student_id=? AND academic_year_id=? AND status='active'""",
            (old_status, sid, body.academic_year_id),
        )

        if body.action in ("promote", "hold_back") and next_year_id:
            target_class = body.to_class_id if body.action == "promote" else body.class_id
            # Create enrollment in next year (idempotent)
            prev = fetch_one(
                "SELECT id FROM enrollments WHERE student_id=? AND academic_year_id=?",
                (sid, next_year_id),
            )
            if prev:
                execute(
                    """UPDATE enrollments SET class_id=?, status='active', exit_date=NULL,
                       updated_at=datetime('now') WHERE id=?""",
                    (target_class, prev["id"]),
                )
            else:
                execute(
                    """INSERT INTO enrollments (student_id, class_id, academic_year_id, created_by)
                       VALUES (?,?,?,?)""",
                    (sid, target_class, next_year_id, user.get("id")),
                )
            # Sync students.class_id to the new class
            execute("UPDATE students SET class_id=? WHERE id=?", (target_class, sid))

        promoted += 1

    return {"promoted": promoted, "total": len(body.student_ids), "next_year_id": next_year_id}


@router.get("/history")
def get_history(user: Usr, student_id: int = Query(None)):
    where = "WHERE 1=1"
    params: list = []
    if student_id:
        where += " AND sp.student_id=?"
        params.append(student_id)
    rows = fetch_all(
        f"""SELECT sp.*,
                   (s.first_name || ' ' || s.last_name) AS student_name, s.admission_no,
                   c1.name AS from_class_name, c2.name AS to_class_name,
                   ay.label AS year_label
            FROM student_promotions sp
            JOIN students s ON s.id=sp.student_id
            LEFT JOIN classes c1 ON c1.id=sp.from_class_id
            LEFT JOIN classes c2 ON c2.id=sp.to_class_id
            LEFT JOIN academic_years ay ON ay.id=sp.academic_year_id
            {where}
            ORDER BY sp.created_at DESC""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/academic-years")
def get_academic_years(user: Usr):
    rows = fetch_all("SELECT * FROM academic_years ORDER BY start_date DESC")
    return [dict(r) for r in rows]
