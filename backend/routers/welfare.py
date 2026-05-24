from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.welfare_service import welfare_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all

router = APIRouter(tags=["welfare"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/records")
def get_records(
    user: Usr,
    student_id:  int  = Query(None),
    category:    str  = Query(None),
    verified:    bool = Query(None),
    limit:       int  = Query(50),
):
    hydrate_session(user)
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("wr.student_id=?"); params.append(student_id)
    if category:
        where.append("wr.category=?");  params.append(category)
    if verified is not None:
        where.append("wr.is_verified=?"); params.append(1 if verified else 0)
    rows = fetch_all(
        f"""SELECT wr.*, s.first_name || ' ' || s.last_name as student_name, s.admission_no
            FROM welfare_records wr
            JOIN students s ON s.id=wr.student_id
            WHERE {' AND '.join(where)}
            ORDER BY wr.incident_date DESC LIMIT ?""",
        params + [limit],
    )
    return [dict(r) for r in rows]


class WelfarePayload(BaseModel):
    student_id:    int
    category:      str           # disciplinary | counseling | achievement | support
    incident_date: str
    description:   str
    action_taken:  str = ""
    follow_up:     str = ""


@router.post("/records")
def register_record(body: WelfarePayload, user: Usr):
    hydrate_session(user)
    try:
        wr_id = welfare_service.register(body.model_dump())
        return {"id": wr_id, "ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.post("/records/{wr_id}/verify")
def verify_record(wr_id: int, user: Usr):
    hydrate_session(user)
    try:
        welfare_service.verify(wr_id)
        return {"ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.get("/categories")
def get_categories(user: Usr):
    rows = fetch_all("SELECT DISTINCT category FROM welfare_records WHERE category IS NOT NULL ORDER BY category")
    return [r["category"] for r in rows]
