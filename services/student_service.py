"""
services/student_service.py — Student and attendance domain logic.
"""

from __future__ import annotations
import datetime
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute, execute_many, get_connection
from auth.rbac import get_class_scope


class StudentService(BaseService):

    # ── Student management ────────────────────────────────────────────────────

    def create_student(self, data: dict) -> int:
        self._require_permission("student.create")
        required = ("first_name", "last_name", "admission_no")
        for f in required:
            if not data.get(f, "").strip():
                raise ServiceError(f"Field '{f}' is required.")

        exists = fetch_one(
            "SELECT id FROM students WHERE admission_no=?",
            (data["admission_no"].strip(),)
        )
        if exists:
            raise ServiceError(f"Admission number '{data['admission_no']}' already exists.")

        sid = execute(
            """INSERT INTO students
               (admission_no, first_name, last_name, gender, date_of_birth,
                class_id, parent_name, parent_phone, parent_email,
                address, student_category, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data["admission_no"].strip(),
                data["first_name"].strip(),
                data["last_name"].strip(),
                data.get("gender"),
                data.get("date_of_birth"),
                data.get("class_id"),
                data.get("parent_name", ""),
                data.get("parent_phone", ""),
                data.get("parent_email", ""),
                data.get("address", ""),
                data.get("student_category", "regular"),
                data.get("notes", ""),
            ),
        )
        self._audit("student_created", "students", sid,
                    detail=f"{data['first_name']} {data['last_name']} ({data['admission_no']})")
        return sid

    def get_students_for_class(self, class_id: int | None = None) -> list[dict]:
        """Return students, scoped to the current user's class access."""
        scope = get_class_scope()

        if class_id is not None:
            from auth.rbac import check_class_access
            if not check_class_access(class_id):
                raise ServiceError("You do not have access to this class.")
            rows = fetch_all(
                "SELECT * FROM students WHERE class_id=? AND is_active=1 ORDER BY last_name",
                (class_id,)
            )
        elif scope is None:
            rows = fetch_all("SELECT * FROM students WHERE is_active=1 ORDER BY last_name")
        elif scope:
            placeholders = ",".join("?" * len(scope))
            rows = fetch_all(
                f"SELECT * FROM students WHERE class_id IN ({placeholders}) AND is_active=1"
                f" ORDER BY last_name",
                tuple(scope)
            )
        else:
            rows = []
        return [dict(r) for r in rows]

    # ── Attendance ────────────────────────────────────────────────────────────

    def mark_attendance(
        self,
        class_id: int,
        date_str: str,
        records: list[dict],   # [{student_id, status, notes}, ...]
    ) -> int:
        """
        Bulk-mark attendance for a class on a date.

        Policy: no future dates; class teachers can only mark their own class.
        """
        self._require_permission("attendance.mark")

        from auth.rbac import check_class_access
        if not check_class_access(class_id):
            raise ServiceError("You do not have access to mark attendance for this class.")

        # Determine actor's class for scoping
        actor_class_id = None
        if self._session.user and self._session.user.get("teacher_id"):
            cls_row = fetch_one(
                "SELECT id FROM classes WHERE teacher_id=?",
                (self._session.user["teacher_id"],)
            )
            if cls_row:
                actor_class_id = cls_row["id"]

        self._enforce(
            "attendance.mark",
            subject={"class_id": class_id},
            data={"date": date_str, "class_id": class_id},
            extra={"actor_class_id": actor_class_id},
        )

        conn = get_connection()
        cur  = conn.cursor()
        saved = 0
        for rec in records:
            cur.execute(
                """INSERT INTO attendance (student_id, class_id, date, status, notes, recorded_by)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(student_id, date) DO UPDATE
                   SET status=excluded.status, notes=excluded.notes,
                       recorded_by=excluded.recorded_by""",
                (rec["student_id"], class_id, date_str,
                 rec["status"], rec.get("notes", ""),
                 self._session.user_id),
            )
            saved += 1
        conn.commit()
        conn.close()

        self._audit("attendance_saved", "attendance",
                    detail=f"Class {class_id} date {date_str}: {saved} records")
        return saved

    def get_attendance_summary(self, class_id: int, date_str: str) -> dict:
        """Return present/absent/late/excused counts for a class on a date."""
        rows = fetch_all(
            "SELECT status, COUNT(*) AS n FROM attendance "
            "WHERE class_id=? AND date=? GROUP BY status",
            (class_id, date_str)
        )
        result = {"Present": 0, "Absent": 0, "Late": 0, "Excused": 0}
        for r in rows:
            result[r["status"]] = r["n"]
        return result


# Singleton
student_service = StudentService()
