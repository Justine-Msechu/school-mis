from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.grades_service import grades_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all

router = APIRouter(tags=["grades"])

Usr = Annotated[dict, Depends(require_auth)]


def _hydrate(user: dict):
    hydrate_session(user)


@router.get("/exams")
def get_exams(user: Usr):
    _hydrate(user)
    try:
        return grades_service.get_exams()
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.get("/classes")
def get_classes(user: Usr):
    rows = fetch_all("SELECT id, name FROM classes ORDER BY name")
    return [dict(r) for r in rows]


@router.get("/subjects")
def get_subjects(class_id: int, user: Usr):
    _hydrate(user)
    try:
        subjs = grades_service.get_subjects_for_teacher(class_id)
        return [dict(s) for s in subjs]
    except (ServiceError, PolicyViolation):
        rows = fetch_all("SELECT id, name, code, credit_hours FROM subjects ORDER BY name")
        return [dict(r) for r in rows]


@router.get("/results")
def get_results(exam_id: int, class_id: int, user: Usr):
    _hydrate(user)
    try:
        report = grades_service.get_result_report(exam_id, class_id)
        # Convert any sqlite3.Row objects inside report to plain dicts
        report["subjects"] = [dict(s) for s in report["subjects"]]
        report["rows"] = [
            {**r, "grades": {str(k): dict(v) if hasattr(v, "keys") else v for k, v in r["grades"].items()}}
            for r in report["rows"]
        ]
        return report
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.get("/sheet")
def get_sheet(exam_id: int, class_id: int, subject_id: int, user: Usr):
    _hydrate(user)
    try:
        sheet = grades_service.get_grade_sheet(exam_id, class_id, subject_id)
        return [dict(r) for r in sheet]
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class SaveGradesBody(BaseModel):
    exam_id: int
    class_id: int
    subject_id: int
    entries: list[dict]


@router.post("/save")
def save_grades(body: SaveGradesBody, user: Usr):
    _hydrate(user)
    try:
        n = grades_service.save_grades(body.exam_id, body.class_id, body.subject_id, body.entries)
        return {"saved": n}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class SubmitGradesBody(BaseModel):
    exam_id: int
    class_id: int
    subject_id: int


@router.post("/submit")
def submit_grades(body: SubmitGradesBody, user: Usr):
    _hydrate(user)
    try:
        n = grades_service.submit_grades(body.exam_id, body.class_id, body.subject_id)
        return {"submitted": n}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class ChangeRequestBody(BaseModel):
    grade_id: int
    proposed_score: float
    proposed_max: float
    reason: str


@router.post("/change-request")
def change_request(body: ChangeRequestBody, user: Usr):
    _hydrate(user)
    try:
        grades_service.request_grade_change(body.grade_id, body.proposed_score, body.proposed_max, body.reason)
        return {"ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))
