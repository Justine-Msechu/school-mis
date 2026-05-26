from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from backend.deps import require_auth
from backend.core.authz import compute_effective_permissions
from backend.core.security import require_permission
from database.db import fetch_all, fetch_one

from backend.deps import rate_limit
from fastapi import Depends
router = APIRouter(tags=["reports"], dependencies=[Depends(rate_limit(max_calls=60, window_secs=60, scope="reports"))])
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


# ── My Subject endpoints (subject teacher scoped) ─────────────────────────────

def _get_subject_assignments(user_id: int) -> list[dict]:
    """Return list of {subject_id, subject_name, class_id, class_name} for the teacher."""
    rows = fetch_all(
        """SELECT ta.subject_id, s.name AS subject_name, ta.class_id, c.name AS class_name
           FROM teacher_assignments ta
           JOIN subjects s ON s.id=ta.subject_id
           JOIN classes  c ON c.id=ta.class_id
           WHERE ta.user_id=? AND ta.is_active=1
           ORDER BY s.name, c.name""",
        (user_id,),
    )
    return [dict(r) for r in rows]


@router.get("/my-subject/info")
def my_subject_info(user: Usr):
    """Return the subjects + classes this teacher is assigned to, plus available exams."""
    assignments = _get_subject_assignments(user["id"])
    if not assignments:
        raise HTTPException(404, "No subject assignments found")

    subject_ids = list({a["subject_id"] for a in assignments})
    class_ids   = list({a["class_id"]   for a in assignments})

    ph_s = ",".join("?" * len(subject_ids))
    ph_c = ",".join("?" * len(class_ids))

    exams = fetch_all(
        f"""SELECT DISTINCT e.id, e.name, e.term, e.status
            FROM exams e
            JOIN grades g ON g.exam_id=e.id
            WHERE g.subject_id IN ({ph_s}) AND g.class_id IN ({ph_c})
            ORDER BY e.term, e.start_date""",
        [*subject_ids, *class_ids],
    )

    # Unique subjects list
    subjects_seen: dict[int, str] = {}
    for a in assignments:
        subjects_seen[a["subject_id"]] = a["subject_name"]

    return {
        "assignments": assignments,
        "subjects": [{"id": sid, "name": sname} for sid, sname in subjects_seen.items()],
        "exams": [dict(r) for r in exams],
    }


@router.get("/my-subject/averages")
def my_subject_averages(user: Usr, exam_id: int = Query(None), subject_id: int = Query(None)):
    """Per-class average for each assigned subject (optionally filtered by exam/subject)."""
    assignments = _get_subject_assignments(user["id"])
    if not assignments:
        raise HTTPException(404, "No subject assignments found")

    if subject_id:
        assignments = [a for a in assignments if a["subject_id"] == subject_id]

    if not assignments:
        return []

    results = []
    for a in assignments:
        params: list = [a["subject_id"], a["class_id"]]
        exam_filter = ""
        if exam_id:
            exam_filter = "AND g.exam_id=?"
            params.append(exam_id)

        row = fetch_one(
            f"""SELECT ROUND(AVG(CAST(g.score AS REAL)/NULLIF(g.max_score,0)*100),1) AS avg_pct,
                       COUNT(g.id) AS total_students,
                       SUM(CASE WHEN g.grade_letter='A' THEN 1 ELSE 0 END) AS a,
                       SUM(CASE WHEN g.grade_letter='B' THEN 1 ELSE 0 END) AS b,
                       SUM(CASE WHEN g.grade_letter='C' THEN 1 ELSE 0 END) AS c,
                       SUM(CASE WHEN g.grade_letter='D' THEN 1 ELSE 0 END) AS d,
                       SUM(CASE WHEN g.grade_letter='F' THEN 1 ELSE 0 END) AS f
                FROM grades g
                WHERE g.subject_id=? AND g.class_id=? {exam_filter}""",
            params,
        )
        if row:
            d = dict(row)
            d["subject"] = a["subject_name"]
            d["class"]   = a["class_name"]
            if d["avg_pct"] is not None:
                results.append(d)

    return results


@router.get("/my-subject/term-comparison")
def my_subject_term_comparison(user: Usr, subject_id: int = Query(None)):
    """Per-class averages grouped by term for the teacher's subject(s)."""
    assignments = _get_subject_assignments(user["id"])
    if not assignments:
        raise HTTPException(404, "No subject assignments found")

    if subject_id:
        assignments = [a for a in assignments if a["subject_id"] == subject_id]

    pivot: dict[str, dict] = {}
    for a in assignments:
        rows = fetch_all(
            """SELECT e.term,
                      ROUND(AVG(CAST(g.score AS REAL)/NULLIF(g.max_score,0)*100),1) AS avg_pct
               FROM grades g
               JOIN exams e ON e.id=g.exam_id
               WHERE g.subject_id=? AND g.class_id=?
               GROUP BY e.term ORDER BY e.term""",
            (a["subject_id"], a["class_id"]),
        )
        key = f"{a['subject_name']} – {a['class_name']}"
        if key not in pivot:
            pivot[key] = {"label": key}
        for r in rows:
            rd = dict(r)
            pivot[key][f"term{rd['term']}"] = rd["avg_pct"]

    return list(pivot.values())


@router.get("/my-subject/grade-distribution")
def my_subject_grade_distribution(user: Usr, exam_id: int = Query(None), subject_id: int = Query(None)):
    """Aggregated A/B/C/D/F counts across all the teacher's assigned classes for a subject."""
    assignments = _get_subject_assignments(user["id"])
    if not assignments:
        raise HTTPException(404, "No subject assignments found")

    if subject_id:
        assignments = [a for a in assignments if a["subject_id"] == subject_id]

    totals = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for a in assignments:
        params: list = [a["subject_id"], a["class_id"]]
        exam_filter = ""
        if exam_id:
            exam_filter = "AND exam_id=?"
            params.append(exam_id)
        row = fetch_one(
            f"""SELECT SUM(CASE WHEN grade_letter='A' THEN 1 ELSE 0 END) AS a,
                       SUM(CASE WHEN grade_letter='B' THEN 1 ELSE 0 END) AS b,
                       SUM(CASE WHEN grade_letter='C' THEN 1 ELSE 0 END) AS c,
                       SUM(CASE WHEN grade_letter='D' THEN 1 ELSE 0 END) AS d,
                       SUM(CASE WHEN grade_letter='F' THEN 1 ELSE 0 END) AS f
                FROM grades WHERE subject_id=? AND class_id=? {exam_filter}""",
            params,
        )
        if row:
            rd = dict(row)
            for letter in ("A","B","C","D","F"):
                totals[letter] += rd.get(letter.lower(), 0) or 0

    return [{"name": k, "value": v} for k, v in totals.items() if v > 0]


@router.get("/my-subject/missing-marks")
def my_subject_missing_marks(user: Usr, exam_id: int = Query(None), subject_id: int = Query(None)):
    """Students missing grades for the teacher's subject(s) in the given exam."""
    assignments = _get_subject_assignments(user["id"])
    if not assignments:
        raise HTTPException(404, "No subject assignments found")

    if subject_id:
        assignments = [a for a in assignments if a["subject_id"] == subject_id]

    # Default to latest exam that has any grade for these assignments
    if not exam_id:
        subject_ids = list({a["subject_id"] for a in assignments})
        class_ids   = list({a["class_id"]   for a in assignments})
        ph_s = ",".join("?" * len(subject_ids))
        ph_c = ",".join("?" * len(class_ids))
        row = fetch_one(
            f"""SELECT e.id FROM exams e
                JOIN grades g ON g.exam_id=e.id
                WHERE g.subject_id IN ({ph_s}) AND g.class_id IN ({ph_c})
                ORDER BY e.term DESC, e.start_date DESC LIMIT 1""",
            [*subject_ids, *class_ids],
        )
        if row:
            exam_id = dict(row)["id"]
        else:
            return []

    missing = []
    for a in assignments:
        rows = fetch_all(
            """SELECT st.first_name||' '||st.last_name AS student_name,
                      st.admission_no,
                      ? AS subject,
                      ? AS class
               FROM students st
               WHERE st.class_id=? AND st.is_active=1
                 AND NOT EXISTS (
                     SELECT 1 FROM grades g
                     WHERE g.student_id=st.id AND g.subject_id=? AND g.exam_id=?
                 )
               ORDER BY st.last_name""",
            (a["subject_name"], a["class_name"], a["class_id"], a["subject_id"], exam_id),
        )
        missing.extend([dict(r) for r in rows])

    return missing


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


# ── Accounting reports ────────────────────────────────────────────────────────

@router.get("/accounting/fee-collection-by-class")
def fee_collection_by_class(
    user: Usr,
    academic_year_id: int = Query(None),
    term: int = Query(None),
):
    """Billed vs collected per class, for the bar chart."""
    require_permission(user, "finance.view")
    where = ["1=1"]
    params: list = []
    if academic_year_id:
        where.append("sb.academic_year_id = ?"); params.append(academic_year_id)
    if term:
        where.append("sb.term = ?"); params.append(term)
    rows = fetch_all(
        f"""SELECT
               COALESCE(c.name, 'Unassigned')    AS class_name,
               COALESCE(SUM(sb.amount_due), 0)   AS billed,
               COALESCE(SUM(sb.amount_paid), 0)  AS collected,
               COALESCE(SUM(sb.amount_due - sb.amount_paid), 0) AS outstanding
            FROM student_bills sb
            JOIN students s ON s.id = sb.student_id
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE {' AND '.join(where)}
            GROUP BY s.class_id
            ORDER BY c.name""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/accounting/monthly-income")
def monthly_income(user: Usr, year: int = Query(None)):
    """Payment totals grouped by month, for the line/bar chart."""
    require_permission(user, "finance.view")
    params: list = []
    year_filter = ""
    if year:
        year_filter = "WHERE strftime('%Y', p.payment_date) = ?"
        params.append(str(year))
    rows = fetch_all(
        f"""SELECT
               strftime('%Y-%m', p.payment_date) AS month,
               COALESCE(SUM(p.amount), 0)        AS income
            FROM payments p
            {year_filter}
            GROUP BY month
            ORDER BY month""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/accounting/expense-breakdown")
def expense_breakdown(
    user: Usr,
    from_date: str = Query(None),
    to_date:   str = Query(None),
):
    """Expenses grouped by category, for the pie chart."""
    require_permission(user, "finance.view")
    where = ["1=1"]
    params: list = []
    if from_date:
        where.append("e.expense_date >= ?"); params.append(from_date)
    if to_date:
        where.append("e.expense_date <= ?"); params.append(to_date)
    rows = fetch_all(
        f"""SELECT
               COALESCE(ec.name, e.category, 'Other') AS category,
               COALESCE(SUM(e.amount), 0)             AS total
            FROM expenses e
            LEFT JOIN expense_categories ec ON ec.id = e.category_id
            WHERE {' AND '.join(where)}
            GROUP BY COALESCE(ec.name, e.category, 'Other')
            ORDER BY total DESC""",
        params,
    )
    return [dict(r) for r in rows]


# ── Inventory reports ─────────────────────────────────────────────────────────

@router.get("/inventory/overview")
def inventory_overview(user: Usr):
    """Summary stats for the storekeeper dashboard."""
    from backend.deps import require_auth  # user already verified
    total     = fetch_one("SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1")
    low       = fetch_one("SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1 AND stock_qty <= reorder_qty")
    value     = fetch_one("SELECT COALESCE(SUM(stock_qty * unit_price),0) AS v FROM inventory_items WHERE is_active=1")
    pending   = fetch_one("SELECT COUNT(*) AS n FROM inventory_requests WHERE status='pending'")
    today_in  = fetch_one("SELECT COUNT(*) AS n FROM inventory_transactions WHERE type='stock_in' AND DATE(created_at)=DATE('now')")
    today_out = fetch_one("SELECT COUNT(*) AS n FROM inventory_transactions WHERE type='issued' AND DATE(created_at)=DATE('now')")
    return {
        "total_items":      dict(total)["n"]   if total   else 0,
        "low_stock_count":  dict(low)["n"]     if low     else 0,
        "stock_value":      dict(value)["v"]   if value   else 0,
        "pending_requests": dict(pending)["n"] if pending else 0,
        "today_stock_in":   dict(today_in)["n"]  if today_in  else 0,
        "today_issued":     dict(today_out)["n"] if today_out else 0,
    }


@router.get("/inventory/by-category")
def inventory_by_category(user: Usr):
    """Items count and total value per main category."""
    rows = fetch_all("""
        SELECT
            COALESCE(main_category, 'Uncategorized') AS category,
            COUNT(*) AS item_count,
            COALESCE(SUM(stock_qty), 0) AS total_qty,
            COALESCE(SUM(stock_qty * unit_price), 0) AS total_value
        FROM inventory_items
        WHERE is_active = 1
        GROUP BY COALESCE(main_category, 'Uncategorized')
        ORDER BY total_value DESC
    """)
    return [dict(r) for r in rows]


@router.get("/inventory/monthly-movements")
def inventory_monthly_movements(user: Usr, months: int = Query(12)):
    """Monthly stock_in vs issued quantities for the last N months."""
    rows = fetch_all("""
        SELECT
            strftime('%Y-%m', created_at) AS month,
            SUM(CASE WHEN type='stock_in' THEN qty ELSE 0 END)  AS received,
            SUM(CASE WHEN type='issued'   THEN qty ELSE 0 END)  AS issued,
            SUM(CASE WHEN type='adjusted' THEN ABS(qty) ELSE 0 END) AS adjusted
        FROM inventory_transactions
        WHERE created_at >= date('now', ? || ' months')
        GROUP BY month
        ORDER BY month
    """, (f"-{months}",))
    return [dict(r) for r in rows]


@router.get("/inventory/type-distribution")
def inventory_type_distribution(user: Usr):
    """Consumable vs asset breakdown."""
    rows = fetch_all("""
        SELECT
            COALESCE(item_type, 'consumable') AS item_type,
            COUNT(*) AS count,
            COALESCE(SUM(stock_qty * unit_price), 0) AS value
        FROM inventory_items
        WHERE is_active = 1
        GROUP BY COALESCE(item_type, 'consumable')
    """)
    return [dict(r) for r in rows]


@router.get("/inventory/low-stock-detail")
def inventory_low_stock_detail(user: Usr):
    """Low-stock items with gap to reorder level, for the report table."""
    rows = fetch_all("""
        SELECT id, name,
               COALESCE(main_category,'') AS main_category,
               COALESCE(location,'') AS location,
               stock_qty AS quantity, reorder_qty, unit,
               COALESCE(unit_price,0) AS unit_price,
               (reorder_qty - stock_qty) AS shortage
        FROM inventory_items
        WHERE is_active=1 AND stock_qty <= reorder_qty
        ORDER BY shortage DESC, name
    """)
    return [dict(r) for r in rows]


@router.get("/accounting/income-vs-expense")
def income_vs_expense(user: Usr, year: int = Query(None)):
    """Monthly income vs expense for the combo chart."""
    require_permission(user, "finance.view")
    y = str(year) if year else None
    income_rows = fetch_all(
        "SELECT strftime('%Y-%m', payment_date) AS month, COALESCE(SUM(amount),0) AS income "
        "FROM payments " +
        ("WHERE strftime('%Y', payment_date)=? " if y else "") +
        "GROUP BY month ORDER BY month",
        [y] if y else [],
    )
    expense_rows = fetch_all(
        "SELECT strftime('%Y-%m', expense_date) AS month, COALESCE(SUM(amount),0) AS expense "
        "FROM expenses " +
        ("WHERE strftime('%Y', expense_date)=? " if y else "") +
        "GROUP BY month ORDER BY month",
        [y] if y else [],
    )
    income_map  = {dict(r)["month"]: dict(r)["income"]  for r in income_rows}
    expense_map = {dict(r)["month"]: dict(r)["expense"] for r in expense_rows}
    months = sorted(set(income_map) | set(expense_map))
    return [
        {"month": m, "income": income_map.get(m, 0), "expense": expense_map.get(m, 0)}
        for m in months
    ]
