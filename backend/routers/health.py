from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.health_service import health_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all

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
    hydrate_session(user)
    try:
        visits = health_service.get_visits(
            student_id=student_id, date_from=date_from, date_to=date_to, limit=limit
        )
        return [dict(v) for v in visits]
    except (ServiceError, PolicyViolation):
        return []


class VisitPayload(BaseModel):
    student_id:   int
    visit_date:   str
    complaint:    str = ""
    diagnosis:    str = ""
    treatment:    str = ""
    prescription: str = ""
    referred:     bool = False
    follow_up:    str | None = None


@router.post("/visits")
def record_visit(body: VisitPayload, user: Usr):
    hydrate_session(user)
    try:
        visit_id = health_service.record_visit(body.model_dump())
        return {"id": visit_id, "ok": True}
    except (ServiceError, PolicyViolation) as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.get("/visits/{visit_id}")
def get_visit(visit_id: int, user: Usr):
    hydrate_session(user)
    try:
        return dict(health_service.get_visit(visit_id))
    except (ServiceError, PolicyViolation) as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.get("/student/{student_id}/history")
def student_history(student_id: int, user: Usr):
    hydrate_session(user)
    try:
        return [dict(v) for v in health_service.get_student_history(student_id)]
    except (ServiceError, PolicyViolation):
        return []


@router.get("/stats")
def get_stats(user: Usr):
    hydrate_session(user)
    try:
        return health_service.get_stats()
    except Exception:
        return {}
