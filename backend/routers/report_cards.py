from typing import Annotated, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.services.report_card_service import ReportCardService
from backend.core.security import require_permission
from backend.deps import require_auth

router = APIRouter(tags=["report_cards"])
Usr = Annotated[dict, Depends(require_auth)]


class GenerateRequest(BaseModel):
    exam_id: int
    class_id: int


class CommentBody(BaseModel):
    comment_type: str = "teacher"
    comment_text: str


@router.post("/generate")
def generate_cards(body: GenerateRequest, user: Usr):
    require_permission(user, "report_cards.generate")
    svc = ReportCardService()
    return svc.generate_for_class(body.exam_id, body.class_id, user["id"])


@router.get("/exam/{exam_id}")
def list_cards(exam_id: int, class_id: Optional[int] = None, user: Usr = None):
    require_permission(user, "report_cards.view")
    svc = ReportCardService()
    return svc.list_cards_for_exam(exam_id, class_id)


@router.get("/jobs/exam/{exam_id}")
def list_jobs(exam_id: int, user: Usr):
    require_permission(user, "report_cards.view")
    svc = ReportCardService()
    return svc.list_jobs(exam_id)


@router.get("/jobs/{job_id}")
def get_job(job_id: int, user: Usr):
    require_permission(user, "report_cards.view")
    svc = ReportCardService()
    return svc.get_job(job_id)


@router.get("/student/{student_id}/exam/{exam_id}")
def get_card(student_id: int, exam_id: int, user: Usr):
    require_permission(user, "report_cards.view")
    svc = ReportCardService()
    return svc.get_full_card(student_id, exam_id)


@router.post("/{card_id}/publish")
def publish_card(card_id: int, user: Usr):
    require_permission(user, "report_cards.publish")
    svc = ReportCardService()
    svc.publish_card(card_id, user["id"])
    return {"status": "published"}


@router.post("/{card_id}/lock")
def lock_card(card_id: int, user: Usr):
    require_permission(user, "report_cards.publish")
    svc = ReportCardService()
    svc.lock_card(card_id)
    return {"status": "locked"}


@router.post("/{card_id}/comments")
def add_comment(card_id: int, body: CommentBody, user: Usr):
    require_permission(user, "report_cards.comment")
    svc = ReportCardService()
    cid = svc.add_comment(card_id, user["id"], user.get("role"), body.comment_type, body.comment_text)
    return {"id": cid}
