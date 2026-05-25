from backend.repositories.timetable_repo import TimetableRepository
from backend.core.exceptions import NotFoundError, ConflictError, BusinessRuleError, StateError


class TimetableService:

    def __init__(self):
        self._repo = TimetableRepository()

    def create_version(self, academic_year_id: int, name: str, term_id: int = None,
                       effective_from: str = None, effective_to: str = None,
                       created_by: int = None) -> dict:
        vid = self._repo.create_version({
            "academic_year_id": academic_year_id,
            "term_id": term_id,
            "name": name,
            "status": "draft",
            "effective_from": effective_from,
            "effective_to": effective_to,
            "created_by": created_by,
        })
        return self._repo.get_version(vid)

    def activate_version(self, version_id: int):
        v = self._repo.get_version(version_id)
        if not v:
            raise NotFoundError("Timetable version not found")
        if v["status"] == "archived":
            raise StateError("Cannot activate an archived version.")
        self._repo.activate_version(version_id, v["academic_year_id"])
        return self._repo.get_version(version_id)

    def archive_version(self, version_id: int):
        v = self._repo.get_version(version_id)
        if not v:
            raise NotFoundError("Timetable version not found")
        self._repo.update_version_status(version_id, "archived")

    def list_versions(self, academic_year_id: int) -> list:
        return self._repo.list_versions(academic_year_id)

    def list_periods(self) -> list:
        return self._repo.list_periods()

    def set_slot(self, version_id: int, class_id: int, subject_id: int,
                 period_id: int, day_of_week: int, teacher_id: int = None,
                 room: str = None, notes: str = None) -> dict:
        v = self._repo.get_version(version_id)
        if not v:
            raise NotFoundError("Timetable version not found")
        if v["status"] == "archived":
            raise StateError("Cannot edit an archived timetable.")

        if teacher_id:
            conflicts = self._repo.teacher_conflicts(version_id, teacher_id, period_id, day_of_week)
            if conflicts:
                c = conflicts[0]
                raise ConflictError(
                    f"Teacher already assigned to {c['class_name']} / {c['subject_name']} at this period."
                )

        period = self._repo.get_period(period_id)
        if not period:
            raise NotFoundError("Period not found")
        if period["is_break"]:
            raise BusinessRuleError("Cannot assign subjects to break periods.")

        slot_id = self._repo.upsert_slot({
            "version_id": version_id,
            "class_id": class_id,
            "subject_id": subject_id,
            "teacher_id": teacher_id,
            "period_id": period_id,
            "day_of_week": day_of_week,
            "room": room,
            "notes": notes,
        })
        return {"slot_id": slot_id}

    def delete_slot(self, slot_id: int):
        self._repo.delete_slot(slot_id)

    def get_class_timetable(self, version_id: int, class_id: int) -> dict:
        slots = self._repo.list_slots_for_class(version_id, class_id)
        periods = self._repo.list_periods()
        grid: dict[int, dict[int, dict]] = {}
        for s in slots:
            day = s["day_of_week"]
            pid = s["period_id"]
            grid.setdefault(day, {})[pid] = s
        return {"periods": periods, "grid": grid, "slots": slots}

    def get_teacher_timetable(self, version_id: int, teacher_id: int) -> list:
        return self._repo.list_slots_for_teacher(version_id, teacher_id)

    def get_active_version(self, academic_year_id: int):
        return self._repo.get_active_version(academic_year_id)
