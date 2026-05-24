from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.promotion_service import promotion_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all, fetch_one

router = APIRouter(tags=["promotion"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/class-status")
def class_status(class_id: int, academic_year_id: int, user: Usr):
    hydrate_session(user)
    try:
        rows = promotion_service.get_class_students_with_status(class_id, academic_year_id)
        return [dict(r) for r in rows]
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class PromoteBatchBody(BaseModel):
    class_id:          int
    academic_year_id:  int
    to_class_id:       int
    student_ids:       list[int]


@router.post("/promote")
def promote_batch(body: PromoteBatchBody, user: Usr):
    hydrate_session(user)
    try:
        result = promotion_service.promote_batch(
            body.class_id, body.academic_year_id,
            body.to_class_id, body.student_ids
        )
        return result if isinstance(result, dict) else {"promoted": len(body.student_ids)}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.get("/history")
def get_history(user: Usr, student_id: int = Query(None)):
    hydrate_session(user)
    try:
        rows = promotion_service.get_history(student_id=student_id)
        return [dict(r) for r in rows]
    except (ServiceError, PolicyViolation):
        return []


@router.get("/academic-years")
def get_academic_years(user: Usr):
    rows = fetch_all("SELECT * FROM academic_years ORDER BY start_date DESC")
    return [dict(r) for r in rows]
