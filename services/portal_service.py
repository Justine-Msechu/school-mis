"""
services/portal_service.py — Data access for student and parent portals.

All methods enforce OWN-scope: a student only ever sees their own record;
a parent only ever sees their linked children's records.  No crossover.
"""

from database.db import fetch_all, fetch_one, execute
from services.base import BaseService, ServiceError


class PortalService(BaseService):

    # ── Student: own approved grades ─────────────────────────────────────────

    def get_my_grades(self) -> list[dict]:
        """
        Returns approved grades for the logged-in student, grouped by exam.
        Raises ServiceError if the user is not linked to a student account.
        """
        self._require_permission("portal.student.grades")
        student_id = self._my_student_id()

        rows = fetch_all(
            """SELECT e.name AS exam_name, e.term, ay.label AS year_label,
                      s.name AS subject_name, s.code AS subject_code,
                      g.score, g.max_score, g.grade_letter, g.remarks,
                      g.status
               FROM grades g
               JOIN exams    e  ON e.id  = g.exam_id
               JOIN subjects s  ON s.id  = g.subject_id
               LEFT JOIN academic_years ay ON ay.id = e.academic_year_id
               WHERE g.student_id = ? AND g.status = 'approved'
               ORDER BY ay.label DESC, e.term, s.name""",
            (student_id,),
        )
        return [dict(r) for r in rows]

    def get_my_homework(self) -> list[dict]:
        """
        Returns homework assignments for the student's class, with submission status.
        """
        self._require_permission("portal.student.homework")
        student_id = self._my_student_id()

        student = fetch_one(
            "SELECT class_id FROM students WHERE id=?", (student_id,)
        )
        if not student:
            raise ServiceError("Student record not found.")
        class_id = student["class_id"]

        rows = fetch_all(
            """SELECT ha.id AS assignment_id, ha.title, ha.description,
                      ha.deadline, ha.max_points,
                      s.name AS subject_name,
                      hs.id AS submission_id, hs.submitted_at,
                      hs.file_path, hs.notes, hs.status AS sub_status,
                      hs.points_earned, hs.feedback
               FROM homework_assignments ha
               JOIN subjects s ON s.id = ha.subject_id
               LEFT JOIN homework_submissions hs
                 ON hs.assignment_id = ha.id AND hs.student_id = ?
               WHERE ha.class_id = ?
               ORDER BY ha.deadline DESC""",
            (student_id, class_id),
        )
        return [dict(r) for r in rows]

    def submit_homework(self, assignment_id: int, file_path: str, notes: str) -> int:
        """Student submits (or re-submits) a homework file."""
        self._require_permission("portal.student.homework")
        student_id = self._my_student_id()

        hw = fetch_one(
            "SELECT id, deadline FROM homework_assignments WHERE id=?",
            (assignment_id,)
        )
        if not hw:
            raise ServiceError("Assignment not found.")

        import datetime
        now = datetime.datetime.now()
        deadline = datetime.datetime.fromisoformat(hw["deadline"])
        status = "late" if now > deadline else "submitted"

        existing = fetch_one(
            "SELECT id FROM homework_submissions WHERE assignment_id=? AND student_id=?",
            (assignment_id, student_id)
        )
        if existing:
            execute(
                """UPDATE homework_submissions
                   SET file_path=?, notes=?, submitted_at=datetime('now'), status=?
                   WHERE id=?""",
                (file_path, notes, status, existing["id"])
            )
            return existing["id"]
        else:
            row_id = execute(
                """INSERT INTO homework_submissions
                   (assignment_id, student_id, file_path, notes, status)
                   VALUES (?,?,?,?,?)""",
                (assignment_id, student_id, file_path, notes, status)
            )
            return row_id

    # ── Parent: children's approved grades ───────────────────────────────────

    def get_children(self) -> list[dict]:
        """Returns the list of children linked to the logged-in parent."""
        self._require_permission("portal.parent.grades")
        ids = self._my_children_ids()
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = fetch_all(
            f"""SELECT s.id, s.first_name||' '||s.last_name AS name,
                       s.admission_no, c.name AS class_name,
                       pa.relation
                FROM students s
                LEFT JOIN classes c ON c.id = s.class_id
                JOIN parent_portal_accounts pa
                  ON pa.student_id = s.id AND pa.user_id = ?
                WHERE s.id IN ({placeholders})""",
            (self._session.user_id, *ids),
        )
        return [dict(r) for r in rows]

    def get_child_grades(self, student_id: int) -> list[dict]:
        """Returns approved grades for one child. Verifies the child belongs to this parent."""
        self._require_permission("portal.parent.grades")
        self._verify_child(student_id)

        rows = fetch_all(
            """SELECT e.name AS exam_name, e.term, ay.label AS year_label,
                      s.name AS subject_name,
                      g.score, g.max_score, g.grade_letter, g.remarks
               FROM grades g
               JOIN exams    e  ON e.id  = g.exam_id
               JOIN subjects s  ON s.id  = g.subject_id
               LEFT JOIN academic_years ay ON ay.id = e.academic_year_id
               WHERE g.student_id = ? AND g.status = 'approved'
               ORDER BY ay.label DESC, e.term, s.name""",
            (student_id,),
        )
        return [dict(r) for r in rows]

    def get_child_fee_summary(self, student_id: int) -> dict:
        """Returns the fee balance and recent payments for one child."""
        self._require_permission("portal.parent.fees")
        self._verify_child(student_id)

        allocations = fetch_all(
            """SELECT fa.amount_due, fa.amount_paid, fa.balance,
                      fa.term, ay.label AS year_label, fs.name AS fee_name
               FROM fee_allocations fa
               JOIN fee_structures fs ON fs.id = fa.fee_structure_id
               LEFT JOIN academic_years ay ON ay.id = fs.academic_year_id
               WHERE fa.student_id = ?
               ORDER BY ay.label DESC, fa.term""",
            (student_id,),
        )
        payments = fetch_all(
            """SELECT fp.amount, fp.payment_date, fp.payment_method, fp.reference_no
               FROM fee_payments fp
               WHERE fp.student_id = ?
               ORDER BY fp.payment_date DESC
               LIMIT 10""",
            (student_id,),
        )
        total_due  = sum(r["amount_due"]  or 0 for r in allocations)
        total_paid = sum(r["amount_paid"] or 0 for r in allocations)
        return {
            "allocations": [dict(r) for r in allocations],
            "recent_payments": [dict(r) for r in payments],
            "total_due": total_due,
            "total_paid": total_paid,
            "balance": total_due - total_paid,
        }

    # ── Leave requests ────────────────────────────────────────────────────────

    def submit_leave_request(self, student_id: int,
                             date_from: str, date_to: str, reason: str) -> int:
        """Parent submits a leave request for their child."""
        self._require_permission("portal.parent.leave")
        self._verify_child(student_id)
        if not reason.strip():
            raise ServiceError("Reason is required.")
        row_id = execute(
            """INSERT INTO leave_requests
               (student_id, submitted_by, date_from, date_to, reason)
               VALUES (?,?,?,?,?)""",
            (student_id, self._session.user_id, date_from, date_to, reason.strip())
        )
        self._audit("leave_request_submitted", "leave_requests", row_id,
                    detail=f"Student {student_id}: {date_from} to {date_to}")
        return row_id

    def get_my_leave_requests(self, student_id: int) -> list[dict]:
        """Returns leave requests submitted by this parent for one child."""
        self._require_permission("portal.parent.leave")
        self._verify_child(student_id)
        rows = fetch_all(
            """SELECT lr.*, s.first_name||' '||s.last_name AS student_name,
                      u.full_name AS reviewed_by_name
               FROM leave_requests lr
               JOIN students s ON s.id = lr.student_id
               LEFT JOIN users u ON u.id = lr.reviewed_by
               WHERE lr.student_id = ? AND lr.submitted_by = ?
               ORDER BY lr.created_at DESC""",
            (student_id, self._session.user_id)
        )
        return [dict(r) for r in rows]

    # ── Staff: review leave requests ─────────────────────────────────────────

    def get_all_leave_requests(self, status: str = "pending") -> list[dict]:
        """Academic officers and class teachers review leave requests."""
        self._require_permission("leave.review")
        rows = fetch_all(
            """SELECT lr.*, s.first_name||' '||s.last_name AS student_name,
                      c.name AS class_name,
                      u.full_name AS submitted_by_name,
                      rv.full_name AS reviewed_by_name
               FROM leave_requests lr
               JOIN students s ON s.id = lr.student_id
               LEFT JOIN classes c ON c.id = s.class_id
               LEFT JOIN users u  ON u.id  = lr.submitted_by
               LEFT JOIN users rv ON rv.id = lr.reviewed_by
               WHERE lr.status = ?
               ORDER BY lr.created_at DESC""",
            (status,)
        )
        return [dict(r) for r in rows]

    def review_leave_request(self, request_id: int,
                             approved: bool, note: str = "") -> None:
        """Approve or reject a leave request."""
        self._require_permission("leave.review")
        req = fetch_one("SELECT * FROM leave_requests WHERE id=?", (request_id,))
        if not req:
            raise ServiceError("Leave request not found.")
        if req["status"] != "pending":
            raise ServiceError("This request has already been reviewed.")
        new_status = "approved" if approved else "rejected"
        execute(
            """UPDATE leave_requests
               SET status=?, reviewed_by=?, review_note=?,
                   reviewed_at=datetime('now')
               WHERE id=?""",
            (new_status, self._session.user_id, note, request_id)
        )
        self._audit("leave_request_reviewed", "leave_requests", request_id,
                    detail=f"{new_status}: {note[:80]}")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _my_student_id(self) -> int:
        from auth.rbac import get_portal_student_id
        sid = get_portal_student_id()
        if not sid:
            raise ServiceError(
                "Your account is not linked to a student record. "
                "Contact the school administrator."
            )
        return sid

    def _my_children_ids(self) -> list[int]:
        from auth.rbac import get_portal_children_ids
        return get_portal_children_ids()

    def _verify_child(self, student_id: int) -> None:
        """Raise ServiceError if student_id is not a linked child of this parent."""
        children = self._my_children_ids()
        if student_id not in children:
            raise ServiceError("You do not have access to this student's records.")


portal_service = PortalService()
