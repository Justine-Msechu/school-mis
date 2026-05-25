from backend.repositories.report_card_repo import ReportCardRepository
from backend.domain.grades.engine import GradingEngine
from backend.core.db import fetch_one, fetch_all
from backend.core.exceptions import NotFoundError, BusinessRuleError, StateError
from backend.core.events import event_bus


class ReportCardService:

    def __init__(self):
        self._rc = ReportCardRepository()

    def _get_exam(self, exam_id: int):
        row = fetch_one("SELECT * FROM exams WHERE id = ?", (exam_id,))
        if not row:
            raise NotFoundError("Exam not found")
        return row

    def _get_class(self, class_id: int):
        row = fetch_one("SELECT * FROM classes WHERE id = ?", (class_id,))
        if not row:
            raise NotFoundError("Class not found")
        return row

    def _get_scale(self, academic_year_id: int):
        return fetch_all(
            "SELECT * FROM grade_scales WHERE academic_year_id = ? ORDER BY min_pct DESC",
            (academic_year_id,),
        )

    def _get_grades(self, exam_id: int, class_id: int):
        return fetch_all(
            """SELECT g.student_id, g.subject_id, g.score AS marks_obtained, g.max_score AS total_marks,
                      sub.name AS subject_name
               FROM grades g
               JOIN students s ON s.id = g.student_id
               JOIN subjects sub ON sub.id = g.subject_id
               WHERE g.exam_id = ? AND s.class_id = ?
               ORDER BY g.student_id, sub.name""",
            (exam_id, class_id),
        )

    def generate_for_class(self, exam_id: int, class_id: int, generated_by: int) -> dict:
        exam = self._get_exam(exam_id)
        cls = self._get_class(class_id)
        grade_rows = self._get_grades(exam_id, class_id)

        if not grade_rows:
            raise BusinessRuleError("No grade data found for this exam/class combination.")

        scale = self._get_scale(exam["academic_year_id"])
        engine = GradingEngine(scale)

        student_ids = list({row["student_id"] for row in grade_rows})
        students_map = {
            r["id"]: r for r in
            fetch_all(
                f"SELECT id, (first_name || ' ' || last_name) AS full_name, admission_no "
                f"FROM students WHERE id IN ({','.join('?' * len(student_ids))})",
                student_ids,
            )
        }

        subject_map: dict[int, list] = {}
        for row in grade_rows:
            subject_map.setdefault(row["student_id"], []).append(row)

        student_scores = []
        for sid, rows in subject_map.items():
            scored = [
                engine.grade(
                    float(row["marks_obtained"] or 0),
                    float(row["total_marks"] or 100),
                )
                for row in rows
            ]
            total_pct = sum(g.percentage for g in scored) / max(len(scored), 1)
            overall = engine.grade(total_pct, 100)
            student_scores.append((sid, rows, scored, overall))

        ranked = sorted(student_scores, key=lambda x: -x[3].percentage)
        created = failed = 0

        for rank, (sid, rows, scored, overall) in enumerate(ranked, 1):
            card_id = self._rc.create_card({
                "student_id": sid,
                "exam_id": exam_id,
                "academic_year_id": exam["academic_year_id"],
                "class_id": class_id,
                "class_name_snapshot": cls["name"],
                "total_marks": sum(r["marks_obtained"] or 0 for r in rows),
                "total_possible": sum(r["total_marks"] or 100 for r in rows),
                "overall_pct": round(overall.percentage, 2),
                "overall_grade": overall.grade_label,
                "class_rank": rank,
                "stream_rank": None,
                "days_present": None,
                "days_absent": None,
                "days_total": None,
                "generated_by": generated_by,
            })

            if card_id:
                for i, row in enumerate(rows):
                    g = scored[i]
                    self._rc.upsert_subject({
                        "report_card_id": card_id,
                        "subject_id": row["subject_id"],
                        "subject_name": row["subject_name"] or "",
                        "marks_obtained": row["marks_obtained"],
                        "total_marks": row["total_marks"],
                        "percentage": round(g.percentage, 2),
                        "grade_label": g.grade_label,
                        "gpa_points": g.gpa_points,
                        "position": None,
                        "teacher_name": None,
                        "remarks": None,
                    })
                created += 1
            else:
                failed += 1

        return {"created": created, "failed": failed, "class": cls["name"], "exam": exam["name"]}

    def publish_card(self, card_id: int, published_by: int):
        card = self._rc.get_card_by_id(card_id)
        if not card:
            raise NotFoundError("Report card not found")
        if card["is_locked"]:
            raise StateError("Report card is locked and cannot be modified.")
        self._rc.publish_card(card_id, published_by)
        event_bus.emit("report_card.published", {"card_id": card_id, "student_id": card["student_id"]})

    def lock_card(self, card_id: int):
        card = self._rc.get_card_by_id(card_id)
        if not card:
            raise NotFoundError("Report card not found")
        if not card["is_published"]:
            raise BusinessRuleError("Only published cards can be locked.")
        self._rc.lock_card(card_id)

    def add_comment(self, card_id: int, author_id: int, author_role: str,
                    comment_type: str, text: str) -> int:
        card = self._rc.get_card_by_id(card_id)
        if not card:
            raise NotFoundError("Report card not found")
        if card["is_locked"]:
            raise StateError("Report card is locked.")
        return self._rc.add_comment({
            "report_card_id": card_id,
            "author_id": author_id,
            "author_role": author_role,
            "comment_type": comment_type,
            "comment_text": text,
        })

    def get_full_card(self, student_id: int, exam_id: int) -> dict:
        card = self._rc.get_card(student_id, exam_id)
        if not card:
            raise NotFoundError("Report card not found")
        card["subjects"] = self._rc.list_subjects(card["id"])
        card["comments"] = self._rc.list_comments(card["id"])
        return card

    def list_cards_for_exam(self, exam_id: int, class_id: int = None) -> list:
        return self._rc.list_cards_for_exam(exam_id, class_id)

    def create_job(self, exam_id: int, class_id: int, academic_year_id: int,
                   initiated_by: int, total_students: int) -> int:
        return self._rc.create_job(exam_id, class_id, academic_year_id, initiated_by, total_students)

    def update_job(self, job_id: int, data: dict):
        self._rc.update_job(job_id, data)

    def get_job(self, job_id: int):
        job = self._rc.get_job(job_id)
        if not job:
            raise NotFoundError("Job not found")
        return job

    def list_jobs(self, exam_id: int) -> list:
        return self._rc.list_jobs(exam_id)
