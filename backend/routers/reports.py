from typing import Annotated
from fastapi import APIRouter, Depends, Query
from backend.deps import require_auth
from database.db import fetch_all, fetch_one

router = APIRouter(tags=["reports"])
Usr = Annotated[dict, Depends(require_auth)]


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
    students  = dict(fetch_one("SELECT COUNT(*) as n FROM students WHERE is_active=1") or {}).get("n", 0)
    teachers  = dict(fetch_one("SELECT COUNT(*) as n FROM teachers") or {}).get("n", 0)
    books     = dict(fetch_one("SELECT COUNT(*) as n FROM library_books WHERE is_active=1") or {}).get("n", 0)
    loans_out = dict(fetch_one("SELECT COUNT(*) as n FROM library_loans WHERE status='active'") or {}).get("n", 0)
    expenses  = dict(fetch_one("SELECT COALESCE(SUM(amount),0) as n FROM expenses") or {}).get("n", 0)
    revenue   = dict(fetch_one("SELECT COALESCE(SUM(amount_paid),0) as n FROM fee_payments") or {}).get("n", 0)
    return {
        "students": students, "teachers": teachers,
        "books": books,       "active_loans": loans_out,
        "total_expenses": expenses, "total_revenue": revenue,
    }
