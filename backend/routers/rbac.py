"""
RBAC management router.
All authorization decisions use authorize() — no role-name checks.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from backend.core.authz import authorize
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["rbac"])
Usr = Annotated[dict, Depends(require_auth)]


# ── Roles ──────────────────────────────────────────────────────────────────────

@router.get("/roles")
def list_roles(user: Usr):
    """List all roles with their permissions."""
    if not authorize(user, "settings.roles.manage") and not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied")
    rows = fetch_all("""
        SELECT r.id, r.name, r.label, r.color, r.is_system,
               GROUP_CONCAT(p.code, ',') AS permissions
        FROM roles r
        LEFT JOIN role_permissions rp ON rp.role_id = r.id
        LEFT JOIN permissions p ON p.id = rp.permission_id
        GROUP BY r.id
        ORDER BY r.name
    """)
    result = []
    for r in rows:
        d = dict(r)
        d["permissions"] = [p for p in (d["permissions"] or "").split(",") if p]
        result.append(d)
    return result


class RoleCreatePayload(BaseModel):
    name:  str
    label: str
    color: str = "#6B7280"


@router.post("/roles")
def create_role(body: RoleCreatePayload, user: Usr):
    if not authorize(user, "settings.roles.manage"):
        raise HTTPException(403, "Permission denied: settings.roles.manage")
    existing = fetch_one("SELECT id FROM roles WHERE name=?", (body.name,))
    if existing:
        raise HTTPException(400, f"Role '{body.name}' already exists")
    row_id = execute(
        "INSERT INTO roles (name, label, color, is_system) VALUES (?,?,?,0)",
        (body.name, body.label, body.color),
    )
    return dict(fetch_one("SELECT * FROM roles WHERE id=?", (row_id,)))


class RoleUpdatePayload(BaseModel):
    label: str
    color: str = "#6B7280"


@router.put("/roles/{role_id}")
def update_role(role_id: int, body: RoleUpdatePayload, user: Usr):
    if not authorize(user, "settings.roles.manage"):
        raise HTTPException(403, "Permission denied: settings.roles.manage")
    target = fetch_one("SELECT * FROM roles WHERE id=?", (role_id,))
    if not target:
        raise HTTPException(404, "Role not found")
    execute(
        "UPDATE roles SET label=?, color=? WHERE id=?",
        (body.label, body.color, role_id),
    )
    return dict(fetch_one("SELECT * FROM roles WHERE id=?", (role_id,)))


@router.get("/roles/{role_id}/permissions")
def get_role_permissions(role_id: int, user: Usr):
    if not authorize(user, "settings.roles.manage"):
        raise HTTPException(403, "Permission denied: settings.roles.manage")
    role = fetch_one("SELECT id, name, label FROM roles WHERE id=?", (role_id,))
    if not role:
        raise HTTPException(404, "Role not found")
    rows = fetch_all("""
        SELECT p.id, p.code, p.domain, p.action, p.description, p.scope_type
        FROM role_permissions rp
        JOIN permissions p ON p.id = rp.permission_id
        WHERE rp.role_id = ?
        ORDER BY p.code
    """, (role_id,))
    return {"role": dict(role), "permissions": [dict(r) for r in rows]}


class SetRolePermissionsPayload(BaseModel):
    permission_codes: list[str]


@router.put("/roles/{role_id}/permissions")
def set_role_permissions(role_id: int, body: SetRolePermissionsPayload, user: Usr):
    """Replace all permissions for a role."""
    if not authorize(user, "settings.roles.manage"):
        raise HTTPException(403, "Permission denied: settings.roles.manage")
    role = fetch_one("SELECT id FROM roles WHERE id=?", (role_id,))
    if not role:
        raise HTTPException(404, "Role not found")

    execute("DELETE FROM role_permissions WHERE role_id=?", (role_id,))
    for code in body.permission_codes:
        perm = fetch_one("SELECT id FROM permissions WHERE code=?", (code,))
        if perm:
            execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?,?)",
                (role_id, perm["id"]),
            )
    return {"ok": True, "role_id": role_id, "permissions_set": len(body.permission_codes)}


# ── Permissions catalog ────────────────────────────────────────────────────────

@router.get("/permissions")
def list_permissions(user: Usr):
    """List all permissions in the catalog."""
    if not authorize(user, "settings.roles.manage") and not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied")
    rows = fetch_all("SELECT * FROM permissions ORDER BY domain, action")
    return [dict(r) for r in rows]


# ── User permission overrides ──────────────────────────────────────────────────

@router.get("/users/{uid}/overrides")
def get_user_overrides(uid: int, user: Usr):
    if not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied: settings.users.manage")
    target = fetch_one("SELECT id, username, full_name, role FROM users WHERE id=?", (uid,))
    if not target:
        raise HTTPException(404, "User not found")
    rows = fetch_all("""
        SELECT upo.*, u.full_name AS granted_by_name
        FROM user_permission_overrides upo
        LEFT JOIN users u ON u.id = upo.granted_by
        WHERE upo.user_id = ?
        ORDER BY upo.permission
    """, (uid,))
    return {"user": dict(target), "overrides": [dict(r) for r in rows]}


class OverridePayload(BaseModel):
    permission: str
    effect:     str          # 'ALLOW' or 'DENY'
    reason:     str = ""
    expires_at: str | None = None


@router.post("/users/{uid}/overrides")
def add_user_override(uid: int, body: OverridePayload, user: Usr):
    if not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied: settings.users.manage")
    if body.effect not in ("ALLOW", "DENY"):
        raise HTTPException(400, "effect must be 'ALLOW' or 'DENY'")
    target = fetch_one("SELECT id FROM users WHERE id=?", (uid,))
    if not target:
        raise HTTPException(404, "User not found")
    # Upsert: update if already exists
    existing = fetch_one(
        "SELECT id FROM user_permission_overrides WHERE user_id=? AND permission=?",
        (uid, body.permission),
    )
    if existing:
        execute(
            """UPDATE user_permission_overrides
               SET effect=?, reason=?, granted_by=?, expires_at=?, created_at=datetime('now')
               WHERE user_id=? AND permission=?""",
            (body.effect, body.reason, user["id"], body.expires_at, uid, body.permission),
        )
        oid = existing["id"]
    else:
        oid = execute(
            """INSERT INTO user_permission_overrides
               (user_id, permission, effect, reason, granted_by, expires_at)
               VALUES (?,?,?,?,?,?)""",
            (uid, body.permission, body.effect, body.reason, user["id"], body.expires_at),
        )
    return dict(fetch_one("SELECT * FROM user_permission_overrides WHERE id=?", (oid,)))


@router.delete("/users/{uid}/overrides/{oid}")
def delete_user_override(uid: int, oid: int, user: Usr):
    if not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied: settings.users.manage")
    row = fetch_one("SELECT id FROM user_permission_overrides WHERE id=? AND user_id=?", (oid, uid))
    if not row:
        raise HTTPException(404, "Override not found")
    execute("DELETE FROM user_permission_overrides WHERE id=?", (oid,))
    return {"ok": True}


# ── Teacher subject assignments ────────────────────────────────────────────────

@router.get("/assignments/teacher")
def list_teacher_assignments(user: Usr, user_id: int | None = None, class_id: int | None = None):
    if not authorize(user, "teachers.manage") and not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied")
    sql = """
        SELECT ta.id, ta.user_id, ta.class_id, ta.subject_id, ta.academic_year_id,
               ta.is_active, ta.assigned_at,
               u.full_name AS teacher_name, u.role AS teacher_role,
               c.name AS class_name,
               s.name AS subject_name,
               ay.label AS year_label
        FROM teacher_assignments ta
        JOIN users u ON u.id = ta.user_id
        JOIN classes c ON c.id = ta.class_id
        JOIN subjects s ON s.id = ta.subject_id
        LEFT JOIN academic_years ay ON ay.id = ta.academic_year_id
        WHERE 1=1
    """
    params: list = []
    if user_id:
        sql += " AND ta.user_id=?"
        params.append(user_id)
    if class_id:
        sql += " AND ta.class_id=?"
        params.append(class_id)
    sql += " ORDER BY u.full_name, c.name, s.name"
    rows = fetch_all(sql, tuple(params))
    return [dict(r) for r in rows]


class TeacherAssignPayload(BaseModel):
    user_id:          int
    class_id:         int
    subject_id:       int
    academic_year_id: int | None = None
    is_active:        bool = True


@router.post("/assignments/teacher")
def assign_teacher(body: TeacherAssignPayload, user: Usr):
    if not authorize(user, "teachers.manage"):
        raise HTTPException(403, "Permission denied: teachers.manage")
    # Validate references
    if not fetch_one("SELECT id FROM users WHERE id=?", (body.user_id,)):
        raise HTTPException(404, "User not found")
    if not fetch_one("SELECT id FROM classes WHERE id=?", (body.class_id,)):
        raise HTTPException(404, "Class not found")
    if not fetch_one("SELECT id FROM subjects WHERE id=?", (body.subject_id,)):
        raise HTTPException(404, "Subject not found")
    existing = fetch_one(
        """SELECT id FROM teacher_assignments
           WHERE user_id=? AND class_id=? AND subject_id=?
           AND (academic_year_id=? OR (academic_year_id IS NULL AND ? IS NULL))""",
        (body.user_id, body.class_id, body.subject_id,
         body.academic_year_id, body.academic_year_id),
    )
    if existing:
        execute(
            "UPDATE teacher_assignments SET is_active=?, assigned_by=?, assigned_at=datetime('now') WHERE id=?",
            (1 if body.is_active else 0, user["id"], existing["id"]),
        )
        row_id = existing["id"]
    else:
        row_id = execute(
            """INSERT INTO teacher_assignments
               (user_id, class_id, subject_id, academic_year_id, is_active, assigned_by)
               VALUES (?,?,?,?,?,?)""",
            (body.user_id, body.class_id, body.subject_id,
             body.academic_year_id, 1 if body.is_active else 0, user["id"]),
        )
    return dict(fetch_one("SELECT * FROM teacher_assignments WHERE id=?", (row_id,)))


@router.delete("/assignments/teacher/{assignment_id}")
def remove_teacher_assignment(assignment_id: int, user: Usr):
    if not authorize(user, "teachers.manage"):
        raise HTTPException(403, "Permission denied: teachers.manage")
    row = fetch_one("SELECT id FROM teacher_assignments WHERE id=?", (assignment_id,))
    if not row:
        raise HTTPException(404, "Assignment not found")
    execute("DELETE FROM teacher_assignments WHERE id=?", (assignment_id,))
    return {"ok": True}


# ── Class teacher assignments ──────────────────────────────────────────────────

@router.get("/assignments/classteacher")
def list_class_teacher_assignments(user: Usr):
    if not authorize(user, "teachers.manage") and not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied")
    rows = fetch_all("""
        SELECT cta.id, cta.user_id, cta.class_id, cta.academic_year_id,
               cta.is_active, cta.assigned_at,
               u.full_name AS teacher_name,
               c.name AS class_name,
               ay.label AS year_label
        FROM class_teacher_assignments cta
        JOIN users u ON u.id = cta.user_id
        JOIN classes c ON c.id = cta.class_id
        LEFT JOIN academic_years ay ON ay.id = cta.academic_year_id
        ORDER BY c.name, u.full_name
    """)
    return [dict(r) for r in rows]


class ClassTeacherAssignPayload(BaseModel):
    user_id:          int
    class_id:         int
    academic_year_id: int | None = None
    is_active:        bool = True


@router.post("/assignments/classteacher")
def assign_class_teacher(body: ClassTeacherAssignPayload, user: Usr):
    if not authorize(user, "teachers.manage"):
        raise HTTPException(403, "Permission denied: teachers.manage")
    if not fetch_one("SELECT id FROM users WHERE id=?", (body.user_id,)):
        raise HTTPException(404, "User not found")
    if not fetch_one("SELECT id FROM classes WHERE id=?", (body.class_id,)):
        raise HTTPException(404, "Class not found")
    existing = fetch_one(
        """SELECT id FROM class_teacher_assignments
           WHERE user_id=? AND class_id=?
           AND (academic_year_id=? OR (academic_year_id IS NULL AND ? IS NULL))""",
        (body.user_id, body.class_id, body.academic_year_id, body.academic_year_id),
    )
    if existing:
        execute(
            "UPDATE class_teacher_assignments SET is_active=?, assigned_by=?, assigned_at=datetime('now') WHERE id=?",
            (1 if body.is_active else 0, user["id"], existing["id"]),
        )
        row_id = existing["id"]
    else:
        row_id = execute(
            """INSERT INTO class_teacher_assignments
               (user_id, class_id, academic_year_id, is_active, assigned_by)
               VALUES (?,?,?,?,?)""",
            (body.user_id, body.class_id, body.academic_year_id,
             1 if body.is_active else 0, user["id"]),
        )
    return dict(fetch_one("SELECT * FROM class_teacher_assignments WHERE id=?", (row_id,)))


@router.delete("/assignments/classteacher/{assignment_id}")
def remove_class_teacher_assignment(assignment_id: int, user: Usr):
    if not authorize(user, "teachers.manage"):
        raise HTTPException(403, "Permission denied: teachers.manage")
    row = fetch_one("SELECT id FROM class_teacher_assignments WHERE id=?", (assignment_id,))
    if not row:
        raise HTTPException(404, "Assignment not found")
    execute("DELETE FROM class_teacher_assignments WHERE id=?", (assignment_id,))
    return {"ok": True}


# ── User role assignments ──────────────────────────────────────────────────────

@router.get("/users/{uid}/roles")
def get_user_roles(uid: int, user: Usr):
    if not authorize(user, "settings.users.manage") and not authorize(user, "settings.roles.manage"):
        raise HTTPException(403, "Permission denied")
    target = fetch_one("SELECT id, username, full_name, role FROM users WHERE id=?", (uid,))
    if not target:
        raise HTTPException(404, "User not found")
    rows = fetch_all("""
        SELECT r.id, r.name, r.label, r.color
        FROM user_roles ur
        JOIN roles r ON r.id = ur.role_id
        WHERE ur.user_id = ?
        ORDER BY r.name
    """, (uid,))
    return {"user": dict(target), "roles": [dict(r) for r in rows]}


class SetUserRolesPayload(BaseModel):
    role_ids: list[int]


@router.put("/users/{uid}/roles")
def set_user_roles(uid: int, body: SetUserRolesPayload, user: Usr):
    """Replace all roles for a user."""
    if not authorize(user, "settings.users.manage"):
        raise HTTPException(403, "Permission denied: settings.users.manage")
    target = fetch_one("SELECT id FROM users WHERE id=?", (uid,))
    if not target:
        raise HTTPException(404, "User not found")
    execute("DELETE FROM user_roles WHERE user_id=?", (uid,))
    for role_id in body.role_ids:
        role = fetch_one("SELECT id FROM roles WHERE id=?", (role_id,))
        if role:
            execute(
                "INSERT OR IGNORE INTO user_roles (user_id, role_id, granted_by) VALUES (?,?,?)",
                (uid, role_id, user["id"]),
            )
    return {"ok": True, "user_id": uid, "roles_set": len(body.role_ids)}
