"""Health / Infirmary service — visit records, symptoms, treatment, referrals."""
from __future__ import annotations
import datetime
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute


ACTIONS = ("treated", "referred", "sent_home", "rest", "other")
ACTION_LABELS = {
    "treated": "Treated on site",
    "referred": "Referred to hospital",
    "sent_home": "Sent home",
    "rest": "Rest room",
    "other": "Other",
}


class HealthService(BaseService):

    def record_visit(self, data: dict) -> int:
        self._require_permission("health.record")
        student_id = data.get("student_id")
        if not student_id:
            raise ServiceError("Student is required.")
        student = fetch_one("SELECT id FROM students WHERE id=? AND is_active=1", (student_id,))
        if not student:
            raise ServiceError("Student not found.")

        action = data.get("action_taken") or "other"
        if action not in ACTIONS:
            raise ServiceError(f"Invalid action. Choose: {', '.join(ACTIONS)}")

        now = datetime.datetime.now()
        vid = execute(
            """INSERT INTO health_visits
               (student_id, visit_date, visit_time, symptoms, diagnosis, treatment,
                action_taken, referred_to, parent_notified, parent_notification_note,
                nurse_name, created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (student_id,
             data.get("visit_date") or now.date().isoformat(),
             data.get("visit_time") or now.strftime("%H:%M"),
             (data.get("symptoms") or "").strip() or None,
             (data.get("diagnosis") or "").strip() or None,
             (data.get("treatment") or "").strip() or None,
             action,
             (data.get("referred_to") or "").strip() or None,
             1 if data.get("parent_notified") else 0,
             (data.get("parent_notification_note") or "").strip() or None,
             (data.get("nurse_name") or "").strip() or None,
             self._session.user_id),
        )
        self._audit("health_visit_recorded", "health_visits", vid,
                    detail=f"Student {student_id} — {action}")
        return vid

    def update_visit(self, visit_id: int, data: dict) -> None:
        self._require_permission("health.record")
        visit = fetch_one("SELECT * FROM health_visits WHERE id=?", (visit_id,))
        if not visit:
            raise ServiceError("Visit record not found.")
        action = data.get("action_taken") or visit["action_taken"]
        if action not in ACTIONS:
            raise ServiceError(f"Invalid action.")
        execute(
            """UPDATE health_visits SET
               symptoms=?, diagnosis=?, treatment=?, action_taken=?,
               referred_to=?, parent_notified=?, parent_notification_note=?,
               nurse_name=?
               WHERE id=?""",
            ((data.get("symptoms") or "").strip() or None,
             (data.get("diagnosis") or "").strip() or None,
             (data.get("treatment") or "").strip() or None,
             action,
             (data.get("referred_to") or "").strip() or None,
             1 if data.get("parent_notified") else 0,
             (data.get("parent_notification_note") or "").strip() or None,
             (data.get("nurse_name") or "").strip() or None,
             visit_id),
        )
        self._audit("health_visit_updated", "health_visits", visit_id)

    def get_visits(
        self,
        student_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        action: str | None = None,
    ) -> list[dict]:
        self._require_permission("health.view")
        where, params = [], []
        if student_id:
            where.append("v.student_id=?"); params.append(student_id)
        if date_from:
            where.append("v.visit_date>=?"); params.append(date_from)
        if date_to:
            where.append("v.visit_date<=?"); params.append(date_to)
        if action:
            where.append("v.action_taken=?"); params.append(action)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = fetch_all(
            f"""SELECT v.*,
                       s.first_name||' '||s.last_name AS student_name,
                       s.admission_no,
                       c.name AS class_name
                FROM health_visits v
                JOIN students s ON s.id=v.student_id
                LEFT JOIN classes c ON c.id=s.class_id
                {clause} ORDER BY v.visit_date DESC, v.id DESC""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def get_visit(self, visit_id: int) -> dict:
        self._require_permission("health.view")
        row = fetch_one(
            """SELECT v.*, s.first_name||' '||s.last_name AS student_name,
                      s.admission_no, c.name AS class_name
               FROM health_visits v
               JOIN students s ON s.id=v.student_id
               LEFT JOIN classes c ON c.id=s.class_id
               WHERE v.id=?""",
            (visit_id,)
        )
        if not row:
            raise ServiceError("Visit record not found.")
        return dict(row)

    def get_student_history(self, student_id: int) -> list[dict]:
        return self.get_visits(student_id=student_id)

    def get_stats(self, year: str | None = None) -> dict:
        self._require_permission("health.view")
        where = f"WHERE SUBSTR(v.visit_date,1,4)='{year}'" if year else ""
        total   = fetch_one(f"SELECT COUNT(*) AS n FROM health_visits v {where}")
        referred = fetch_one(
            f"SELECT COUNT(*) AS n FROM health_visits v {where} "
            + ("AND " if where else "WHERE ") + "v.action_taken='referred'"
        )
        today = datetime.date.today().isoformat()
        today_n = fetch_one(
            "SELECT COUNT(*) AS n FROM health_visits WHERE visit_date=?", (today,)
        )
        return {
            "total":    total["n"] if total else 0,
            "referred": referred["n"] if referred else 0,
            "today":    today_n["n"] if today_n else 0,
        }


health_service = HealthService()
