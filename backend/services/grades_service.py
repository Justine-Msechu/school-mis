"""
GradesApprovalService — business logic for the grade approval workflow.

Wraps the state machine from domain/grades/workflow.py.
All grade status mutations go through here.
"""

from __future__ import annotations
import sqlite3

from backend.core.exceptions import BusinessRuleError, NotFoundError
from backend.core.audit import AuditService
from backend.core.events import event_bus, Events
from backend.domain.grades.workflow import transition, available_transitions
from backend.domain.grades.engine import GradingEngine, StudentScore
from backend.repositories.grades_repo import GradesRepository


class GradesApprovalService:
    def __init__(self, conn: sqlite3.Connection):
        self.repo  = GradesRepository(conn)
        self.conn  = conn
        self.audit = AuditService(conn)

    def _engine(self, academic_year_id: int | None = None) -> GradingEngine:
        if academic_year_id:
            scale_rows = self.repo.get_grade_scale(academic_year_id)
            if scale_rows:
                return GradingEngine.from_db_rows(scale_rows)
        return GradingEngine()  # default scale

    # ── Grade entry ───────────────────────────────────────────────────────────

    def save_draft(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        entries: list[dict],  # [{student_id, score, max_score, remarks?}]
        actor: dict,
    ) -> int:
        """Save/update grade entries as DRAFT. Applies grading engine."""
        exam = self.repo.get_exam_or_raise(exam_id)

        # Get scale for this year
        engine = self._engine(exam.get("academic_year_id"))

        saved = 0
        for entry in entries:
            score = float(entry.get("score", 0))
            max_score = float(entry.get("max_score", 100))

            if max_score > 0:
                gr = engine.grade(score, max_score)
                grade_letter = gr.grade_label
            else:
                grade_letter = ""

            self.repo.upsert_grade({
                "student_id":   entry["student_id"],
                "exam_id":      exam_id,
                "subject_id":   subject_id,
                "score":        score,
                "max_score":    max_score,
                "grade_letter": grade_letter,
                "remarks":      entry.get("remarks", ""),
                "entered_by":   actor.get("id"),
            })
            saved += 1

        self.conn.commit()
        return saved

    # ── Workflow transitions ───────────────────────────────────────────────────

    def submit(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        actor: dict,
    ) -> int:
        """Submit all draft grades for a class+subject+exam for review."""
        updated = self.repo.bulk_update_status(
            exam_id, class_id, subject_id,
            new_status="submitted",
            from_status="draft",
            actor_id=actor["id"],
        )
        if updated == 0:
            # Also accept returned → submitted
            updated = self.repo.bulk_update_status(
                exam_id, class_id, subject_id,
                new_status="submitted",
                from_status="returned",
                actor_id=actor["id"],
            )
        if updated == 0:
            raise BusinessRuleError(
                "No grades in 'draft' or 'returned' state to submit for this class/subject/exam",
                rule="nothing_to_submit",
            )
        self.conn.commit()

        self.audit.log("grades", exam_id, "SUBMIT", actor,
                       detail=f"class={class_id} subject={subject_id} count={updated}")

        event_bus.emit(Events.GRADES_SUBMITTED, {
            "exam_id": exam_id, "class_id": class_id, "subject_id": subject_id,
            "count": updated, "submitted_by": actor.get("id"),
        }, actor_id=actor.get("id"), actor_role=actor.get("role"))

        return updated

    def begin_review(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        actor: dict,
    ) -> int:
        updated = self.repo.bulk_update_status(
            exam_id, class_id, subject_id,
            new_status="under_review",
            from_status="submitted",
            actor_id=actor["id"],
        )
        if updated == 0:
            updated = self.repo.bulk_update_status(
                exam_id, class_id, subject_id,
                new_status="under_review",
                from_status="submitted_locked",  # legacy status
                actor_id=actor["id"],
            )
        self.conn.commit()
        return updated

    def approve(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        actor: dict,
        comment: str = "",
    ) -> int:
        # Try from submitted or under_review
        updated = self.repo.bulk_update_status(
            exam_id, class_id, subject_id,
            new_status="approved",
            from_status="under_review",
            actor_id=actor["id"],
        )
        if updated == 0:
            updated = self.repo.bulk_update_status(
                exam_id, class_id, subject_id,
                new_status="approved",
                from_status="submitted",
                actor_id=actor["id"],
            )
        if updated == 0:
            updated = self.repo.bulk_update_status(
                exam_id, class_id, subject_id,
                new_status="approved",
                from_status="submitted_locked",
                actor_id=actor["id"],
            )
        if updated == 0:
            raise BusinessRuleError(
                "No grades in an approvable state for this batch",
                rule="nothing_to_approve",
            )
        self.conn.commit()

        self.audit.log("grades", exam_id, "APPROVE", actor,
                       detail=f"class={class_id} subject={subject_id} count={updated} comment={comment}")

        event_bus.emit(Events.GRADES_APPROVED, {
            "exam_id": exam_id, "class_id": class_id, "subject_id": subject_id,
            "count": updated, "approved_by": actor.get("id"),
        }, actor_id=actor.get("id"), actor_role=actor.get("role"))

        return updated

    def return_for_correction(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        reason: str,
        actor: dict,
    ) -> int:
        updated = self.repo.bulk_update_status(
            exam_id, class_id, subject_id,
            new_status="returned",
            from_status="under_review",
            actor_id=actor["id"],
        )
        if updated == 0:
            updated = self.repo.bulk_update_status(
                exam_id, class_id, subject_id,
                new_status="returned",
                from_status="submitted",
                actor_id=actor["id"],
            )
        self.conn.commit()

        self.audit.log("grades", exam_id, "RETURN", actor,
                       detail=f"class={class_id} subject={subject_id} reason={reason}")

        event_bus.emit(Events.GRADES_RETURNED, {
            "exam_id": exam_id, "class_id": class_id, "subject_id": subject_id,
            "reason": reason, "returned_by": actor.get("id"),
        }, actor_id=actor.get("id"))

        return updated

    def publish(
        self,
        exam_id: int,
        class_id: int,
        subject_id: int,
        actor: dict,
    ) -> int:
        updated = self.repo.bulk_update_status(
            exam_id, class_id, subject_id,
            new_status="published",
            from_status="approved",
            actor_id=actor["id"],
        )
        if updated == 0:
            raise BusinessRuleError(
                "No approved grades to publish for this batch",
                rule="nothing_to_publish",
            )
        self.conn.commit()

        self.audit.log("grades", exam_id, "PUBLISH", actor,
                       detail=f"class={class_id} subject={subject_id} count={updated}")

        event_bus.emit(Events.GRADES_PUBLISHED, {
            "exam_id": exam_id, "class_id": class_id, "subject_id": subject_id,
            "count": updated, "published_by": actor.get("id"),
        }, actor_id=actor.get("id"))

        return updated

    # ── Change requests ───────────────────────────────────────────────────────

    def request_change(
        self,
        grade_id: int,
        proposed_score: float,
        proposed_max: float,
        reason: str,
        actor: dict,
    ) -> int:
        grade = self.repo.get_grade_or_raise(grade_id)

        if grade["status"] not in ("approved", "published", "locked"):
            raise BusinessRuleError(
                "Change requests can only be made for approved or published grades",
                rule="change_request_status",
            )

        cr_id = self.repo.insert_change_request(
            grade_id=grade_id,
            proposed_score=proposed_score,
            proposed_max=proposed_max,
            reason=reason,
            requested_by=actor["id"],
        )
        self.conn.commit()

        self.audit.log("grade_change_requests", cr_id, "INSERT", actor,
                       after={"grade_id": grade_id, "proposed_score": proposed_score, "reason": reason})

        event_bus.emit(Events.CHANGE_REQUEST_CREATED, {
            "cr_id": cr_id, "grade_id": grade_id, "requested_by": actor.get("id"),
        }, actor_id=actor.get("id"))

        return cr_id

    def resolve_change_request(
        self,
        cr_id: int,
        approved: bool,
        comment: str,
        actor: dict,
    ) -> None:
        cr = self.repo.get_change_request(cr_id)
        if not cr:
            raise NotFoundError("Change request", cr_id)
        if cr["status"] != "pending":
            raise BusinessRuleError(f"Change request is already '{cr['status']}'")

        new_status = "approved" if approved else "rejected"
        self.repo.update_change_request(cr_id, new_status, actor["id"], comment)

        if approved:
            # Apply the change to the original grade
            engine = self._engine()
            gr = engine.grade(cr["proposed_score"], cr["proposed_max"])
            self.conn.execute(
                "UPDATE grades SET score=?, max_score=?, grade_letter=? WHERE id=?",
                (cr["proposed_score"], cr["proposed_max"], gr.grade_label, cr["grade_id"]),
            )

        self.conn.commit()

        self.audit.log("grade_change_requests", cr_id, "RESOLVE", actor,
                       before={"status": "pending"},
                       after={"status": new_status, "comment": comment})

        event_bus.emit(Events.CHANGE_REQUEST_RESOLVED, {
            "cr_id": cr_id, "grade_id": cr["grade_id"], "approved": approved,
            "resolved_by": actor.get("id"),
        }, actor_id=actor.get("id"))

    # ── Class rankings ────────────────────────────────────────────────────────

    def get_class_rankings(
        self,
        exam_id: int,
        class_id: int,
        academic_year_id: int | None = None,
    ) -> list[dict]:
        """Compute per-student totals and rank the class."""
        rows = self.repo._q(
            """SELECT g.student_id,
                      s.first_name || ' ' || s.last_name AS student_name,
                      s.admission_no,
                      SUM(g.score) AS total_score,
                      SUM(g.max_score) AS total_max
               FROM grades g
               JOIN students s ON s.id = g.student_id
               WHERE g.exam_id = ? AND s.class_id = ? AND g.status IN ('approved','published')
               GROUP BY g.student_id
               HAVING total_max > 0""",
            (exam_id, class_id),
        )
        engine = self._engine(academic_year_id)
        scores = [StudentScore(r["student_id"], r["total_score"], r["total_max"]) for r in rows]
        ranked = engine.rank(scores)

        # Merge student info back
        info = {r["student_id"]: r for r in rows}
        return [
            {
                **info.get(r.student_id, {}),
                "total_score": r.marks,
                "total_max":   r.total,
                "percentage":  r.percentage,
                "grade_label": r.grade_label,
                "gpa_points":  r.gpa_points,
                "rank":        r.rank,
            }
            for r in ranked
        ]
