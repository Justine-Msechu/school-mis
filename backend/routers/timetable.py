from typing import Annotated, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.services.timetable_service import TimetableService
from backend.core.security import require_permission
from backend.deps import require_auth

router = APIRouter(tags=["timetable"])
Usr = Annotated[dict, Depends(require_auth)]


class VersionCreate(BaseModel):
    academic_year_id: int
    name: str
    term_id: Optional[int] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None


class SlotBody(BaseModel):
    class_id: int
    subject_id: int
    period_id: int
    day_of_week: int
    teacher_id: Optional[int] = None
    room: Optional[str] = None
    notes: Optional[str] = None


@router.get("/periods")
def list_periods(user: Usr):
    svc = TimetableService()
    return svc.list_periods()


@router.get("/versions")
def list_versions(academic_year_id: int, user: Usr):
    require_permission(user, "timetable.view")
    svc = TimetableService()
    return svc.list_versions(academic_year_id)


@router.post("/versions")
def create_version(body: VersionCreate, user: Usr):
    require_permission(user, "timetable.manage")
    svc = TimetableService()
    return svc.create_version(
        body.academic_year_id, body.name, body.term_id,
        body.effective_from, body.effective_to, user["id"]
    )


@router.post("/versions/{version_id}/activate")
def activate_version(version_id: int, user: Usr):
    require_permission(user, "timetable.manage")
    svc = TimetableService()
    return svc.activate_version(version_id)


@router.post("/versions/{version_id}/archive")
def archive_version(version_id: int, user: Usr):
    require_permission(user, "timetable.manage")
    svc = TimetableService()
    svc.archive_version(version_id)
    return {"status": "archived"}


@router.get("/active")
def active_version(academic_year_id: int, user: Usr):
    require_permission(user, "timetable.view")
    svc = TimetableService()
    return svc.get_active_version(academic_year_id)


@router.get("/versions/{version_id}/class/{class_id}")
def class_timetable(version_id: int, class_id: int, user: Usr):
    require_permission(user, "timetable.view")
    svc = TimetableService()
    return svc.get_class_timetable(version_id, class_id)


@router.get("/versions/{version_id}/teacher/{teacher_id}")
def teacher_timetable(version_id: int, teacher_id: int, user: Usr):
    require_permission(user, "timetable.view")
    svc = TimetableService()
    return svc.get_teacher_timetable(version_id, teacher_id)


@router.post("/versions/{version_id}/slots")
def set_slot(version_id: int, body: SlotBody, user: Usr):
    require_permission(user, "timetable.manage")
    svc = TimetableService()
    return svc.set_slot(
        version_id, body.class_id, body.subject_id,
        body.period_id, body.day_of_week, body.teacher_id,
        body.room, body.notes
    )


@router.delete("/slots/{slot_id}")
def delete_slot(slot_id: int, user: Usr):
    require_permission(user, "timetable.manage")
    svc = TimetableService()
    svc.delete_slot(slot_id)
    return {"status": "deleted"}
