from backend.core.db import fetch_one, fetch_all, execute


class TimetableRepository:

    # ── Versions ────────────────────────────────────────────────────────────────

    def create_version(self, data: dict) -> int:
        return execute(
            """INSERT INTO timetable_versions
               (academic_year_id, term_id, name, status, effective_from, effective_to, created_by)
               VALUES (:academic_year_id,:term_id,:name,:status,:effective_from,:effective_to,:created_by)""",
            data,
        )

    def get_version(self, version_id: int):
        return fetch_one("SELECT * FROM timetable_versions WHERE id = ?", (version_id,))

    def list_versions(self, academic_year_id: int):
        return fetch_all(
            "SELECT * FROM timetable_versions WHERE academic_year_id = ? ORDER BY created_at DESC",
            (academic_year_id,),
        )

    def activate_version(self, version_id: int, academic_year_id: int):
        execute(
            "UPDATE timetable_versions SET status='archived' WHERE academic_year_id = ? AND status='active'",
            (academic_year_id,),
        )
        execute(
            "UPDATE timetable_versions SET status='active' WHERE id = ?", (version_id,)
        )

    def update_version_status(self, version_id: int, status: str):
        execute(
            "UPDATE timetable_versions SET status=? WHERE id=?", (status, version_id)
        )

    # ── Periods ─────────────────────────────────────────────────────────────────

    def list_periods(self):
        return fetch_all("SELECT * FROM timetable_periods ORDER BY sort_order")

    def get_period(self, period_id: int):
        return fetch_one("SELECT * FROM timetable_periods WHERE id = ?", (period_id,))

    # ── Slots ────────────────────────────────────────────────────────────────────

    def upsert_slot(self, data: dict) -> int:
        existing = fetch_one(
            """SELECT id FROM timetable_slots
               WHERE version_id=? AND class_id=? AND period_id=? AND day_of_week=?""",
            (data["version_id"], data["class_id"], data["period_id"], data["day_of_week"]),
        )
        if existing:
            execute(
                """UPDATE timetable_slots SET subject_id=?, teacher_id=?, room=?, notes=?
                   WHERE id=?""",
                (data["subject_id"], data.get("teacher_id"), data.get("room"), data.get("notes"), existing["id"]),
            )
            return existing["id"]
        return execute(
            """INSERT INTO timetable_slots
               (version_id, class_id, subject_id, teacher_id, period_id, day_of_week, room, notes)
               VALUES (:version_id,:class_id,:subject_id,:teacher_id,:period_id,:day_of_week,:room,:notes)""",
            data,
        )

    def delete_slot(self, slot_id: int):
        execute("DELETE FROM timetable_slots WHERE id = ?", (slot_id,))

    def list_slots_for_class(self, version_id: int, class_id: int):
        return fetch_all(
            """SELECT ts.*, tp.name AS period_name, tp.start_time, tp.end_time, tp.is_break,
                      s.name AS subject_name, (t.first_name || ' ' || t.last_name) AS teacher_name, tp.sort_order
               FROM timetable_slots ts
               JOIN timetable_periods tp ON tp.id = ts.period_id
               JOIN subjects s ON s.id = ts.subject_id
               LEFT JOIN teachers t ON t.id = ts.teacher_id
               WHERE ts.version_id = ? AND ts.class_id = ?
               ORDER BY ts.day_of_week, tp.sort_order""",
            (version_id, class_id),
        )

    def list_slots_for_teacher(self, version_id: int, teacher_id: int):
        return fetch_all(
            """SELECT ts.*, tp.name AS period_name, tp.start_time, tp.end_time,
                      s.name AS subject_name, c.name AS class_name, tp.sort_order
               FROM timetable_slots ts
               JOIN timetable_periods tp ON tp.id = ts.period_id
               JOIN subjects s ON s.id = ts.subject_id
               JOIN classes c ON c.id = ts.class_id
               WHERE ts.version_id = ? AND ts.teacher_id = ?
               ORDER BY ts.day_of_week, tp.sort_order""",
            (version_id, teacher_id),
        )

    def teacher_conflicts(self, version_id: int, teacher_id: int, period_id: int, day_of_week: int, exclude_slot_id: int = 0):
        return fetch_all(
            """SELECT ts.*, c.name AS class_name, s.name AS subject_name
               FROM timetable_slots ts
               JOIN classes c ON c.id = ts.class_id
               JOIN subjects s ON s.id = ts.subject_id
               WHERE ts.version_id = ? AND ts.teacher_id = ?
                 AND ts.period_id = ? AND ts.day_of_week = ?
                 AND ts.id != ?""",
            (version_id, teacher_id, period_id, day_of_week, exclude_slot_id),
        )

    def get_active_version(self, academic_year_id: int):
        return fetch_one(
            "SELECT * FROM timetable_versions WHERE academic_year_id = ? AND status = 'active'",
            (academic_year_id,),
        )
