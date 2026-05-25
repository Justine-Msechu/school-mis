from backend.core.db import fetch_one, fetch_all, execute


class EnrollmentRepository:

    def enroll(self, student_id: int, class_id: int, academic_year_id: int, created_by: int) -> int:
        return execute(
            """INSERT INTO enrollments
               (student_id, class_id, academic_year_id, created_by)
               VALUES (?, ?, ?, ?)""",
            (student_id, class_id, academic_year_id, created_by),
        )

    def get_active(self, student_id: int, academic_year_id: int):
        return fetch_one(
            """SELECT e.*, c.name AS class_name, ay.label AS year_name
               FROM enrollments e
               JOIN classes c ON c.id = e.class_id
               JOIN academic_years ay ON ay.id = e.academic_year_id
               WHERE e.student_id = ? AND e.academic_year_id = ? AND e.status = 'active'""",
            (student_id, academic_year_id),
        )

    def get_by_id(self, enrollment_id: int):
        return fetch_one(
            "SELECT * FROM enrollments WHERE id = ?", (enrollment_id,)
        )

    def list_by_class(self, class_id: int, academic_year_id: int, status: str = "active"):
        return fetch_all(
            """SELECT e.*, (s.first_name || ' ' || s.last_name) AS student_name, s.admission_no
               FROM enrollments e
               JOIN students s ON s.id = e.student_id
               WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = ?
               ORDER BY s.first_name, s.last_name""",
            (class_id, academic_year_id, status),
        )

    def list_by_student(self, student_id: int):
        return fetch_all(
            """SELECT e.*, c.name AS class_name, ay.label AS year_name
               FROM enrollments e
               JOIN classes c ON c.id = e.class_id
               JOIN academic_years ay ON ay.id = e.academic_year_id
               WHERE e.student_id = ?
               ORDER BY ay.start_date DESC""",
            (student_id,),
        )

    def transfer(self, enrollment_id: int, new_class_id: int, reason: str, created_by: int) -> int:
        row = self.get_by_id(enrollment_id)
        if not row:
            raise ValueError("Enrollment not found")
        execute(
            """UPDATE enrollments SET status='transferred', exit_date=date('now'), transfer_reason=?
               WHERE id = ?""",
            (reason, enrollment_id),
        )
        return execute(
            """INSERT INTO enrollments
               (student_id, class_id, academic_year_id, transfer_from_class_id, transfer_reason, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (row["student_id"], new_class_id, row["academic_year_id"], row["class_id"], reason, created_by),
        )

    def withdraw(self, enrollment_id: int, reason: str):
        execute(
            """UPDATE enrollments SET status='withdrawn', exit_date=date('now'), transfer_reason=?, updated_at=datetime('now')
               WHERE id = ?""",
            (reason, enrollment_id),
        )

    def graduate(self, class_id: int, academic_year_id: int):
        execute(
            """UPDATE enrollments SET status='graduated', exit_date=date('now'), updated_at=datetime('now')
               WHERE class_id = ? AND academic_year_id = ? AND status = 'active'""",
            (class_id, academic_year_id),
        )

    def class_headcount(self, academic_year_id: int):
        return fetch_all(
            """SELECT c.id AS class_id, c.name AS class_name,
                      COUNT(CASE WHEN e.status='active' THEN 1 END) AS enrolled,
                      COUNT(CASE WHEN e.status='transferred' THEN 1 END) AS transferred,
                      COUNT(CASE WHEN e.status='withdrawn' THEN 1 END) AS withdrawn
               FROM classes c
               LEFT JOIN enrollments e ON e.class_id = c.id AND e.academic_year_id = ?
               WHERE c.deleted_at IS NULL
               GROUP BY c.id, c.name
               ORDER BY c.name""",
            (academic_year_id,),
        )

    def bulk_enroll(self, rows: list[dict]) -> int:
        count = 0
        for r in rows:
            try:
                self.enroll(r["student_id"], r["class_id"], r["academic_year_id"], r["created_by"])
                count += 1
            except Exception:
                pass
        return count
