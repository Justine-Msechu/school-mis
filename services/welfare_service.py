"""
services/welfare_service.py — Welfare domain business logic.
"""

from __future__ import annotations
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute, db_write


class WelfareService(BaseService):

    # ── Register welfare record ───────────────────────────────────────────────

    def register(
        self,
        student_id: int,
        category: str,
        support_type: str,
        sponsor_name: str = "",
        sponsor_org: str = "",
        notes: str = "",
        verified: bool = False,
    ) -> int:
        """
        Create a welfare record for a student.

        Policy: no duplicate records; full_fees only for orphan/half_orphan.
        Side-effect: sets students.student_category = category if orphan.
        """
        self._require_permission("welfare.*")

        student = fetch_one("SELECT * FROM students WHERE id=?", (student_id,))
        if not student:
            raise ServiceError("Student not found.")

        existing = fetch_one(
            "SELECT id FROM welfare_records WHERE student_id=?", (student_id,)
        )

        self._enforce(
            "welfare.register",
            subject=dict(student),
            data={"category": category, "support_type": support_type},
            extra={"existing_record": bool(existing)},
        )

        wr_id = execute(
            """INSERT INTO welfare_records
               (student_id, category, support_type, sponsor_name, sponsor_org, notes)
               VALUES (?,?,?,?,?,?)""",
            (student_id, category, support_type, sponsor_name, sponsor_org, notes),
        )

        # Sync student_category field so billing engine can detect orphans
        if category in ("orphan", "half_orphan"):
            execute(
                "UPDATE students SET student_category=? WHERE id=?",
                (category, student_id),
            )

        if verified:
            import datetime
            today = datetime.date.today().isoformat()
            execute(
                "UPDATE welfare_records SET verified=1, verified_by=?, verified_date=? WHERE id=?",
                (self._session.user_id, today, wr_id),
            )

        self._audit("welfare_registered", "welfare_records", wr_id,
                    detail=f"Student {student_id}: {category} / {support_type}",
                    after={"category": category, "support_type": support_type,
                           "verified": verified})
        return wr_id

    # ── Edit welfare record ───────────────────────────────────────────────────

    def update(
        self,
        wr_id: int,
        category: str,
        support_type: str,
        sponsor_name: str = "",
        sponsor_org: str = "",
        notes: str = "",
        verified: bool | None = None,
    ) -> None:
        self._require_permission("welfare.*")

        wr = fetch_one("SELECT * FROM welfare_records WHERE id=?", (wr_id,))
        if not wr:
            raise ServiceError("Welfare record not found.")

        student = fetch_one("SELECT * FROM students WHERE id=?", (wr["student_id"],))

        self._enforce(
            "welfare.edit",
            subject=dict(student) if student else {},
            data={"category": category, "support_type": support_type},
        )

        execute(
            """UPDATE welfare_records
               SET category=?, support_type=?, sponsor_name=?,
                   sponsor_org=?, notes=?
               WHERE id=?""",
            (category, support_type, sponsor_name, sponsor_org, notes, wr_id),
        )

        if student and category in ("orphan", "half_orphan"):
            execute(
                "UPDATE students SET student_category=? WHERE id=?",
                (category, student["id"]),
            )

        if verified is not None:
            import datetime
            today = datetime.date.today().isoformat()
            execute(
                "UPDATE welfare_records SET verified=?, verified_by=?, verified_date=? WHERE id=?",
                (1 if verified else 0,
                 self._session.user_id if verified else None,
                 today if verified else None,
                 wr_id),
            )

        self._audit("welfare_updated", "welfare_records", wr_id,
                    before=dict(wr),
                    after={"category": category, "support_type": support_type,
                           "verified": verified})

    # ── Verify welfare record ─────────────────────────────────────────────────

    def verify(self, wr_id: int) -> None:
        """Mark a welfare record as verified. Restricted to welfare_officer / head_teacher / admin."""
        self._require_permission("welfare.*")

        wr = fetch_one("SELECT * FROM welfare_records WHERE id=?", (wr_id,))
        if not wr:
            raise ServiceError("Welfare record not found.")
        if wr["verified"]:
            raise ServiceError("This record is already verified.")

        self._enforce(
            "welfare.verify",
            subject=dict(wr),
        )

        import datetime
        today = datetime.date.today().isoformat()
        execute(
            "UPDATE welfare_records SET verified=1, verified_by=?, verified_date=? WHERE id=?",
            (self._session.user_id, today, wr_id),
        )
        self._audit("welfare_verified", "welfare_records", wr_id,
                    detail=f"Verified by {self._session.full_name}")

    # ── Exemption queries ─────────────────────────────────────────────────────

    def get_exempt_students(self) -> list[dict]:
        """Return all students with full fee exemption."""
        rows = fetch_all("""
            SELECT s.id, s.first_name||' '||s.last_name AS student,
                   s.admission_no, c.name AS class_name,
                   wr.category, wr.support_type, wr.verified
            FROM welfare_records wr
            JOIN students s ON s.id=wr.student_id
            LEFT JOIN classes c ON c.id=s.class_id
            WHERE wr.support_type='full_fees'
            ORDER BY s.last_name
        """)
        return [dict(r) for r in rows]


# Singleton
welfare_service = WelfareService()
