"""
GradesRepository — data access for the grades domain.

Covers: grades, exams, subjects, grade_change_requests,
        result_approval_log (new), grade_scales (new).
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from backend.repositories.base import BaseRepository
from backend.core.exceptions import NotFoundError


class GradesRepository(BaseRepository):
    table = "grades"

    # ── Exams ─────────────────────────────────────────────────────────────────

    def list_exams(self, academic_year_id: int | None = None) -> list[dict]:
        where = "1=1"
        params: list = []
        if academic_year_id:
            where = "academic_year_id = ?"
            params.append(academic_year_id)
        return self._q(
            f"SELECT * FROM exams WHERE {where} ORDER BY start_date DESC, name",
            params,
        )

    def get_exam(self, exam_id: int) -> dict | None:
        return self._one("SELECT * FROM exams WHERE id = ?", (exam_id,))

    def get_exam_or_raise(self, exam_id: int) -> dict:
        e = self.get_exam(exam_id)
        if not e:
            raise NotFoundError("Exam", exam_id)
        return e

    # ── Grades / results ──────────────────────────────────────────────────────

    def get_grade(self, grade_id: int) -> dict | None:
        return self._one(
            """SELECT g.*,
                      s.first_name || ' ' || s.last_name AS student_name,
                      s.admission_no,
                      subj.name AS subject_name,
                      e.name AS exam_name
               FROM grades g
               JOIN students s ON s.id = g.student_id
               JOIN subjects subj ON subj.id = g.subject_id
               JOIN exams e ON e.id = g.exam_id
               WHERE g.id = ?""",
            (grade_id,),
        )

    def get_grade_or_raise(self, grade_id: int) -> dict:
        g = self.get_grade(grade_id)
        if not g:
            raise NotFoundError("Grade record", grade_id)
        return g

    def get_sheet(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
    ) -> list[dict]:
        return self._q(
            """SELECT g.*, s.first_name || ' ' || s.last_name AS student_name, s.admission_no
               FROM grades g
               JOIN students s ON s.id = g.student_id
               WHERE g.exam_id = ? AND s.class_id = ? AND g.subject_id = ?
               ORDER BY s.last_name, s.first_name""",
            (exam_id, class_id, subject_id),
        )

    def upsert_grade(self, data: dict) -> int:
        """Insert or update a grade entry. Returns the grade id."""
        existing = self._one(
            "SELECT id FROM grades WHERE student_id=? AND exam_id=? AND subject_id=?",
            (data["student_id"], data["exam_id"], data["subject_id"]),
        )
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            self.conn.execute(
                """UPDATE grades
                   SET score=?, max_score=?, grade_letter=?, remarks=?, status='draft'
                   WHERE id=?""",
                (data["score"], data["max_score"], data.get("grade_letter", ""),
                 data.get("remarks", ""), existing["id"]),
            )
            return existing["id"]
        else:
            return self._exec(
                """INSERT INTO grades
                   (student_id, exam_id, subject_id, score, max_score,
                    grade_letter, remarks, entered_by, status)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    data["student_id"], data["exam_id"], data["subject_id"],
                    data["score"], data["max_score"],
                    data.get("grade_letter", ""), data.get("remarks", ""),
                    data.get("entered_by"), "draft",
                ),
            )

    def update_grade_status(self, grade_id: int, new_status: str, actor_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if new_status == "approved":
            self.conn.execute(
                "UPDATE grades SET status=?, approved_by=? WHERE id=?",
                (new_status, actor_id, grade_id),
            )
        else:
            self.conn.execute(
                "UPDATE grades SET status=? WHERE id=?",
                (new_status, grade_id),
            )

    def bulk_update_status(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        new_status: str,
        from_status: str,
        actor_id: int,
    ) -> int:
        """Update status for all grades in a class+subject+exam batch. Returns row count."""
        cur = self.conn.execute(
            """UPDATE grades SET status=?, approved_by=CASE WHEN ? = 'approved' THEN ? ELSE approved_by END
               WHERE exam_id=? AND subject_id=?
                 AND student_id IN (SELECT id FROM students WHERE class_id=?)
                 AND status=?""",
            (new_status, new_status, actor_id, exam_id, subject_id, class_id, from_status),
        )
        return cur.rowcount

    # ── Approval log (new table) ──────────────────────────────────────────────

    def log_approval(
        self,
        grade_id: int,
        from_status: str,
        to_status: str,
        action: str,
        actor_id: int,
        comment: str = "",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO result_approval_log
               (grade_id, from_status, to_status, action, actor_id, comment, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (grade_id, from_status, to_status, action, actor_id, comment, now),
        )

    def get_approval_log(self, grade_id: int) -> list[dict]:
        return self._q(
            """SELECT ral.*, u.full_name AS actor_name, u.role AS actor_role
               FROM result_approval_log ral
               LEFT JOIN users u ON u.id = ral.actor_id
               WHERE ral.grade_id = ?
               ORDER BY ral.created_at ASC""",
            (grade_id,),
        )

    # ── Change requests ───────────────────────────────────────────────────────

    def list_change_requests(
        self, status: str = "pending", requested_by: int | None = None
    ) -> list[dict]:
        params: list = [status]
        extra = ""
        if requested_by is not None:
            extra = "AND gcr.requested_by = ?"
            params.append(requested_by)
        return self._q(
            f"""SELECT gcr.*,
                      s.first_name || ' ' || s.last_name AS student_name,
                      s.admission_no,
                      subj.name AS subject_name,
                      e.name AS exam_name
               FROM grade_change_requests gcr
               JOIN grades g     ON g.id   = gcr.grade_id
               JOIN students s   ON s.id   = g.student_id
               JOIN subjects subj ON subj.id = g.subject_id
               JOIN exams e      ON e.id   = g.exam_id
               WHERE gcr.status = ? {extra}
               ORDER BY gcr.created_at DESC""",
            params,
        )

    def get_change_request(self, cr_id: int) -> dict | None:
        return self._one(
            """SELECT gcr.*, g.score AS current_score, g.max_score AS current_max, g.status AS grade_status
               FROM grade_change_requests gcr
               JOIN grades g ON g.id = gcr.grade_id
               WHERE gcr.id = ?""",
            (cr_id,),
        )

    def insert_change_request(
        self,
        grade_id: int,
        proposed_score: float,
        proposed_max: float,
        reason: str,
        requested_by: int,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        return self._exec(
            """INSERT INTO grade_change_requests
               (grade_id, requested_by, proposed_score, proposed_max, reason, status, created_at)
               VALUES (?,?,?,?,?,'pending',?)""",
            (grade_id, requested_by, proposed_score, proposed_max, reason, now),
        )

    def update_change_request(
        self,
        cr_id: int,
        new_status: str,
        reviewed_by: int,
        note: str = "",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """UPDATE grade_change_requests
               SET status=?, reviewed_by=?, review_note=?, reviewed_at=?
               WHERE id=?""",
            (new_status, reviewed_by, note, now, cr_id),
        )

    # ── Grade scales (new table) ──────────────────────────────────────────────

    def get_grade_scale(self, academic_year_id: int) -> list[dict]:
        return self._q(
            "SELECT * FROM grade_scales WHERE academic_year_id = ? ORDER BY min_pct DESC",
            (academic_year_id,),
        )

    # ── Subjects ──────────────────────────────────────────────────────────────

    def list_subjects(self, class_id: int | None = None) -> list[dict]:
        if class_id:
            return self._q(
                """SELECT DISTINCT subj.*
                   FROM subjects subj
                   JOIN grades g ON g.subject_id = subj.id
                   JOIN students st ON st.id = g.student_id
                   WHERE st.class_id = ?
                   UNION
                   SELECT subj.* FROM subjects subj
                   JOIN teacher_subjects ts ON ts.subject_id = subj.id
                   WHERE subj.grade_level = (SELECT grade_level FROM classes WHERE id=?)
                   ORDER BY name""",
                (class_id, class_id),
            )
        return self._q("SELECT * FROM subjects ORDER BY name")

    # ── Pending approval summary ──────────────────────────────────────────────

    def pending_approval_summary(self) -> list[dict]:
        return self._q(
            """SELECT g.subject_id, g.exam_id, st.class_id,
                      subj.name AS subject_name,
                      e.name AS exam_name,
                      c.name AS class_name,
                      COUNT(g.id) AS count
               FROM grades g
               JOIN students st    ON st.id   = g.student_id
               JOIN subjects subj  ON subj.id = g.subject_id
               JOIN exams e        ON e.id    = g.exam_id
               JOIN classes c      ON c.id    = st.class_id
               WHERE g.status IN ('submitted', 'submitted_locked', 'under_review')
               GROUP BY g.subject_id, g.exam_id, st.class_id
               ORDER BY e.name, c.name, subj.name"""
        )
