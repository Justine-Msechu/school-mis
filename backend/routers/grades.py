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


# ── Change requests (review) ──────────────────────────────────────────────────

@router.get("/change-requests")
def list_change_requests(user: Usr, status: str = Query("pending")):
    _hydrate(user)
    rows = fetch_all(
        """SELECT gcr.*,
                  s.first_name || ' ' || s.last_name as student_name, s.admission_no,
                  subj.name as subject_name, e.name as exam_name
           FROM grade_change_requests gcr
           JOIN grades g ON g.id=gcr.grade_id
           JOIN students s ON s.id=g.student_id
           JOIN subjects subj ON subj.id=g.subject_id
           JOIN exams e ON e.id=g.exam_id
           WHERE gcr.status=?
           ORDER BY gcr.created_at DESC""",
        (status,),
    )
    return [dict(r) for r in rows]


class ReviewChangeBody(BaseModel):
    action: str   # approve | reject
    note:   str = ""


@router.post("/change-requests/{cr_id}/review")
def review_change_request(cr_id: int, body: ReviewChangeBody, user: Usr):
    _hydrate(user)
    try:
        if body.action == "approve":
            grades_service.approve_grade_change(cr_id)
        else:
            grades_service.reject_grade_change(cr_id, body.note)
        return {"ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


# ── Exam management ───────────────────────────────────────────────────────────

class ExamPayload(BaseModel):
    name:       str
    term:       int
    year_label: str = ""
    status:     str = "open"


@router.post("/exams")
def create_exam(body: ExamPayload, user: Usr):
    from database.db import execute as db_execute, fetch_one as db_fetch_one
    _hydrate(user)
    row_id = db_execute(
        "INSERT INTO exams (name, term, year_label, status) VALUES (?,?,?,?)",
        (body.name, body.term, body.year_label, body.status),
    )
    return dict(db_fetch_one("SELECT * FROM exams WHERE id=?", (row_id,)))


@router.put("/exams/{exam_id}")
def update_exam(exam_id: int, body: ExamPayload, user: Usr):
    from database.db import execute as db_execute, fetch_one as db_fetch_one
    _hydrate(user)
    db_execute(
        "UPDATE exams SET name=?, term=?, year_label=?, status=? WHERE id=?",
        (body.name, body.term, body.year_label, body.status, exam_id),
    )
    return dict(db_fetch_one("SELECT * FROM exams WHERE id=?", (exam_id,)))


# ── Approvals ─────────────────────────────────────────────────────────────────

@router.get("/pending-approval")
def pending_approval(user: Usr):
    _hydrate(user)
    rows = fetch_all(
        """SELECT g.subject_id, g.exam_id, st.class_id,
                  subj.name as subject_name, e.name as exam_name, c.name as class_name,
                  COUNT(g.id) as count
           FROM grades g
           JOIN students st ON st.id=g.student_id
           JOIN subjects subj ON subj.id=g.subject_id
           JOIN exams e ON e.id=g.exam_id
           JOIN classes c ON c.id=st.class_id
           WHERE g.status='submitted_locked'
           GROUP BY g.subject_id, g.exam_id, st.class_id
           ORDER BY e.name, c.name, subj.name"""
    )
    return [dict(r) for r in rows]


class ApproveBody(BaseModel):
    exam_id:    int
    class_id:   int
    subject_id: int


@router.post("/approve")
def approve_grades(body: ApproveBody, user: Usr):
    _hydrate(user)
    try:
        n = grades_service.approve_grades(body.exam_id, body.class_id, body.subject_id)
        return {"approved": n}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


# ── Homework ──────────────────────────────────────────────────────────────────

@router.get("/homework")
def list_homework(user: Usr, class_id: int = Query(None), subject_id: int = Query(None)):
    _hydrate(user)
    where = ["1=1"]
    params: list = []
    if class_id:   where.append("ha.class_id=?");   params.append(class_id)
    if subject_id: where.append("ha.subject_id=?"); params.append(subject_id)
    rows = fetch_all(
        f"""SELECT ha.*, c.name as class_name, s.name as subject_name
            FROM homework_assignments ha
            JOIN classes c ON c.id=ha.class_id
            JOIN subjects s ON s.id=ha.subject_id
            WHERE {' AND '.join(where)}
            ORDER BY ha.deadline DESC""",
        params,
    )
    return [dict(r) for r in rows]


class HomeworkPayload(BaseModel):
    class_id:    int
    subject_id:  int
    title:       str
    instructions:str = ""
    deadline:    str
    max_points:  float = 100


@router.post("/homework")
def create_homework(body: HomeworkPayload, user: Usr):
    from database.db import execute as db_execute, fetch_one as db_fetch_one
    _hydrate(user)
    row_id = db_execute(
        "INSERT INTO homework_assignments (class_id, subject_id, title, instructions, deadline, max_points, created_by) VALUES (?,?,?,?,?,?,?)",
        (body.class_id, body.subject_id, body.title, body.instructions, body.deadline, body.max_points, user.get("id")),
    )
    return dict(db_fetch_one("SELECT * FROM homework_assignments WHERE id=?", (row_id,)))


@router.get("/homework/{hw_id}/submissions")
def get_submissions(hw_id: int, user: Usr):
    rows = fetch_all(
        """SELECT hs.*, s.first_name || ' ' || s.last_name as student_name, s.admission_no
           FROM homework_submissions hs
           JOIN students s ON s.id=hs.student_id
           WHERE hs.assignment_id=?
           ORDER BY hs.submitted_at DESC""",
        (hw_id,),
    )
    return [dict(r) for r in rows]
