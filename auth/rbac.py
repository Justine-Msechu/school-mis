"""
auth/rbac.py — RBAC guard decorator and scope helpers.

Usage:
    from auth.rbac import require, get_class_scope, check_class_access,
                          check_subject_access, get_portal_student_id,
                          get_portal_children_ids
"""

from functools import wraps
from auth.session import session


def require(permission: str):
    """Decorator — raises PermissionError if current user lacks the permission."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            session.require(permission)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Roles with unrestricted (school-wide) class access.
_GLOBAL_ROLES = frozenset({
    "admin", "head_teacher", "academic",
    "accountant", "welfare_officer",
})


# ── Class-level scope ─────────────────────────────────────────────────────────

def get_class_scope() -> list | None:
    """
    Returns the list of class IDs the current user may access.
    None  → no restriction (global access)
    []    → no classes (effectively no access)
    [1,2] → only these class IDs
    """
    if not session.is_logged_in:
        return []

    if session.role in _GLOBAL_ROLES:
        return None  # unrestricted

    # Portal roles have no class scope (filtered differently by student/parent)
    if session.role in ("student_portal", "parent_portal"):
        return []

    # Check DB for explicit class scopes
    try:
        from database.db import fetch_all
        scopes = fetch_all(
            "SELECT scope_value FROM user_scopes "
            "WHERE user_id=? AND scope_type='CLASS'",
            (session.user_id,)
        )
        if scopes:
            return [int(s["scope_value"]) for s in scopes if s["scope_value"]]
    except Exception:
        pass

    # Fall back: use the class assigned to this teacher
    try:
        from database.db import fetch_one
        if session.user and session.user.get("teacher_id"):
            cls = fetch_one(
                "SELECT id FROM classes WHERE teacher_id=?",
                (session.user["teacher_id"],)
            )
            if cls:
                return [cls["id"]]
    except Exception:
        pass

    return []


def check_class_access(class_id: int) -> bool:
    """True if the current user can access the given class."""
    scope = get_class_scope()
    return scope is None or class_id in scope


# ── Subject-level scope (teacher domain restriction) ─────────────────────────

def get_subject_scope() -> list | None:
    """
    Returns list of (class_id, subject_id) tuples the current user may teach.
    None  → unrestricted (global roles, admins, etc.)
    []    → no subject access
    [(c,s), …] → only these class/subject combos
    """
    if not session.is_logged_in:
        return []

    if session.role in _GLOBAL_ROLES:
        return None

    if session.role not in ("subject_teacher", "class_teacher"):
        return []

    teacher_id = session.user.get("teacher_id") if session.user else None
    if not teacher_id:
        return []

    try:
        from database.db import fetch_all
        rows = fetch_all(
            "SELECT class_id, subject_id FROM teacher_subjects WHERE teacher_id=?",
            (teacher_id,)
        )
        return [(r["class_id"], r["subject_id"]) for r in rows]
    except Exception:
        return []


def check_subject_access(class_id: int, subject_id: int) -> bool:
    """
    True if the current user is authorised to teach this class/subject combo.
    Global roles always return True.
    """
    scope = get_subject_scope()
    return scope is None or (class_id, subject_id) in scope


# ── Portal-account lookups ────────────────────────────────────────────────────

def get_portal_student_id() -> int | None:
    """For a student_portal user, return the linked student's DB id."""
    if not session.is_logged_in or session.role != "student_portal":
        return None
    try:
        from database.db import fetch_one
        row = fetch_one(
            "SELECT student_id FROM student_portal_accounts WHERE user_id=?",
            (session.user_id,)
        )
        return row["student_id"] if row else None
    except Exception:
        return None


def get_portal_children_ids() -> list[int]:
    """For a parent_portal user, return the list of linked student ids."""
    if not session.is_logged_in or session.role != "parent_portal":
        return []
    try:
        from database.db import fetch_all
        rows = fetch_all(
            "SELECT student_id FROM parent_portal_accounts WHERE user_id=?",
            (session.user_id,)
        )
        return [r["student_id"] for r in rows]
    except Exception:
        return []
