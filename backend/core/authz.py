"""
Centralized authorization engine.
This is the ONLY place where access-control decisions are made.
No role checks, no permission lists in controllers.
"""
from __future__ import annotations
from database.db import fetch_one, fetch_all


def compute_effective_permissions(user_id: int) -> list[str]:
    """
    Compute a user's full permission set from DB:
      role permissions (via user_roles → role_permissions → permissions)
      + ALLOW overrides − DENY overrides
    Call this at login and store result in the token.
    """
    # Superadmin: platform owner — unconditional wildcard, no DB lookup needed
    user_row = fetch_one("SELECT role FROM users WHERE id=?", (user_id,))
    if user_row and user_row["role"] == "superadmin":
        return ["*"]

    # Admin wildcard: if any role grants '*', return immediately
    wildcard = fetch_one(
        """SELECT 1 FROM user_roles ur
           JOIN role_permissions rp ON rp.role_id = ur.role_id
           JOIN permissions p ON p.id = rp.permission_id
           WHERE ur.user_id = ? AND p.code = '*'""",
        (user_id,),
    )
    if wildcard:
        return ["*"]

    rows = fetch_all(
        """SELECT DISTINCT p.code
           FROM user_roles ur
           JOIN role_permissions rp ON rp.role_id = ur.role_id
           JOIN permissions p ON p.id = rp.permission_id
           WHERE ur.user_id = ?""",
        (user_id,),
    )
    perm_set: set[str] = {r["code"] for r in rows}

    overrides = fetch_all(
        """SELECT permission, effect FROM user_permission_overrides
           WHERE user_id = ?
           AND (expires_at IS NULL OR expires_at > datetime('now'))""",
        (user_id,),
    )
    for ov in overrides:
        if ov["effect"] == "ALLOW":
            perm_set.add(ov["permission"])
        elif ov["effect"] == "DENY":
            perm_set.discard(ov["permission"])

    return sorted(perm_set)


def authorize(user: dict, action: str, context: dict | None = None) -> bool:
    """
    Single authorization entry point. Use this everywhere.

    Always re-reads permissions from DB so that role revocations and
    overrides take effect immediately — no re-login required.

    Context keys: class_id, subject_id
    """
    if not user:
        return False

    # Fast path: wildcard from token (admin never changes)
    if "*" in user.get("permissions", []):
        return True

    user_id = user.get("id")
    if not user_id:
        return False

    # Always re-read from DB — catches role revocations without re-login
    current_perms = compute_effective_permissions(user_id)

    if "*" in current_perms:
        return True

    if action not in current_perms:
        return False

    # Context check (class/subject scoping)
    if context:
        return _check_context(user_id, context)

    return True


def _check_context(user_id: int, context: dict) -> bool:
    """
    Verify the user is assigned to the given class/subject scope.
    Users with NO assignments are treated as global-scope (e.g. academic officer).
    """
    class_id   = context.get("class_id")
    subject_id = context.get("subject_id")

    # No relevant context keys → pass
    if not class_id and not subject_id:
        return True

    # Does this user have ANY scoped assignment at all?
    has_any = fetch_one(
        """SELECT 1 FROM teacher_assignments WHERE user_id = ? AND is_active = 1
           UNION SELECT 1 FROM class_teacher_assignments WHERE user_id = ? AND is_active = 1""",
        (user_id, user_id),
    )
    # No assignments → global access (academic officer, head teacher, etc.)
    if not has_any:
        return True

    if class_id and subject_id:
        return bool(fetch_one(
            """SELECT 1 FROM teacher_assignments
               WHERE user_id=? AND class_id=? AND subject_id=? AND is_active=1""",
            (user_id, class_id, subject_id),
        ))

    if class_id:
        ct = fetch_one(
            "SELECT 1 FROM class_teacher_assignments WHERE user_id=? AND class_id=? AND is_active=1",
            (user_id, class_id),
        )
        if ct:
            return True
        ta = fetch_one(
            "SELECT 1 FROM teacher_assignments WHERE user_id=? AND class_id=? AND is_active=1",
            (user_id, class_id),
        )
        return bool(ta)

    return True
