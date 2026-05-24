"""Year-end student promotion service."""
from __future__ import annotations
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute


class PromotionService(BaseService):

    def already_promoted(self, student_id: int, academic_year_id: int) -> bool:
        row = fetch_one(
            "SELECT id FROM student_promotions WHERE student_id=? AND academic_year_id=?",
            (student_id, academic_year_id)
        )
        return row is not None

    def promote_batch(
        self,
        academic_year_id: int,
        from_class_id: int,
        to_class_id: int,
        entries: list[dict],   # [{student_id, action, notes}]
    ) -> dict:
        """
        Bulk-process promotion decisions. Returns {promoted, held, graduated, skipped}.
        action: 'promote' → move to to_class_id
                'hold_back' → stays in from_class_id (no class change)
                'graduate' → is_active set to 0
        """
        self._require_permission("student.promote")
        if not entries:
            raise ServiceError("No students selected.")

        counts = {"promoted": 0, "held_back": 0, "graduated": 0, "skipped": 0}
        for entry in entries:
            sid    = entry["student_id"]
            action = entry.get("action", "promote")
            notes  = entry.get("notes", "")

            if self.already_promoted(sid, academic_year_id):
                counts["skipped"] += 1
                continue

            if action == "promote":
                execute("UPDATE students SET class_id=? WHERE id=?", (to_class_id, sid))
                counts["promoted"] += 1
            elif action == "graduate":
                execute("UPDATE students SET is_active=0, class_id=NULL WHERE id=?", (sid,))
                counts["graduated"] += 1
            else:
                counts["held_back"] += 1

            execute(
                """INSERT INTO student_promotions
                   (student_id, from_class_id, to_class_id, academic_year_id,
                    action, notes, promoted_by)
                   VALUES (?,?,?,?,?,?,?)""",
                (sid, from_class_id,
                 to_class_id if action == "promote" else from_class_id,
                 academic_year_id, action, notes or None, self._session.user_id),
            )

        self._audit(
            "batch_promotion", "student_promotions",
            detail=(f"Year {academic_year_id} Class {from_class_id}→{to_class_id}: "
                    f"{counts['promoted']} promoted, {counts['held_back']} held, "
                    f"{counts['graduated']} graduated, {counts['skipped']} skipped"),
        )
        return counts

    def get_class_students_with_status(
        self, class_id: int, academic_year_id: int
    ) -> list[dict]:
        """Return students in a class with their promotion status and latest avg grade."""
        self._require_permission("student.promote")
        rows = fetch_all(
            """SELECT s.id, s.first_name||' '||s.last_name AS name,
                      s.admission_no, s.gender,
                      p.action AS promotion_action, p.id AS promotion_id,
                      (SELECT ROUND(AVG(g.score * 100.0 / NULLIF(g.max_score,0)), 1)
                       FROM grades g
                       JOIN exams e ON e.id=g.exam_id
                       WHERE g.student_id=s.id AND e.academic_year_id=?
                         AND g.status='approved') AS avg_pct
               FROM students s
               LEFT JOIN student_promotions p
                 ON p.student_id=s.id AND p.academic_year_id=?
               WHERE s.class_id=? AND s.is_active=1
               ORDER BY s.last_name, s.first_name""",
            (academic_year_id, academic_year_id, class_id),
        )
        return [dict(r) for r in rows]

    def get_history(
        self, academic_year_id: int | None = None,
        from_class_id: int | None = None,
    ) -> list[dict]:
        self._require_permission("student.promote")
        where, params = [], []
        if academic_year_id:
            where.append("p.academic_year_id=?"); params.append(academic_year_id)
        if from_class_id:
            where.append("p.from_class_id=?"); params.append(from_class_id)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = fetch_all(
            f"""SELECT p.*,
                       s.first_name||' '||s.last_name AS student_name,
                       s.admission_no,
                       fc.name AS from_class, tc.name AS to_class,
                       ay.label AS year_label,
                       u.full_name AS promoted_by_name
                FROM student_promotions p
                JOIN students s ON s.id=p.student_id
                LEFT JOIN classes fc ON fc.id=p.from_class_id
                LEFT JOIN classes tc ON tc.id=p.to_class_id
                LEFT JOIN academic_years ay ON ay.id=p.academic_year_id
                LEFT JOIN users u ON u.id=p.promoted_by
                {clause} ORDER BY p.id DESC""",
            tuple(params),
        )
        return [dict(r) for r in rows]


promotion_service = PromotionService()
