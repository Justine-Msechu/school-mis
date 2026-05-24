"""
services/grades_service.py — Exam and grades domain business logic.

Flow for every graded exam:
  Teacher enters scores (draft) → Teacher submits → Academic approves → Admin/Academic publishes
"""

from __future__ import annotations
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute, execute_many


def _letter_grade(score: float, max_score: float = 100) -> str:
    """Tanzania PSLE-style letter grading."""
    pct = (score / max_score * 100) if max_score else 0
    if pct >= 75: return "A"
    if pct >= 65: return "B"
    if pct >= 50: return "C"
    if pct >= 30: return "D"
    return "F"


class GradesService(BaseService):

    # ── Exam management ───────────────────────────────────────────────────────

    def create_exam(
        self,
        name: str,
        academic_year_id: int,
        term: int,
        start_date: str = "",
        end_date: str = "",
    ) -> int:
        self._require_permission("grades.approve")
        if not name.strip():
            raise ServiceError("Exam name is required.")
        eid = execute(
            """INSERT INTO exams (name, academic_year_id, term, start_date, end_date)
               VALUES (?,?,?,?,?)""",
            (name.strip(), academic_year_id, term,
             start_date or None, end_date or None),
        )
        self._audit("exam_created", "exams", eid,
                    detail=f"{name} — Year {academic_year_id} T{term}")
        return eid

    def get_exams(
        self,
        academic_year_id: int | None = None,
        term: int | None = None,
    ) -> list[dict]:
        """Return exams, optionally filtered by year/term."""
        self._require_permission("grades.view")
        where, params = [], []
        if academic_year_id:
            where.append("e.academic_year_id=?"); params.append(academic_year_id)
        if term is not None:
            where.append("e.term=?"); params.append(term)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = fetch_all(
            f"""SELECT e.*, ay.label AS year_label
                FROM exams e
                LEFT JOIN academic_years ay ON ay.id=e.academic_year_id
                {clause} ORDER BY e.id DESC""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def update_exam_status(self, exam_id: int, status: str) -> None:
        """Lock or publish an exam. Publishing requires all grades to be approved."""
        self._require_permission("grades.publish")
        if status not in ("open", "locked", "published"):
            raise ServiceError("Invalid exam status.")
        exam = fetch_one("SELECT * FROM exams WHERE id=?", (exam_id,))
        if not exam:
            raise ServiceError("Exam not found.")

        if status == "published":
            unapproved = fetch_one(
                "SELECT COUNT(*) AS n FROM grades WHERE exam_id=? "
                "AND status NOT IN ('approved')",
                (exam_id,)
            )
            self._enforce(
                "grade.publish",
                subject=dict(exam),
                extra={"unapproved_count": unapproved["n"] if unapproved else 0},
            )

        execute("UPDATE exams SET status=? WHERE id=?", (status, exam_id))
        self._audit("exam_status_changed", "exams", exam_id,
                    before={"status": exam["status"]}, after={"status": status})

    # ── Subject helpers ───────────────────────────────────────────────────────

    def get_subjects(self) -> list[dict]:
        self._require_permission("grades.view")
        return [dict(r) for r in fetch_all("SELECT * FROM subjects ORDER BY name")]

    def get_subjects_for_teacher(self, class_id: int) -> list[dict]:
        """Return subjects this user (teacher) is assigned to for the given class."""
        self._require_permission("grades.enter")
        user = self._session.user or {}
        teacher_id = user.get("teacher_id")
        if not teacher_id:
            return []
        rows = fetch_all(
            """SELECT s.* FROM subjects s
               JOIN teacher_subjects ts ON ts.subject_id=s.id
               WHERE ts.teacher_id=? AND ts.class_id=?
               ORDER BY s.name""",
            (teacher_id, class_id),
        )
        return [dict(r) for r in rows]

    # ── Grade entry (teachers) ────────────────────────────────────────────────

    def get_grade_sheet(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
    ) -> list[dict]:
        """
        Return all students in a class with their current grade for this exam/subject.
        Used to pre-fill the entry table.
        """
        self._require_permission("grades.view")

        from auth.rbac import check_class_access, check_subject_access
        if not check_class_access(class_id):
            raise ServiceError("You do not have access to this class.")
        if not check_subject_access(class_id, subject_id):
            raise ServiceError(
                "You are not assigned to teach this subject in this class. "
                "Only your assigned subjects are accessible."
            )

        rows = fetch_all(
            """SELECT s.id AS student_id,
                      s.first_name||' '||s.last_name AS student_name,
                      s.admission_no,
                      g.id AS grade_id, g.score, g.max_score,
                      g.grade_letter, g.remarks, g.status
               FROM students s
               LEFT JOIN grades g
                 ON g.student_id=s.id AND g.exam_id=? AND g.subject_id=?
               WHERE s.class_id=? AND s.is_active=1
               ORDER BY s.last_name, s.first_name""",
            (exam_id, subject_id, class_id),
        )
        return [dict(r) for r in rows]

    # ── Lockdown enforcement ─────────────────────────────────────────────────

    def _check_grade_writable(self, exam_id: int, class_id: int, subject_id: int):
        """
        Raise ServiceError if any grades in this batch are past draft stage.
        Called before any save/update on grade entries by non-approvers.
        """
        locked = fetch_one(
            """SELECT COUNT(*) AS n FROM grades g
               JOIN students s ON s.id=g.student_id
               WHERE g.exam_id=? AND g.subject_id=? AND s.class_id=?
                 AND g.status IN ('submitted_locked','approved')""",
            (exam_id, subject_id, class_id),
        )
        if locked and locked["n"] > 0:
            raise ServiceError(
                "One or more grades in this batch are locked (submitted or approved). "
                "Use 'Request Change' to propose corrections."
            )

    def save_grades(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        entries: list[dict],
    ) -> int:
        """Bulk-upsert grades as 'draft'. Hard-blocked if any grade is locked/approved."""
        self._require_permission("grades.enter")

        from auth.rbac import check_class_access, check_subject_access
        if not check_class_access(class_id):
            raise ServiceError("You do not have access to this class.")
        if not check_subject_access(class_id, subject_id):
            raise ServiceError(
                "You are not assigned to teach this subject in this class."
            )

        exam = fetch_one("SELECT * FROM exams WHERE id=?", (exam_id,))
        if not exam:
            raise ServiceError("Exam not found.")

        self._enforce("grade.enter", subject=dict(exam),
                      extra={"exam_status": exam["status"]})

        # ── LOCKDOWN CHECK ────────────────────────────────────────────────────
        self._check_grade_writable(exam_id, class_id, subject_id)

        saved = 0
        for entry in entries:
            score = entry.get("score")
            if score is None:
                continue
            max_score = entry.get("max_score", 100) or 100
            letter = _letter_grade(float(score), float(max_score))
            execute(
                """INSERT INTO grades
                   (student_id, exam_id, subject_id, score, max_score,
                    grade_letter, remarks, entered_by, status)
                   VALUES (?,?,?,?,?,?,?,?,'draft')
                   ON CONFLICT(student_id, exam_id, subject_id) DO UPDATE SET
                     score=excluded.score, max_score=excluded.max_score,
                     grade_letter=excluded.grade_letter, remarks=excluded.remarks,
                     entered_by=excluded.entered_by, status='draft'""",
                (entry["student_id"], exam_id, subject_id,
                 score, max_score, letter,
                 entry.get("remarks", ""), self._session.user_id),
            )
            saved += 1

        self._audit("grades_saved", "grades",
                    detail=f"Exam {exam_id} class {class_id} subj {subject_id}: {saved} draft grades")
        return saved

    def submit_grades(self, exam_id: int, class_id: int, subject_id: int) -> int:
        """Finalize & submit: transitions grades from 'draft' → 'submitted_locked'."""
        self._require_permission("grades.enter")

        from auth.rbac import check_class_access, check_subject_access
        if not check_class_access(class_id):
            raise ServiceError("You do not have access to this class.")
        if not check_subject_access(class_id, subject_id):
            raise ServiceError("You are not assigned to teach this subject in this class.")

        exam = fetch_one("SELECT * FROM exams WHERE id=?", (exam_id,))
        if not exam:
            raise ServiceError("Exam not found.")
        self._enforce("grade.enter", subject=dict(exam),
                      extra={"exam_status": exam["status"]})

        count = fetch_one(
            """SELECT COUNT(*) AS n FROM grades g
               JOIN students s ON s.id=g.student_id
               WHERE g.exam_id=? AND g.subject_id=? AND s.class_id=? AND g.status='draft'""",
            (exam_id, subject_id, class_id),
        )
        if not count or count["n"] == 0:
            raise ServiceError("No draft grades to submit.")

        execute(
            """UPDATE grades SET status='submitted_locked'
               WHERE exam_id=? AND subject_id=?
                 AND student_id IN (SELECT id FROM students WHERE class_id=?)
                 AND status='draft'""",
            (exam_id, subject_id, class_id),
        )
        self._audit("grades_submitted_locked", "grades",
                    detail=f"Exam {exam_id} class {class_id} subj {subject_id}: "
                           f"{count['n']} locked for approval")
        return count["n"]

    # ── Grade Change Requests ─────────────────────────────────────────────────

    def request_grade_change(
        self, grade_id: int, proposed_score: float,
        proposed_max: float, reason: str,
    ) -> int:
        """Submit a change request for a locked/approved grade. Audited."""
        self._require_permission("grades.change_request")
        grade = fetch_one("SELECT * FROM grades WHERE id=?", (grade_id,))
        if not grade:
            raise ServiceError("Grade record not found.")
        if grade["status"] == "draft":
            raise ServiceError("Draft grades can be edited directly — no request needed.")
        if not reason.strip():
            raise ServiceError("A reason is required for grade change requests.")

        existing = fetch_one(
            "SELECT id FROM grade_change_requests WHERE grade_id=? AND status='pending'",
            (grade_id,),
        )
        if existing:
            raise ServiceError("A pending change request already exists for this grade.")

        req_id = execute(
            """INSERT INTO grade_change_requests
               (grade_id, requested_by, proposed_score, proposed_max, reason)
               VALUES (?,?,?,?,?)""",
            (grade_id, self._session.user_id, proposed_score, proposed_max, reason.strip()),
        )
        self._audit("grade_change_requested", "grade_change_requests", req_id,
                    detail=f"Grade {grade_id}: {proposed_score}/{proposed_max} — {reason[:60]}",
                    before={"score": grade["score"], "max_score": grade["max_score"],
                            "status": grade["status"]})
        return req_id

    def get_change_requests(self, status: str | None = "pending") -> list[dict]:
        self._require_permission("grades.change_request.review")
        where = f"WHERE gcr.status='{status}'" if status else ""
        rows = fetch_all(
            f"""SELECT gcr.*,
                       g.score AS current_score, g.max_score AS current_max,
                       g.grade_letter, g.status AS grade_status,
                       e.name AS exam_name, s.name AS subject_name,
                       st.first_name||' '||st.last_name AS student_name,
                       st.admission_no, c.name AS class_name,
                       u.full_name AS requested_by_name
                FROM grade_change_requests gcr
                JOIN grades g ON g.id=gcr.grade_id
                JOIN exams e ON e.id=g.exam_id
                JOIN subjects s ON s.id=g.subject_id
                JOIN students st ON st.id=g.student_id
                LEFT JOIN classes c ON c.id=st.class_id
                LEFT JOIN users u ON u.id=gcr.requested_by
                {where} ORDER BY gcr.id DESC""",
        )
        return [dict(r) for r in rows]

    def approve_change_request(self, request_id: int) -> None:
        """Apply the proposed change, update grade, mark request approved. Fully audited."""
        self._require_permission("grades.change_request.review")
        req = fetch_one("SELECT * FROM grade_change_requests WHERE id=?", (request_id,))
        if not req:
            raise ServiceError("Change request not found.")
        if req["status"] != "pending":
            raise ServiceError("This request has already been reviewed.")

        grade = fetch_one("SELECT * FROM grades WHERE id=?", (req["grade_id"],))
        if not grade:
            raise ServiceError("Grade record not found.")

        import datetime
        new_score   = req["proposed_score"]
        new_max     = req["proposed_max"] or 100
        new_letter  = _letter_grade(float(new_score), float(new_max))

        execute(
            """UPDATE grades SET score=?, max_score=?, grade_letter=?, approved_by=?
               WHERE id=?""",
            (new_score, new_max, new_letter, self._session.user_id, req["grade_id"]),
        )
        execute(
            """UPDATE grade_change_requests
               SET status='approved', reviewed_by=?, reviewed_at=?
               WHERE id=?""",
            (self._session.user_id, datetime.datetime.now().isoformat(), request_id),
        )
        self._audit("grade_change_approved", "grade_change_requests", request_id,
                    before={"score": grade["score"], "max_score": grade["max_score"]},
                    after={"score": new_score, "max_score": new_max})

    def reject_change_request(self, request_id: int, review_note: str) -> None:
        self._require_permission("grades.change_request.review")
        req = fetch_one("SELECT id, status FROM grade_change_requests WHERE id=?", (request_id,))
        if not req:
            raise ServiceError("Change request not found.")
        if req["status"] != "pending":
            raise ServiceError("This request has already been reviewed.")

        import datetime
        execute(
            """UPDATE grade_change_requests
               SET status='rejected', reviewed_by=?, reviewed_at=?, review_note=?
               WHERE id=?""",
            (self._session.user_id, datetime.datetime.now().isoformat(),
             (review_note or "").strip(), request_id),
        )
        self._audit("grade_change_rejected", "grade_change_requests", request_id)

    # ── Approval (academic officer / head teacher) ────────────────────────────

    def get_pending_submissions(self) -> list[dict]:
        """Return all grade batches awaiting approval."""
        self._require_permission("grades.approve")
        rows = fetch_all(
            """SELECT e.name AS exam_name, e.id AS exam_id, e.status AS exam_status,
                      c.name AS class_name, c.id AS class_id,
                      s.name AS subject_name, s.id AS subject_id,
                      COUNT(g.id) AS grade_count,
                      MAX(g.rowid) AS last_entry
               FROM grades g
               JOIN exams e   ON e.id=g.exam_id
               JOIN students st ON st.id=g.student_id
               JOIN classes c ON c.id=st.class_id
               JOIN subjects s ON s.id=g.subject_id
               WHERE g.status='submitted_locked'
               GROUP BY g.exam_id, c.id, g.subject_id
               ORDER BY e.id DESC, c.name, s.name""",
        )
        return [dict(r) for r in rows]

    def approve_grades(self, exam_id: int, class_id: int, subject_id: int) -> int:
        """Approve submitted grades for a class/subject/exam batch."""
        self._require_permission("grades.approve")

        exam = fetch_one("SELECT * FROM exams WHERE id=?", (exam_id,))
        if not exam:
            raise ServiceError("Exam not found.")

        self._enforce("grade.approve", subject=dict(exam))

        execute(
            """UPDATE grades SET status='approved', approved_by=?
               WHERE exam_id=? AND subject_id=?
                 AND student_id IN (SELECT id FROM students WHERE class_id=?)
                 AND status='submitted_locked'""",
            (self._session.user_id, exam_id, subject_id, class_id),
        )
        count = fetch_one(
            """SELECT COUNT(*) AS n FROM grades g
               JOIN students s ON s.id=g.student_id
               WHERE g.exam_id=? AND g.subject_id=? AND s.class_id=? AND g.status='approved'""",
            (exam_id, subject_id, class_id)
        )
        n = count["n"] if count else 0
        self._audit("grades_approved", "grades",
                    detail=f"Exam {exam_id} class {class_id} subj {subject_id}: {n} approved",
                    after={"approved_by": self._session.user_id})
        return n

    def reject_grades(self, exam_id: int, class_id: int, subject_id: int) -> int:
        """Send submitted grades back to draft (requires re-entry by teacher)."""
        self._require_permission("grades.approve")
        execute(
            """UPDATE grades SET status='draft', approved_by=NULL
               WHERE exam_id=? AND subject_id=?
                 AND student_id IN (SELECT id FROM students WHERE class_id=?)
                 AND status='submitted_locked'""",
            (exam_id, subject_id, class_id),
        )
        self._audit("grades_rejected", "grades",
                    detail=f"Exam {exam_id} class {class_id} subj {subject_id}: returned to draft")
        return 1

    # ── Result report ─────────────────────────────────────────────────────────

    def get_result_report(self, exam_id: int, class_id: int) -> dict:
        """
        Return structured result data for a class/exam.
        Includes per-subject scores, totals, averages, and rank.
        """
        self._require_permission("grades.view")

        from auth.rbac import check_class_access
        if not check_class_access(class_id):
            raise ServiceError("You do not have access to this class.")

        exam = fetch_one(
            """SELECT e.*, ay.label AS year_label
               FROM exams e LEFT JOIN academic_years ay ON ay.id=e.academic_year_id
               WHERE e.id=?""",
            (exam_id,)
        )
        if not exam:
            raise ServiceError("Exam not found.")

        cls = fetch_one("SELECT * FROM classes WHERE id=?", (class_id,))
        subjects = fetch_all(
            """SELECT DISTINCT s.id, s.name, s.code
               FROM subjects s
               JOIN grades g ON g.subject_id=s.id
               JOIN students st ON st.id=g.student_id
               WHERE g.exam_id=? AND st.class_id=?
               ORDER BY s.name""",
            (exam_id, class_id),
        )
        students = fetch_all(
            "SELECT * FROM students WHERE class_id=? AND is_active=1 ORDER BY last_name, first_name",
            (class_id,),
        )
        grades_rows = fetch_all(
            """SELECT g.student_id, g.subject_id, g.score, g.max_score,
                      g.grade_letter, g.status
               FROM grades g
               JOIN students s ON s.id=g.student_id
               WHERE g.exam_id=? AND s.class_id=?""",
            (exam_id, class_id),
        )
        # Index: grade_map[student_id][subject_id] = grade row
        grade_map: dict[int, dict] = {}
        for gr in grades_rows:
            grade_map.setdefault(gr["student_id"], {})[gr["subject_id"]] = dict(gr)

        subject_list = [dict(s) for s in subjects]
        rows = []
        for st in students:
            sid = st["id"]
            sg = grade_map.get(sid, {})
            total = sum(r["score"] for r in sg.values() if r.get("score") is not None)
            max_total = sum(r["max_score"] or 100 for r in sg.values() if r.get("score") is not None)
            avg = (total / max_total * 100) if max_total else None
            rows.append({
                "student_id":   sid,
                "student_name": f"{st['first_name']} {st['last_name']}",
                "admission_no": st["admission_no"],
                "grades":       sg,   # subject_id → grade row
                "total":        total,
                "max_total":    max_total,
                "average":      round(avg, 1) if avg is not None else None,
                "overall_grade": _letter_grade(total, max_total) if max_total else "—",
            })

        # Rank by total score (descending), only students with at least one grade
        graded = [r for r in rows if r["max_total"] > 0]
        graded.sort(key=lambda r: r["total"], reverse=True)
        rank = 1
        for i, r in enumerate(graded):
            if i > 0 and r["total"] < graded[i - 1]["total"]:
                rank = i + 1
            r["rank"] = rank

        for r in rows:
            if "rank" not in r:
                r["rank"] = "—"

        # GPA calculation for secondary schools (A=4,B=3,C=2,D=1,F=0)
        _gpa_map = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
        subj_credits = {s["id"]: (s.get("credit_hours") or 1) for s in subjects}
        for row in rows:
            total_pts   = sum(
                _gpa_map.get(row["grades"][sid].get("grade_letter", "F"), 0) * subj_credits.get(sid, 1)
                for sid in row["grades"]
                if row["grades"][sid].get("grade_letter")
            )
            total_creds = sum(subj_credits.get(sid, 1) for sid in row["grades"])
            row["gpa"] = round(total_pts / total_creds, 2) if total_creds > 0 else None

        from database.db import get_config
        school_type = get_config("school_type", "primary")

        return {
            "exam":        dict(exam),
            "class":       dict(cls) if cls else {},
            "subjects":    subject_list,
            "rows":        rows,
            "school_type": school_type,
        }


# Singleton
grades_service = GradesService()
