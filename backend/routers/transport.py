from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.transport_service import transport_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all, fetch_one

router = APIRouter(tags=["transport"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/routes")
def get_routes(user: Usr):
    hydrate_session(user)
    try:
        return [dict(r) for r in transport_service.get_routes()]
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class RoutePayload(BaseModel):
    name:         str
    description:  str = ""
    fare:         float = 0
    vehicle_no:   str = ""
    driver_name:  str = ""
    driver_phone: str = ""


@router.post("/routes")
def create_route(body: RoutePayload, user: Usr):
    hydrate_session(user)
    try:
        route_id = transport_service.add_route(body.model_dump())
        return dict(fetch_one("SELECT * FROM transport_routes WHERE id=?", (route_id,)))
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.put("/routes/{route_id}")
def update_route(route_id: int, body: RoutePayload, user: Usr):
    hydrate_session(user)
    try:
        transport_service.update_route(route_id, body.model_dump())
        return dict(fetch_one("SELECT * FROM transport_routes WHERE id=?", (route_id,)))
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.get("/routes/{route_id}/students")
def get_route_students(route_id: int, user: Usr):
    hydrate_session(user)
    try:
        return [dict(r) for r in transport_service.get_route_students(route_id)]
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class AssignBody(BaseModel):
    student_id:        int
    route_id:          int
    academic_year_id:  int
    term:              int = 1
    pickup_point:      str = ""


@router.post("/assign")
def assign_student(body: AssignBody, user: Usr):
    hydrate_session(user)
    try:
        sub_id = transport_service.assign_student(
            body.student_id, body.route_id, body.academic_year_id,
            body.term, body.pickup_point,
        )
        return {"subscription_id": sub_id, "ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.delete("/subscriptions/{sub_id}")
def unassign_student(sub_id: int, user: Usr):
    hydrate_session(user)
    try:
        transport_service.cancel_subscription(sub_id)
        return {"ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.get("/stats")
def get_stats(user: Usr):
    hydrate_session(user)
    try:
        return transport_service.get_stats()
    except Exception:
        return {}
