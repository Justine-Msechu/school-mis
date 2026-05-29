from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from backend.core.security import require_permission
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["transport"])
Usr = Annotated[dict, Depends(require_auth)]


def _audit(user_id: int, action: str, table: str, record_id: int | None = None, detail: str = ""):
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user_id, action, table, record_id, detail),
        )
    except Exception:
        pass


@router.get("/routes")
def get_routes(user: Usr):
    require_permission(user, "transport.view")
    rows = fetch_all(
        """SELECT r.*,
                   (SELECT COUNT(*) FROM transport_subscriptions s
                    WHERE s.route_id=r.id AND s.status='active') AS student_count
            FROM transport_routes r WHERE r.is_active=1 ORDER BY r.name"""
    )
    return [dict(r) for r in rows]


class RoutePayload(BaseModel):
    name:         str
    description:  str = ""
    fare:         float = 0
    vehicle_no:   str = ""
    driver_name:  str = ""
    driver_phone: str = ""


@router.post("/routes")
def create_route(body: RoutePayload, user: Usr):
    require_permission(user, "transport.manage")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Route name is required.")
    route_id = execute(
        """INSERT INTO transport_routes
           (name, description, vehicle_no, driver_name, driver_phone,
            fare_term1, fare_term2, fare_term3)
           VALUES (?,?,?,?,?,?,?,?)""",
        (name,
         body.description.strip() or None,
         body.vehicle_no.strip() or None,
         body.driver_name.strip() or None,
         body.driver_phone.strip() or None,
         body.fare, body.fare, body.fare),
    )
    _audit(user["id"], "route_added", "transport_routes", route_id, name)
    return dict(fetch_one("SELECT * FROM transport_routes WHERE id=?", (route_id,)))


@router.put("/routes/{route_id}")
def update_route(route_id: int, body: RoutePayload, user: Usr):
    require_permission(user, "transport.manage")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Route name is required.")
    execute(
        """UPDATE transport_routes SET
           name=?, description=?, vehicle_no=?, driver_name=?, driver_phone=?,
           fare_term1=?, fare_term2=?, fare_term3=?
           WHERE id=?""",
        (name,
         body.description.strip() or None,
         body.vehicle_no.strip() or None,
         body.driver_name.strip() or None,
         body.driver_phone.strip() or None,
         body.fare, body.fare, body.fare,
         route_id),
    )
    _audit(user["id"], "route_updated", "transport_routes", route_id, name)
    return dict(fetch_one("SELECT * FROM transport_routes WHERE id=?", (route_id,)))


@router.get("/routes/{route_id}/students")
def get_route_students(route_id: int, user: Usr):
    require_permission(user, "transport.view")
    rows = fetch_all(
        """SELECT s.*, s.notes AS pickup_point,
                   st.first_name||' '||st.last_name AS student_name,
                   st.admission_no, c.name AS class_name,
                   r.name AS route_name,
                   ay.label AS year_label
            FROM transport_subscriptions s
            JOIN students st ON st.id=s.student_id
            LEFT JOIN classes c ON c.id=st.class_id
            JOIN transport_routes r ON r.id=s.route_id
            LEFT JOIN academic_years ay ON ay.id=s.academic_year_id
            WHERE s.route_id=? AND s.status='active'
            ORDER BY st.last_name, st.first_name""",
        (route_id,),
    )
    return [dict(r) for r in rows]


class AssignBody(BaseModel):
    student_id:        int
    route_id:          int
    academic_year_id:  int
    term:              int = 1
    pickup_point:      str = ""


@router.post("/assign")
def assign_student(body: AssignBody, user: Usr):
    require_permission(user, "transport.assign")
    existing = fetch_one(
        """SELECT id FROM transport_subscriptions
           WHERE student_id=? AND route_id=? AND academic_year_id=? AND term=?
             AND status='active'""",
        (body.student_id, body.route_id, body.academic_year_id, body.term),
    )
    if existing:
        raise HTTPException(400, "Student is already assigned to this route for the selected term.")
    sub_id = execute(
        """INSERT INTO transport_subscriptions
           (student_id, route_id, academic_year_id, term, status, notes, assigned_by)
           VALUES (?,?,?,?,'active',?,?)""",
        (body.student_id, body.route_id, body.academic_year_id, body.term,
         body.pickup_point or None, user["id"]),
    )
    _audit(user["id"], "transport_assigned", "transport_subscriptions", sub_id,
           f"Student {body.student_id} → Route {body.route_id} T{body.term}")
    return {"subscription_id": sub_id, "ok": True}


@router.delete("/subscriptions/{sub_id}")
def unassign_student(sub_id: int, user: Usr):
    require_permission(user, "transport.assign")
    execute("UPDATE transport_subscriptions SET status='cancelled' WHERE id=?", (sub_id,))
    _audit(user["id"], "transport_cancelled", "transport_subscriptions", sub_id)
    return {"ok": True}


@router.get("/stats")
def get_stats(user: Usr):
    try:
        require_permission(user, "transport.view")
        routes = fetch_one("SELECT COUNT(*) AS n FROM transport_routes WHERE is_active=1")
        on_bus = fetch_one(
            "SELECT COUNT(DISTINCT student_id) AS n FROM transport_subscriptions WHERE status='active'"
        )
        return {
            "active_routes":   routes["n"] if routes else 0,
            "students_on_bus": on_bus["n"] if on_bus else 0,
        }
    except Exception:
        return {}
