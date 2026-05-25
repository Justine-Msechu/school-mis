from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.services.enrollment_service import EnrollmentService
from backend.core.security import require_permission
from backend.deps import require_auth

router = APIRouter(tags=["enrollments"])
Usr = Annotated[dict, Depends(require_auth)]


class EnrollRequest(BaseModel):
    student_id: int
    class_id: int
    academic_year_id: int


class TransferRequest(BaseModel):
    new_class_id: int
    reason: str


class WithdrawRequest(BaseModel):
    reason: str


class BulkEnrollRow(BaseModel):
    student_id: int
    class_id: int
    academic_year_id: int


class BulkEnrollRequest(BaseModel):
    rows: list[BulkEnrollRow]


@router.post("")
def enroll_student(body: EnrollRequest, user: Usr):
    require_permission(user, "enrollment.manage")
    svc = EnrollmentService()
    return svc.enroll_student(body.student_id, body.class_id, body.academic_year_id, user["id"])


@router.post("/{enrollment_id}/transfer")
def transfer_student(enrollment_id: int, body: TransferRequest, user: Usr):
    require_permission(user, "enrollment.manage")
    svc = EnrollmentService()
    return {"new_enrollment_id": svc.transfer_student(enrollment_id, body.new_class_id, body.reason, user["id"])}


@router.post("/{enrollment_id}/withdraw")
def withdraw_student(enrollment_id: int, body: WithdrawRequest, user: Usr):
    require_permission(user, "enrollment.manage")
    svc = EnrollmentService()
    svc.withdraw_student(enrollment_id, body.reason)
    return {"status": "withdrawn"}


@router.get("/class/{class_id}")
def class_roll(class_id: int, academic_year_id: int, status: str = "active", user: Usr = None):
    require_permission(user, "enrollment.view")
    svc = EnrollmentService()
    return svc.get_class_roll(class_id, academic_year_id, status)


@router.get("/student/{student_id}")
def student_history(student_id: int, user: Usr):
    require_permission(user, "enrollment.view")
    svc = EnrollmentService()
    return svc.get_student_history(student_id)


@router.get("/student/{student_id}/current")
def current_enrollment(student_id: int, user: Usr):
    require_permission(user, "enrollment.view")
    svc = EnrollmentService()
    return svc.get_current_enrollment(student_id)


@router.get("/headcount")
def headcount_summary(academic_year_id: int = None, user: Usr = None):
    require_permission(user, "enrollment.view")
    svc = EnrollmentService()
    return svc.get_headcount_summary(academic_year_id)


@router.post("/bulk")
def bulk_enroll(body: BulkEnrollRequest, user: Usr):
    require_permission(user, "enrollment.manage")
    svc = EnrollmentService()
    rows = [{"student_id": r.student_id, "class_id": r.class_id,
             "academic_year_id": r.academic_year_id, "created_by": user["id"]}
            for r in body.rows]
    return svc.bulk_enroll(rows)
