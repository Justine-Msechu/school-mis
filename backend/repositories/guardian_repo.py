from backend.core.db import fetch_one, fetch_all, execute


class GuardianRepository:

    def create(self, data: dict) -> int:
        return execute(
            """INSERT INTO guardians
               (full_name, relationship, gender, phone, alt_phone, email, id_number,
                occupation, address, is_emergency_contact, is_pickup_authorized,
                is_billing_contact, communication_pref, user_id, notes)
               VALUES (:full_name,:relationship,:gender,:phone,:alt_phone,:email,:id_number,
                       :occupation,:address,:is_emergency_contact,:is_pickup_authorized,
                       :is_billing_contact,:communication_pref,:user_id,:notes)""",
            data,
        )

    def update(self, guardian_id: int, data: dict):
        fields = ", ".join(f"{k}=:{k}" for k in data if k != "id")
        execute(
            f"UPDATE guardians SET {fields}, updated_at=datetime('now') WHERE id = :id",
            {**data, "id": guardian_id},
        )

    def get(self, guardian_id: int):
        return fetch_one(
            "SELECT * FROM guardians WHERE id = ? AND deleted_at IS NULL", (guardian_id,)
        )

    def list_all(self, search: str = "") -> list:
        like = f"%{search}%"
        return fetch_all(
            """SELECT g.*, COUNT(gs.student_id) AS student_count
               FROM guardians g
               LEFT JOIN guardian_students gs ON gs.guardian_id = g.id
               WHERE g.deleted_at IS NULL AND (g.full_name LIKE ? OR g.phone LIKE ? OR g.email LIKE ?)
               GROUP BY g.id ORDER BY g.full_name""",
            (like, like, like),
        )

    def students_of(self, guardian_id: int) -> list:
        return fetch_all(
            """SELECT s.id, (s.first_name || ' ' || s.last_name) AS full_name, s.admission_no, gs.is_primary
               FROM guardian_students gs
               JOIN students s ON s.id = gs.student_id
               WHERE gs.guardian_id = ? AND s.deleted_at IS NULL
               ORDER BY gs.is_primary DESC, s.first_name, s.last_name""",
            (guardian_id,),
        )

    def guardians_of(self, student_id: int) -> list:
        return fetch_all(
            """SELECT g.*, gs.is_primary
               FROM guardian_students gs
               JOIN guardians g ON g.id = gs.guardian_id
               WHERE gs.student_id = ? AND g.deleted_at IS NULL
               ORDER BY gs.is_primary DESC, g.full_name""",
            (student_id,),
        )

    def link_student(self, guardian_id: int, student_id: int, is_primary: int = 0):
        execute(
            """INSERT OR IGNORE INTO guardian_students (guardian_id, student_id, is_primary)
               VALUES (?, ?, ?)""",
            (guardian_id, student_id, is_primary),
        )

    def unlink_student(self, guardian_id: int, student_id: int):
        execute(
            "DELETE FROM guardian_students WHERE guardian_id = ? AND student_id = ?",
            (guardian_id, student_id),
        )

    def soft_delete(self, guardian_id: int):
        execute(
            "UPDATE guardians SET deleted_at=datetime('now') WHERE id = ?", (guardian_id,)
        )

    def exists_link(self, guardian_id: int, student_id: int) -> bool:
        row = fetch_one(
            "SELECT 1 FROM guardian_students WHERE guardian_id = ? AND student_id = ?",
            (guardian_id, student_id),
        )
        return row is not None
