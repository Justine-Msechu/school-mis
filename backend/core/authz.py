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

    Priority order:
      1. Wildcard ('*') in token permissions → always True
      2. DB DENY override → always False
      3. DB ALLOW override → True (then context check)
      4. Token permissions → True (then context check)
      5. False

    Context keys: class_id, subject_id
    """
    if not user:
        return False

    # Wildcard (admin)
    if "*" in user.get("permissions", []):
        return True

    user_id = user.get("id")
    if not user_id:
        return False

    # 1. Hard DENY override (authoritative, checked against DB on every request)
    deny = fetch_one(
        """SELECT 1 FROM user_permission_overrides
           WHERE user_id = ? AND permission = ? AND effect = 'DENY'
           AND (expires_at IS NULL OR expires_at > datetime('now'))""",
        (user_id, action),
    )
    if deny:
        return False

    # 2. ALLOW override (DB)
    allow_override = fetch_one(
        """SELECT 1 FROM user_permission_overrides
           WHERE user_id = ? AND permission = ? AND effect = 'ALLOW'
           AND (expires_at IS NULL OR expires_at > datetime('now'))""",
        (user_id, action),
    )
    has_perm = bool(allow_override) or (action in user.get("permissions", []))

    if not has_perm:
        return False

    # 3. Context check
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
