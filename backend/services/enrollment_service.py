from backend.repositories.enrollment_repo import EnrollmentRepository
from backend.core.exceptions import ConflictError, NotFoundError, BusinessRuleError
from backend.core.db import fetch_one


class EnrollmentService:

    def __init__(self):
        self._repo = EnrollmentRepository()

    def _current_year(self):
        row = fetch_one("SELECT id, label AS name FROM academic_years WHERE is_current = 1")
        if not row:
            raise BusinessRuleError("No active academic year is set. Configure one in Settings.")
        return row

    def enroll_student(self, student_id: int, class_id: int, academic_year_id: int, created_by: int) -> dict:
        existing = self._repo.get_active(student_id, academic_year_id)
        if existing:
            raise ConflictError(
                f"Student is already enrolled in {existing['class_name']} for this year."
            )
        student = fetch_one("SELECT id, (first_name || ' ' || last_name) AS full_name FROM students WHERE id = ? AND deleted_at IS NULL", (student_id,))
        if not student:
            raise NotFoundError("Student not found")
        cls = fetch_one("SELECT id, name FROM classes WHERE id = ? AND deleted_at IS NULL", (class_id,))
        if not cls:
            raise NotFoundError("Class not found")
        eid = self._repo.enroll(student_id, class_id, academic_year_id, created_by)
        return {"id": eid, "student_name": student["full_name"], "class_name": cls["name"]}

    def transfer_student(self, enrollment_id: int, new_class_id: int, reason: str, created_by: int) -> int:
        enrollment = self._repo.get_by_id(enrollment_id)
        if not enrollment:
            raise NotFoundError("Enrollment not found")
        if enrollment["status"] != "active":
            raise BusinessRuleError("Only active enrollments can be transferred.")
        cls = fetch_one("SELECT id FROM classes WHERE id = ? AND deleted_at IS NULL", (new_class_id,))
        if not cls:
            raise NotFoundError("Target class not found")
        return self._repo.transfer(enrollment_id, new_class_id, reason, created_by)

    def withdraw_student(self, enrollment_id: int, reason: str):
        enrollment = self._repo.get_by_id(enrollment_id)
        if not enrollment:
            raise NotFoundError("Enrollment not found")
        if enrollment["status"] != "active":
            raise BusinessRuleError("Only active enrollments can be withdrawn.")
        self._repo.withdraw(enrollment_id, reason)

    def get_class_roll(self, class_id: int, academic_year_id: int, status: str = "active") -> list:
        return self._repo.list_by_class(class_id, academic_year_id, status)

    def get_student_history(self, student_id: int) -> list:
        return self._repo.list_by_student(student_id)

    def get_headcount_summary(self, academic_year_id: int = None) -> list:
        if not academic_year_id:
            year = self._current_year()
            academic_year_id = year["id"]
        return self._repo.class_headcount(academic_year_id)

    def get_current_enrollment(self, student_id: int):
        year = self._current_year()
        return self._repo.get_active(student_id, year["id"])

    def bulk_enroll(self, rows: list[dict]) -> dict:
        count = self._repo.bulk_enroll(rows)
        return {"enrolled": count, "total": len(rows)}
