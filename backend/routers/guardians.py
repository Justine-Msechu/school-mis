from typing import Annotated, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.services.guardian_service import GuardianService
from backend.core.security import require_permission
from backend.deps import require_auth

router = APIRouter(tags=["guardians"])
Usr = Annotated[dict, Depends(require_auth)]


class GuardianCreate(BaseModel):
    full_name: str
    relationship: str = "guardian"
    gender: Optional[str] = None
    phone: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    id_number: Optional[str] = None
    occupation: Optional[str] = None
    address: Optional[str] = None
    is_emergency_contact: int = 0
    is_pickup_authorized: int = 1
    is_billing_contact: int = 0
    communication_pref: str = "phone"
    notes: Optional[str] = None


class GuardianUpdate(BaseModel):
    full_name: Optional[str] = None
    relationship: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    id_number: Optional[str] = None
    occupation: Optional[str] = None
    address: Optional[str] = None
    is_emergency_contact: Optional[int] = None
    is_pickup_authorized: Optional[int] = None
    is_billing_contact: Optional[int] = None
    communication_pref: Optional[str] = None
    notes: Optional[str] = None


class LinkStudentBody(BaseModel):
    student_id: int
    is_primary: bool = False


@router.get("")
def list_guardians(search: str = "", user: Usr = None):
    require_permission(user, "guardian.view")
    svc = GuardianService()
    return svc.list_guardians(search)


@router.post("")
def create_guardian(body: GuardianCreate, user: Usr):
    require_permission(user, "guardian.manage")
    svc = GuardianService()
    return svc.create_guardian(body.model_dump())


@router.get("/by-student/{student_id}")
def student_guardians(student_id: int, user: Usr):
    require_permission(user, "guardian.view")
    svc = GuardianService()
    return svc.get_student_guardians(student_id)


@router.get("/{guardian_id}")
def get_guardian(guardian_id: int, user: Usr):
    require_permission(user, "guardian.view")
    svc = GuardianService()
    return svc.get_guardian(guardian_id)


@router.patch("/{guardian_id}")
def update_guardian(guardian_id: int, body: GuardianUpdate, user: Usr):
    require_permission(user, "guardian.manage")
    svc = GuardianService()
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return svc.update_guardian(guardian_id, data)


@router.delete("/{guardian_id}")
def delete_guardian(guardian_id: int, user: Usr):
    require_permission(user, "guardian.manage")
    svc = GuardianService()
    svc.delete_guardian(guardian_id)
    return {"status": "deleted"}


@router.post("/{guardian_id}/students")
def link_student(guardian_id: int, body: LinkStudentBody, user: Usr):
    require_permission(user, "guardian.manage")
    svc = GuardianService()
    svc.link_to_student(guardian_id, body.student_id, body.is_primary)
    return {"status": "linked"}


@router.delete("/{guardian_id}/students/{student_id}")
def unlink_student(guardian_id: int, student_id: int, user: Usr):
    require_permission(user, "guardian.manage")
    svc = GuardianService()
    svc.unlink_from_student(guardian_id, student_id)
    return {"status": "unlinked"}


@router.get("/{guardian_id}/students")
def guardian_students(guardian_id: int, user: Usr):
    require_permission(user, "guardian.view")
    svc = GuardianService()
    return svc.get_guardian_students(guardian_id)
