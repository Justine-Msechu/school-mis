"""
auth/rbac.py — RBAC guard decorator and scope helpers.

Usage:
    from auth.rbac import require, get_class_scope, check_class_access

    @require("finance.view")
    def open_finance_tab(): ...

    scope = get_class_scope()   # None = global access, [] = no access, [1,3] = class IDs
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
# storekeeper is excluded — they access students only through inventory.issue
# and receive a filtered eligibility-only response (no class scope needed).
_GLOBAL_ROLES = frozenset({
    "admin", "head_teacher", "academic",
    "accountant", "welfare_officer",
})


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
