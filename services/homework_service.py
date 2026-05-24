"""
services/homework_service.py — Teachers create assignments; students submit.
All operations are scoped to the teacher's assigned class/subject combos.
"""

from database.db import fetch_all, fetch_one, execute
from services.base import BaseService, ServiceError


class HomeworkService(BaseService):

    def create_assignment(self, class_id: int, subject_id: int,
                          title: str, description: str,
                          deadline: str, max_points: float = 10) -> int:
        """Teacher posts a homework assignment for a class/subject."""
        self._require_permission("homework.assign")

        from auth.rbac import check_subject_access
        if not check_subject_access(class_id, subject_id):
            raise ServiceError("You are not assigned to teach this subject in this class.")

        if not title.strip():
            raise ServiceError("Title is required.")
        if not deadline:
            raise ServiceError("Deadline is required.")

        teacher_id = (self._session.user or {}).get("teacher_id")
        row_id = execute(
            """INSERT INTO homework_assignments
               (class_id, subject_id, teacher_id, title, description,
                deadline, max_points, created_by)
               VALUES (?,?,?,?,?,?,?,?)""",
            (class_id, subject_id, teacher_id,
             title.strip(), description.strip(), deadline, max_points,
             self._session.user_id)
        )
        self._audit("homework_created", "homework_assignments", row_id,
                    detail=f"Class {class_id} / Subject {subject_id}: '{title}'")
        return row_id

    def get_assignments(self, class_id: int, subject_id: int | None = None) -> list[dict]:
        """Return assignments for a class, optionally filtered by subject."""
        self._require_permission("homework.view")

        from auth.rbac import check_class_access
        if not check_class_access(class_id):
            raise ServiceError("You do not have access to this class.")

        sql = """SELECT ha.*, s.name AS subject_name, c.name AS class_name,
                        u.full_name AS created_by_name,
                        (SELECT COUNT(*) FROM homework_submissions hs
                         WHERE hs.assignment_id = ha.id) AS submission_count
                 FROM homework_assignments ha
                 JOIN subjects s ON s.id = ha.subject_id
                 JOIN classes  c ON c.id = ha.class_id
                 LEFT JOIN users u ON u.id = ha.created_by
                 WHERE ha.class_id = ?"""
        params = [class_id]
        if subject_id:
            sql += " AND ha.subject_id = ?"
            params.append(subject_id)
        sql += " ORDER BY ha.deadline DESC"

        return [dict(r) for r in fetch_all(sql, params)]

    def get_submissions(self, assignment_id: int) -> list[dict]:
        """Teacher views all submissions for an assignment."""
        self._require_permission("homework.grade")

        hw = fetch_one("SELECT * FROM homework_assignments WHERE id=?", (assignment_id,))
        if not hw:
            raise ServiceError("Assignment not found.")

        from auth.rbac import check_subject_access
        if not check_subject_access(hw["class_id"], hw["subject_id"]):
            raise ServiceError("You do not have access to this assignment.")

        rows = fetch_all(
            """SELECT hs.*,
                      s.first_name||' '||s.last_name AS student_name,
                      s.admission_no
               FROM homework_submissions hs
               JOIN students s ON s.id = hs.student_id
               WHERE hs.assignment_id = ?
               ORDER BY s.last_name, s.first_name""",
            (assignment_id,)
        )
        return [dict(r) for r in rows]

    def grade_submission(self, submission_id: int,
                         points: float, feedback: str = "") -> None:
        """Teacher grades a submitted homework."""
        self._require_permission("homework.grade")

        sub = fetch_one(
            """SELECT hs.*, ha.class_id, ha.subject_id, ha.max_points
               FROM homework_submissions hs
               JOIN homework_assignments ha ON ha.id = hs.assignment_id
               WHERE hs.id = ?""",
            (submission_id,)
        )
        if not sub:
            raise ServiceError("Submission not found.")

        from auth.rbac import check_subject_access
        if not check_subject_access(sub["class_id"], sub["subject_id"]):
            raise ServiceError("You do not have access to this submission.")

        if points < 0 or points > (sub["max_points"] or 100):
            raise ServiceError(
                f"Points must be between 0 and {sub['max_points'] or 100}."
            )

        execute(
            """UPDATE homework_submissions
               SET points_earned=?, feedback=?, status='graded',
                   graded_by=?, graded_at=datetime('now')
               WHERE id=?""",
            (points, feedback, self._session.user_id, submission_id)
        )

    def delete_assignment(self, assignment_id: int) -> None:
        """Teacher deletes an assignment (only if no submissions yet)."""
        self._require_permission("homework.assign")

        hw = fetch_one("SELECT * FROM homework_assignments WHERE id=?", (assignment_id,))
        if not hw:
            raise ServiceError("Assignment not found.")

        from auth.rbac import check_subject_access
        if not check_subject_access(hw["class_id"], hw["subject_id"]):
            raise ServiceError("You do not have access to this assignment.")

        sub_count = fetch_one(
            "SELECT COUNT(*) AS n FROM homework_submissions WHERE assignment_id=?",
            (assignment_id,)
        )
        if sub_count and sub_count["n"] > 0:
            raise ServiceError(
                "Cannot delete an assignment that already has submissions. "
                "Extend the deadline or close it instead."
            )
        execute("DELETE FROM homework_assignments WHERE id=?", (assignment_id,))


homework_service = HomeworkService()
