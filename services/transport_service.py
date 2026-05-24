"""Transport management service — routes and student subscriptions."""
from __future__ import annotations
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute


class TransportService(BaseService):

    # ── Routes ────────────────────────────────────────────────────────────────

    def add_route(self, data: dict) -> int:
        self._require_permission("transport.manage")
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceError("Route name is required.")
        rid = execute(
            """INSERT INTO transport_routes
               (name, description, vehicle_no, driver_name, driver_phone,
                fare_term1, fare_term2, fare_term3)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name,
             (data.get("description") or "").strip() or None,
             (data.get("vehicle_no") or "").strip() or None,
             (data.get("driver_name") or "").strip() or None,
             (data.get("driver_phone") or "").strip() or None,
             float(data.get("fare_term1") or 0),
             float(data.get("fare_term2") or 0),
             float(data.get("fare_term3") or 0)),
        )
        self._audit("route_added", "transport_routes", rid, detail=name)
        return rid

    def update_route(self, route_id: int, data: dict) -> None:
        self._require_permission("transport.manage")
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceError("Route name is required.")
        execute(
            """UPDATE transport_routes SET
               name=?, description=?, vehicle_no=?, driver_name=?, driver_phone=?,
               fare_term1=?, fare_term2=?, fare_term3=?
               WHERE id=?""",
            (name,
             (data.get("description") or "").strip() or None,
             (data.get("vehicle_no") or "").strip() or None,
             (data.get("driver_name") or "").strip() or None,
             (data.get("driver_phone") or "").strip() or None,
             float(data.get("fare_term1") or 0),
             float(data.get("fare_term2") or 0),
             float(data.get("fare_term3") or 0),
             route_id),
        )
        self._audit("route_updated", "transport_routes", route_id, detail=name)

    def deactivate_route(self, route_id: int) -> None:
        self._require_permission("transport.manage")
        execute("UPDATE transport_routes SET is_active=0 WHERE id=?", (route_id,))
        self._audit("route_deactivated", "transport_routes", route_id)

    def get_routes(self, active_only: bool = True) -> list[dict]:
        self._require_permission("transport.view")
        where = "WHERE r.is_active=1" if active_only else ""
        rows = fetch_all(
            f"""SELECT r.*,
                       (SELECT COUNT(*) FROM transport_subscriptions s
                        WHERE s.route_id=r.id AND s.status='active') AS student_count
                FROM transport_routes r {where} ORDER BY r.name""",
        )
        return [dict(r) for r in rows]

    def get_route(self, route_id: int) -> dict:
        self._require_permission("transport.view")
        row = fetch_one("SELECT * FROM transport_routes WHERE id=?", (route_id,))
        if not row:
            raise ServiceError("Route not found.")
        return dict(row)

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def assign_student(self, student_id: int, route_id: int,
                       academic_year_id: int, term: int,
                       notes: str = "") -> int:
        self._require_permission("transport.assign")
        existing = fetch_one(
            """SELECT id FROM transport_subscriptions
               WHERE student_id=? AND route_id=? AND academic_year_id=? AND term=?
                 AND status='active'""",
            (student_id, route_id, academic_year_id, term)
        )
        if existing:
            raise ServiceError("Student is already assigned to this route for the selected term.")
        sub_id = execute(
            """INSERT INTO transport_subscriptions
               (student_id, route_id, academic_year_id, term, status, notes, assigned_by)
               VALUES (?,?,?,?,'active',?,?)""",
            (student_id, route_id, academic_year_id, term,
             notes or None, self._session.user_id),
        )
        self._audit("transport_assigned", "transport_subscriptions", sub_id,
                    detail=f"Student {student_id} → Route {route_id} T{term}")
        return sub_id

    def cancel_subscription(self, sub_id: int) -> None:
        self._require_permission("transport.assign")
        execute(
            "UPDATE transport_subscriptions SET status='cancelled' WHERE id=?",
            (sub_id,)
        )
        self._audit("transport_cancelled", "transport_subscriptions", sub_id)

    def get_route_students(self, route_id: int,
                           academic_year_id: int | None = None,
                           term: int | None = None) -> list[dict]:
        self._require_permission("transport.view")
        where = ["s.route_id=?", "s.status='active'"]
        params: list = [route_id]
        if academic_year_id:
            where.append("s.academic_year_id=?"); params.append(academic_year_id)
        if term:
            where.append("s.term=?"); params.append(term)
        rows = fetch_all(
            f"""SELECT s.*, st.first_name||' '||st.last_name AS student_name,
                       st.admission_no, c.name AS class_name,
                       r.name AS route_name,
                       ay.label AS year_label
                FROM transport_subscriptions s
                JOIN students st ON st.id=s.student_id
                LEFT JOIN classes c ON c.id=st.class_id
                JOIN transport_routes r ON r.id=s.route_id
                LEFT JOIN academic_years ay ON ay.id=s.academic_year_id
                WHERE {' AND '.join(where)}
                ORDER BY st.last_name, st.first_name""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def get_student_subscription(self, student_id: int,
                                  academic_year_id: int | None = None) -> list[dict]:
        self._require_permission("transport.view")
        where = ["s.student_id=?", "s.status='active'"]
        params: list = [student_id]
        if academic_year_id:
            where.append("s.academic_year_id=?"); params.append(academic_year_id)
        rows = fetch_all(
            f"""SELECT s.*, r.name AS route_name, r.fare_term1, r.fare_term2, r.fare_term3
                FROM transport_subscriptions s
                JOIN transport_routes r ON r.id=s.route_id
                WHERE {' AND '.join(where)}
                ORDER BY s.term""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def get_all_subscriptions(self, academic_year_id: int | None = None,
                               term: int | None = None,
                               status: str = "active") -> list[dict]:
        self._require_permission("transport.view")
        where = ["s.status=?"]
        params: list = [status]
        if academic_year_id:
            where.append("s.academic_year_id=?"); params.append(academic_year_id)
        if term:
            where.append("s.term=?"); params.append(term)
        rows = fetch_all(
            f"""SELECT s.*, st.first_name||' '||st.last_name AS student_name,
                       st.admission_no, c.name AS class_name,
                       r.name AS route_name,
                       ay.label AS year_label,
                       CASE s.term
                         WHEN 1 THEN r.fare_term1
                         WHEN 2 THEN r.fare_term2
                         WHEN 3 THEN r.fare_term3
                         ELSE 0 END AS fare
                FROM transport_subscriptions s
                JOIN students st ON st.id=s.student_id
                LEFT JOIN classes c ON c.id=st.class_id
                JOIN transport_routes r ON r.id=s.route_id
                LEFT JOIN academic_years ay ON ay.id=s.academic_year_id
                WHERE {' AND '.join(where)}
                ORDER BY r.name, st.last_name, st.first_name""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        self._require_permission("transport.view")
        routes  = fetch_one("SELECT COUNT(*) AS n FROM transport_routes WHERE is_active=1")
        on_bus  = fetch_one(
            "SELECT COUNT(DISTINCT student_id) AS n FROM transport_subscriptions WHERE status='active'"
        )
        return {
            "active_routes":  routes["n"] if routes else 0,
            "students_on_bus": on_bus["n"] if on_bus else 0,
        }


transport_service = TransportService()
