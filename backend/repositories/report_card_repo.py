from backend.core.db import fetch_one, fetch_all, execute


class ReportCardRepository:

    # ── Cards ────────────────────────────────────────────────────────────────────

    def create_card(self, data: dict) -> int:
        return execute(
            """INSERT OR IGNORE INTO report_cards
               (student_id, exam_id, academic_year_id, class_id, class_name_snapshot,
                total_marks, total_possible, overall_pct, overall_grade,
                class_rank, stream_rank, days_present, days_absent, days_total,
                generated_by)
               VALUES (:student_id,:exam_id,:academic_year_id,:class_id,:class_name_snapshot,
                       :total_marks,:total_possible,:overall_pct,:overall_grade,
                       :class_rank,:stream_rank,:days_present,:days_absent,:days_total,
                       :generated_by)""",
            data,
        )

    def update_card(self, card_id: int, data: dict):
        fields = ", ".join(f"{k}=:{k}" for k in data if k != "id")
        execute(f"UPDATE report_cards SET {fields} WHERE id=:id", {**data, "id": card_id})

    def get_card(self, student_id: int, exam_id: int):
        return fetch_one(
            """SELECT rc.*, (s.first_name || ' ' || s.last_name) AS student_name, s.admission_no
               FROM report_cards rc
               JOIN students s ON s.id = rc.student_id
               WHERE rc.student_id = ? AND rc.exam_id = ?""",
            (student_id, exam_id),
        )

    def get_card_by_id(self, card_id: int):
        return fetch_one("SELECT * FROM report_cards WHERE id = ?", (card_id,))

    def list_cards_for_exam(self, exam_id: int, class_id: int = None):
        args = [exam_id]
        clause = "WHERE rc.exam_id = ?"
        if class_id:
            clause += " AND rc.class_id = ?"
            args.append(class_id)
        return fetch_all(
            f"""SELECT rc.*, (s.first_name || ' ' || s.last_name) AS student_name, s.admission_no
                FROM report_cards rc
                JOIN students s ON s.id = rc.student_id
                {clause}
                ORDER BY rc.class_rank""",
            args,
        )

    def publish_card(self, card_id: int, published_by: int):
        execute(
            """UPDATE report_cards
               SET is_published=1, published_at=datetime('now'), published_by=?
               WHERE id=?""",
            (published_by, card_id),
        )

    def lock_card(self, card_id: int):
        execute(
            "UPDATE report_cards SET is_locked=1, locked_at=datetime('now') WHERE id=?",
            (card_id,),
        )

    def set_pdf_path(self, card_id: int, path: str):
        execute("UPDATE report_cards SET pdf_path=? WHERE id=?", (path, card_id))

    def set_principal_comment(self, card_id: int, comment: str):
        execute(
            "UPDATE report_cards SET principal_comment=? WHERE id=?", (comment, card_id)
        )

    def set_teacher_comment(self, card_id: int, comment: str):
        execute(
            "UPDATE report_cards SET class_teacher_comment=? WHERE id=?", (comment, card_id)
        )

    # ── Subjects ─────────────────────────────────────────────────────────────────

    def upsert_subject(self, data: dict):
        execute(
            """INSERT OR REPLACE INTO report_card_subjects
               (report_card_id, subject_id, subject_name, marks_obtained, total_marks,
                percentage, grade_label, gpa_points, position, teacher_name, remarks)
               VALUES (:report_card_id,:subject_id,:subject_name,:marks_obtained,:total_marks,
                       :percentage,:grade_label,:gpa_points,:position,:teacher_name,:remarks)""",
            data,
        )

    def list_subjects(self, report_card_id: int):
        return fetch_all(
            "SELECT * FROM report_card_subjects WHERE report_card_id = ? ORDER BY subject_name",
            (report_card_id,),
        )

    # ── Comments ─────────────────────────────────────────────────────────────────

    def add_comment(self, data: dict) -> int:
        return execute(
            """INSERT INTO report_card_comments
               (report_card_id, author_id, author_role, comment_type, comment_text)
               VALUES (:report_card_id,:author_id,:author_role,:comment_type,:comment_text)""",
            data,
        )

    def list_comments(self, report_card_id: int):
        return fetch_all(
            "SELECT * FROM report_card_comments WHERE report_card_id = ? ORDER BY created_at",
            (report_card_id,),
        )

    # ── Jobs ─────────────────────────────────────────────────────────────────────

    def create_job(self, exam_id: int, class_id: int, academic_year_id: int, initiated_by: int, total_students: int) -> int:
        return execute(
            """INSERT INTO report_card_jobs
               (exam_id, class_id, academic_year_id, total_students, initiated_by, status)
               VALUES (?, ?, ?, ?, ?, 'pending')""",
            (exam_id, class_id, academic_year_id, total_students, initiated_by),
        )

    def update_job(self, job_id: int, data: dict):
        fields = ", ".join(f"{k}=:{k}" for k in data)
        execute(f"UPDATE report_card_jobs SET {fields} WHERE id=:id", {**data, "id": job_id})

    def get_job(self, job_id: int):
        return fetch_one("SELECT * FROM report_card_jobs WHERE id = ?", (job_id,))

    def list_jobs(self, exam_id: int):
        return fetch_all(
            "SELECT * FROM report_card_jobs WHERE exam_id = ? ORDER BY created_at DESC",
            (exam_id,),
        )
