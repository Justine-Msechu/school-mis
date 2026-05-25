"""
Grades router — thin HTTP controller.

For legacy compatibility, the old grades_service (PyQt6 layer) is preserved
for read operations. Write/approval operations go through the new
GradesApprovalService from backend.services.grades_service.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.deps import require_auth, hydrate_session
from backend.core.db import _get_conn
from backend.core.security import require_permission
from backend.core.exceptions import AppError
from backend.services.grades_service import GradesApprovalService
from backend.repositories.grades_repo import GradesRepository
from database.db import fetch_all

router = APIRouter(tags=["grades"])
Usr = Annotated[dict, Depends(require_auth)]


def _svc() -> GradesApprovalService:
    return GradesApprovalService(_get_conn())


def _repo() -> GradesRepository:
    return GradesRepository(_get_conn())


def _hydrate(user: dict):
    hydrate_session(user)


# ── Exams ──────────────────────────────────────────────────────────────────────

@router.get("/exams")
def get_exams(user: Usr, academic_year_id: int = Query(None)):
    return _repo().list_exams(academic_year_id)


@router.get("/classes")
def get_classes(user: Usr):
    rows = fetch_all("SELECT id, name FROM classes ORDER BY name")
    return [dict(r) for r in rows]


@router.get("/subjects")
def get_subjects(class_id: int, user: Usr):
    _hydrate(user)
    return _repo().list_subjects(class_id)


class ExamPayload(BaseModel):
    name:            str
    term:            int | None = None
    academic_year_id: int | None = None
    start_date:      str | None = None
    end_date:        str | None = None
    status:          str = "open"


@router.post("/exams")
def create_exam(body: ExamPayload, user: Usr):
    require_permission(user, "grades.view")
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO exams (name, term, academic_year_id, start_date, end_date, status) VALUES (?,?,?,?,?,?)",
        (body.name, body.term, body.academic_year_id, body.start_date, body.end_date, body.status),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM exams WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.put("/exams/{exam_id}")
def update_exam(exam_id: int, body: ExamPayload, user: Usr):
    require_permission(user, "grades.view")
    conn = _get_conn()
    conn.execute(
        "UPDATE exams SET name=?, term=?, academic_year_id=?, start_date=?, end_date=?, status=? WHERE id=?",
        (body.name, body.term, body.academic_year_id, body.start_date, body.end_date, body.status, exam_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()
    return dict(row) if row else HTTPException(404, "Exam not found")


# ── Grade sheet ────────────────────────────────────────────────────────────────

@router.get("/sheet")
def get_sheet(exam_id: int, class_id: int, subject_id: int, user: Usr):
    require_permission(user, "grades.view")
    return _repo().get_sheet(exam_id, class_id, subject_id)


@router.get("/results")
def get_results(exam_id: int, class_id: int, user: Usr):
    require_permission(user, "grades.view")
    _hydrate(user)
    try:
        from services.grades_service import grades_service
        report = grades_service.get_result_report(exam_id, class_id)
        report["subjects"] = [dict(s) for s in report["subjects"]]
        report["rows"] = [
            {**r, "grades": {str(k): dict(v) if hasattr(v, "keys") else v for k, v in r["grades"].items()}}
            for r in report["rows"]
        ]
        return report
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Grade entry ────────────────────────────────────────────────────────────────

class SaveGradesBody(BaseModel):
    exam_id:    int
    class_id:   int
    subject_id: int
    entries:    list[dict]


@router.post("/save")
def save_grades(body: SaveGradesBody, user: Usr):
    require_permission(user, "grades.write")
    try:
        svc = _svc()
        n = svc.save_draft(body.exam_id, body.class_id, body.subject_id, body.entries, actor=user)
        return {"saved": n}
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


# ── Workflow transitions ───────────────────────────────────────────────────────

class BatchBody(BaseModel):
    exam_id:    int
    class_id:   int
    subject_id: int
    comment:    str = ""
    reason:     str = ""


@router.post("/submit")
def submit_grades(body: BatchBody, user: Usr):
    require_permission(user, "grades.submit")
    try:
        n = _svc().submit(body.exam_id, body.class_id, body.subject_id, actor=user)
        return {"submitted": n}
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


@router.post("/approve")
def approve_grades(body: BatchBody, user: Usr):
    require_permission(user, "grades.approve")
    try:
        n = _svc().approve(body.exam_id, body.class_id, body.subject_id, actor=user, comment=body.comment)
        return {"approved": n}
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


@router.post("/return")
def return_grades(body: BatchBody, user: Usr):
    require_permission(user, "grades.approve")
    try:
        n = _svc().return_for_correction(body.exam_id, body.class_id, body.subject_id, reason=body.reason, actor=user)
        return {"returned": n}
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


@router.post("/publish")
def publish_grades(body: BatchBody, user: Usr):
    require_permission(user, "grades.publish")
    try:
        n = _svc().publish(body.exam_id, body.class_id, body.subject_id, actor=user)
        return {"published": n}
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


# ── Rankings ──────────────────────────────────────────────────────────────────

@router.get("/rankings")
def get_rankings(exam_id: int, class_id: int, user: Usr, academic_year_id: int = Query(None)):
    require_permission(user, "grades.view")
    try:
        return _svc().get_class_rankings(exam_id, class_id, academic_year_id)
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


# ── Pending approval ──────────────────────────────────────────────────────────

@router.get("/pending-approval")
def pending_approval(user: Usr):
    require_permission(user, "grades.approve")
    return _repo().pending_approval_summary()


# ── Change requests ───────────────────────────────────────────────────────────

@router.get("/change-requests")
def list_change_requests(user: Usr, status: str = Query("pending")):
    require_permission(user, "grades.view")
    return _repo().list_change_requests(status)


class ChangeRequestBody(BaseModel):
    grade_id:       int
    proposed_score: float
    proposed_max:   float
    reason:         str


@router.post("/change-request")
def create_change_request(body: ChangeRequestBody, user: Usr):
    require_permission(user, "grades.change_request.create")
    try:
        cr_id = _svc().request_change(
            body.grade_id, body.proposed_score, body.proposed_max, body.reason, actor=user
        )
        return {"id": cr_id, "ok": True}
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


class ReviewChangeBody(BaseModel):
    action: str   # 'approve' | 'reject'
    note:   str = ""


@router.post("/change-requests/{cr_id}/review")
def review_change_request(cr_id: int, body: ReviewChangeBody, user: Usr):
    require_permission(user, "grades.change_request.review")
    try:
        _svc().resolve_change_request(
            cr_id,
            approved=(body.action == "approve"),
            comment=body.note,
            actor=user,
        )
        return {"ok": True}
    except AppError as e:
        raise HTTPException(e.http_status, e.message)


# ── Grade approval log ─────────────────────────────────────────────────────────

@router.get("/{grade_id}/history")
def get_grade_history(grade_id: int, user: Usr):
    require_permission(user, "grades.view")
    return _repo().get_approval_log(grade_id)


# ── Homework ──────────────────────────────────────────────────────────────────

@router.get("/homework")
def list_homework(user: Usr, class_id: int = Query(None), subject_id: int = Query(None)):
    where = ["1=1"]
    params: list = []
    if class_id:   where.append("ha.class_id=?");   params.append(class_id)
    if subject_id: where.append("ha.subject_id=?"); params.append(subject_id)
    rows = fetch_all(
        f"""SELECT ha.*, c.name AS class_name, s.name AS subject_name
            FROM homework_assignments ha
            JOIN classes c ON c.id=ha.class_id
            JOIN subjects s ON s.id=ha.subject_id
            WHERE {' AND '.join(where)}
            ORDER BY ha.deadline DESC""",
        params,
    )
    return [dict(r) for r in rows]


class HomeworkPayload(BaseModel):
    class_id:     int
    subject_id:   int
    title:        str
    instructions: str = ""
    deadline:     str
    max_points:   float = 100


@router.post("/homework")
def create_homework(body: HomeworkPayload, user: Usr):
    require_permission(user, "homework.write")
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO homework_assignments (class_id, subject_id, title, instructions, deadline, max_points, created_by) VALUES (?,?,?,?,?,?,?)",
        (body.class_id, body.subject_id, body.title, body.instructions, body.deadline, body.max_points, user.get("id")),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM homework_assignments WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.get("/homework/{hw_id}/submissions")
def get_submissions(hw_id: int, user: Usr):
    rows = fetch_all(
        """SELECT hs.*, s.first_name || ' ' || s.last_name AS student_name, s.admission_no
           FROM homework_submissions hs
           JOIN students s ON s.id=hs.student_id
           WHERE hs.assignment_id=?
           ORDER BY hs.submitted_at DESC""",
        (hw_id,),
    )
    return [dict(r) for r in rows]
