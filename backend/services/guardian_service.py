from backend.repositories.guardian_repo import GuardianRepository
from backend.core.exceptions import NotFoundError, ConflictError, BusinessRuleError
from backend.core.db import fetch_one


class GuardianService:

    def __init__(self):
        self._repo = GuardianRepository()

    def create_guardian(self, data: dict) -> dict:
        data.setdefault("relationship", "guardian")
        data.setdefault("is_emergency_contact", 0)
        data.setdefault("is_pickup_authorized", 1)
        data.setdefault("is_billing_contact", 0)
        data.setdefault("communication_pref", "phone")
        data.setdefault("user_id", None)
        data.setdefault("notes", None)
        gid = self._repo.create(data)
        return self._repo.get(gid)

    def update_guardian(self, guardian_id: int, data: dict):
        g = self._repo.get(guardian_id)
        if not g:
            raise NotFoundError("Guardian not found")
        self._repo.update(guardian_id, data)
        return self._repo.get(guardian_id)

    def delete_guardian(self, guardian_id: int):
        g = self._repo.get(guardian_id)
        if not g:
            raise NotFoundError("Guardian not found")
        students = self._repo.students_of(guardian_id)
        if students:
            raise BusinessRuleError(
                f"Cannot delete guardian linked to {len(students)} student(s). Unlink first."
            )
        self._repo.soft_delete(guardian_id)

    def get_guardian(self, guardian_id: int):
        g = self._repo.get(guardian_id)
        if not g:
            raise NotFoundError("Guardian not found")
        g["students"] = self._repo.students_of(guardian_id)
        return g

    def list_guardians(self, search: str = "") -> list:
        return self._repo.list_all(search)

    def link_to_student(self, guardian_id: int, student_id: int, is_primary: bool = False):
        g = self._repo.get(guardian_id)
        if not g:
            raise NotFoundError("Guardian not found")
        s = fetch_one("SELECT id FROM students WHERE id = ? AND (deleted_at IS NULL OR is_active = 1)", (student_id,))
        if not s:
            raise NotFoundError("Student not found")
        self._repo.link_student(guardian_id, student_id, 1 if is_primary else 0)

    def unlink_from_student(self, guardian_id: int, student_id: int):
        if not self._repo.exists_link(guardian_id, student_id):
            raise NotFoundError("Link not found")
        self._repo.unlink_student(guardian_id, student_id)

    def get_student_guardians(self, student_id: int) -> list:
        s = fetch_one("SELECT id FROM students WHERE id = ? AND (deleted_at IS NULL OR is_active = 1)", (student_id,))
        if not s:
            raise NotFoundError("Student not found")
        return self._repo.guardians_of(student_id)

    def get_guardian_students(self, guardian_id: int) -> list:
        g = self._repo.get(guardian_id)
        if not g:
            raise NotFoundError("Guardian not found")
        return self._repo.students_of(guardian_id)
