from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from backend.deps import require_auth
from backend.core.authz import compute_effective_permissions
from database.db import fetch_all, fetch_one

router = APIRouter(tags=["reports"])
Usr = Annotated[dict, Depends(require_auth)]


def _get_teacher_class(user_id: int) -> int | None:
    """Return the class_id the user is assigned to as class teacher, or None."""
    row = fetch_one(
        "SELECT class_id FROM class_teacher_assignments WHERE user_id=? AND is_active=1 LIMIT 1",
        (user_id,),
    )
    return dict(row)["class_id"] if row else None


@router.get("/attendance-summary")
def attendance_summary(user: Usr, class_id: int = Query(None), month: str = Query(None)):
    where = ["1=1"]
    params: list = []
    if class_id:
        where.append("a.class_id=?"); params.append(class_id)
    if month:
        where.append("strftime('%Y-%m', a.date)=?"); params.append(month)
    rows = fetch_all(
        f"""SELECT s.first_name || ' ' || s.last_name as student_name, s.admission_no,
                   COUNT(*) as total_days,
                   SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) as present,
                   SUM(CASE WHEN a.status='absent'  THEN 1 ELSE 0 END) as absent,
                   ROUND(100.0 * SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) / COUNT(*), 1) as rate
            FROM attendance a
            JOIN students s ON s.id=a.student_id
            WHERE {' AND '.join(where)}
            GROUP BY a.student_id ORDER BY rate ASC""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/fee-collection")
def fee_collection(user: Usr, academic_year_id: int = Query(None)):
    where = "WHERE 1=1"
    params: list = []
    if academic_year_id:
        where += " AND fs.academic_year_id=?"; params.append(academic_year_id)
    rows = fetch_all(
        f"""SELECT ft.name as fee_type,
                   COUNT(DISTINCT sb.student_id) as students,
                   COALESCE(SUM(sb.amount_due),0) as billed,
                   COALESCE(SUM(sb.amount_paid),0) as collected
            FROM fee_structures fs
            JOIN fee_types ft ON ft.id=fs.fee_type_id
            LEFT JOIN student_bills sb ON sb.fee_structure_id=fs.id
            {where}
            GROUP BY fs.fee_type_id ORDER BY ft.name""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/grade-summary")
def grade_summary(user: Usr, exam_id: int = Query(None)):
    where = "WHERE 1=1"
    params: list = []
    if exam_id:
        where += " AND g.exam_id=?"; params.append(exam_id)
    rows = fetch_all(
        f"""SELECT c.name as class_name, s.name as subject_name,
                   COUNT(g.id) as total,
                   ROUND(AVG(CAST(g.score AS REAL)/NULLIF(g.max_score,0)*100),1) as avg_pct,
                   SUM(CASE WHEN g.grade_letter='A' THEN 1 ELSE 0 END) as a_count,
                   SUM(CASE WHEN g.grade_letter='B' THEN 1 ELSE 0 END) as b_count,
                   SUM(CASE WHEN g.grade_letter='C' THEN 1 ELSE 0 END) as c_count,
                   SUM(CASE WHEN g.grade_letter='D' THEN 1 ELSE 0 END) as d_count,
                   SUM(CASE WHEN g.grade_letter='F' THEN 1 ELSE 0 END) as f_count
            FROM grades g
            JOIN students st ON st.id=g.student_id
            JOIN classes c ON c.id=st.class_id
            JOIN subjects s ON s.id=g.subject_id
            {where}
            GROUP BY st.class_id, g.subject_id ORDER BY c.name, s.name""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/overview")
def overview(user: Usr):
    perms  = compute_effective_permissions(user["id"])
    is_all = "*" in perms
    def can(p: str) -> bool:
        return is_all or p in perms

    result: dict = {}
    if can("student.view"):
        result["students"] = dict(fetch_one("SELECT COUNT(*) as n FROM students WHERE is_active=1") or {}).get("n", 0)
    if can("teachers.view"):
        result["teachers"] = dict(fetch_one("SELECT COUNT(*) as n FROM teachers") or {}).get("n", 0)
    if can("library.view"):
        result["books"]        = dict(fetch_one("SELECT COUNT(*) as n FROM library_books WHERE is_active=1") or {}).get("n", 0)
        result["active_loans"] = dict(fetch_one("SELECT COUNT(*) as n FROM library_loans WHERE status='active'") or {}).get("n", 0)
    if can("reports.finance") or can("finance.view"):
        result["total_expenses"] = dict(fetch_one("SELECT COALESCE(SUM(amount),0) as n FROM expenses") or {}).get("n", 0)
        result["total_revenue"]  = dict(fetch_one("SELECT COALESCE(SUM(amount_paid),0) as n FROM fee_payments") or {}).get("n", 0)
    return result


# ── My Class endpoints (class teacher scoped) ─────────────────────────────────

@router.get("/my-class/info")
def my_class_info(user: Usr):
    """Return basic info about the class teacher's assigned class + available exams."""
    class_id = _get_teacher_class(user["id"])
    if not class_id:
        raise HTTPException(404, "No class assignment found")
    cls = fetch_one("SELECT id, name, grade_level FROM classes WHERE id=?", (class_id,))
    student_count = dict(fetch_one(
        "SELECT COUNT(*) as n FROM students WHERE class_id=? AND is_active=1", (class_id,)
    ) or {}).get("n", 0)
    exams = fetch_all(
        """SELECT e.id, e.name, e.term, e.status
           FROM exams e
           WHERE EXISTS (SELECT 1 FROM grades g WHERE g.exam_id=e.id AND g.class_id=?)
           ORDER BY e.term, e.start_date""",
        (class_id,),
    )
    return {
        "class": dict(cls) if cls else {},
        "student_count": student_count,
        "exams": [dict(r) for r in exams],
    }


@router.get("/my-class/subject-averages")
def my_class_subject_averages(user: Usr, exam_id: int = Query(None)):
    """Subject averages + grade distribution for the teacher's class."""
    class_id = _get_teacher_class(user["id"])
    if not class_id:
        raise HTTPException(404, "No class assignment found")

    params: list = [class_id]
    exam_filter = ""
    if exam_id:
        exam_filter = "AND g.exam_id=?"
        params.append(exam_id)

    rows = fetch_all(
        f"""SELECT s.name AS subject,
                   ROUND(AVG(CAST(g.score AS REAL)/NULLIF(g.max_score,0)*100), 1) AS avg_pct,
                   COUNT(g.id) AS total_students,
                   SUM(CASE WHEN g.grade_letter='A' THEN 1 ELSE 0 END) AS a,
                   SUM(CASE WHEN g.grade_letter='B' THEN 1 ELSE 0 END) AS b,
                   SUM(CASE WHEN g.grade_letter='C' THEN 1 ELSE 0 END) AS c,
                   SUM(CASE WHEN g.grade_letter='D' THEN 1 ELSE 0 END) AS d,
                   SUM(CASE WHEN g.grade_letter='F' THEN 1 ELSE 0 END) AS f
            FROM grades g
            JOIN subjects s ON s.id=g.subject_id
            WHERE g.class_id=? {exam_filter}
            GROUP BY g.subject_id
            ORDER BY avg_pct DESC""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/my-class/term-comparison")
def my_class_term_comparison(user: Usr):
    """Subject averages grouped by term — used for grouped bar / line chart."""
    class_id = _get_teacher_class(user["id"])
    if not class_id:
        raise HTTPException(404, "No class assignment found")

    rows = fetch_all(
        """SELECT e.term,
                  s.name AS subject,
                  ROUND(AVG(CAST(g.score AS REAL)/NULLIF(g.max_score,0)*100), 1) AS avg_pct
           FROM grades g
           JOIN exams e ON e.id=g.exam_id
           JOIN subjects s ON s.id=g.subject_id
           WHERE g.class_id=?
           GROUP BY e.term, g.subject_id
           ORDER BY s.name, e.term""",
        (class_id,),
    )
    # Pivot: [{subject, term1, term2, term3}, ...]
    pivot: dict[str, dict] = {}
    for r in rows:
        row = dict(r)
        subj = row["subject"]
        if subj not in pivot:
            pivot[subj] = {"subject": subj}
        pivot[subj][f"term{row['term']}"] = row["avg_pct"]
    return list(pivot.values())


@router.get("/my-class/attendance-trend")
def my_class_attendance_trend(user: Usr):
    """Weekly attendance rate for the past 14 weeks for the teacher's class."""
    class_id = _get_teacher_class(user["id"])
    if not class_id:
        raise HTTPException(404, "No class assignment found")

    rows = fetch_all(
        """SELECT strftime('%Y-W%W', date) AS week,
                  strftime('%d %b', MIN(date)) AS week_label,
                  COUNT(*) AS total,
                  SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) AS present,
                  ROUND(100.0*SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)/COUNT(*), 1) AS rate
           FROM attendance
           WHERE class_id=?
             AND date >= date('now', '-98 days')
           GROUP BY week
           ORDER BY week""",
        (class_id,),
    )
    return [dict(r) for r in rows]


@router.get("/my-class/missing-marks")
def my_class_missing_marks(user: Usr, exam_id: int = Query(None)):
    """Students who are missing grades for any subject in the given exam."""
    class_id = _get_teacher_class(user["id"])
    if not class_id:
        raise HTTPException(404, "No class assignment found")

    # Default to most recent exam for this class
    if not exam_id:
        row = fetch_one(
            """SELECT e.id FROM exams e
               WHERE EXISTS (SELECT 1 FROM grades g WHERE g.exam_id=e.id AND g.class_id=?)
               ORDER BY e.term DESC, e.start_date DESC LIMIT 1""",
            (class_id,),
        )
        if row:
            exam_id = dict(row)["id"]
        else:
            return []

    # Subjects that have at least one grade recorded for this class/exam
    subjects_in_exam = fetch_all(
        "SELECT DISTINCT subject_id FROM grades WHERE class_id=? AND exam_id=?",
        (class_id, exam_id),
    )
    subject_ids = [dict(r)["subject_id"] for r in subjects_in_exam]
    if not subject_ids:
        return []

    placeholders = ",".join("?" * len(subject_ids))
    missing = fetch_all(
        f"""SELECT st.first_name||' '||st.last_name AS student_name,
                   st.admission_no,
                   s.name AS subject
            FROM students st
            CROSS JOIN subjects s
            WHERE st.class_id=? AND st.is_active=1
              AND s.id IN ({placeholders})
              AND NOT EXISTS (
                  SELECT 1 FROM grades g
                  WHERE g.student_id=st.id AND g.subject_id=s.id AND g.exam_id=?
              )
            ORDER BY st.last_name, s.name""",
        [class_id, *subject_ids, exam_id],
    )
    return [dict(r) for r in missing]
