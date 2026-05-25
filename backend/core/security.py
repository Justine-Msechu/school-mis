"""
Authorization helpers for the FastAPI layer.

All runtime authorization decisions go through backend.core.authz.authorize().
The ROLE_PERMISSIONS and ROLE_CONDITIONS dicts below are LEGACY — they are NOT
used for any runtime checks. All permissions live in the database and are
managed through the Roles & Access UI.

require_permission() and role_filter_sql() are kept so existing callers
continue to work without modification.
"""

from __future__ import annotations
from backend.core.exceptions import PermissionError as AppPermError
from backend.core.authz import authorize as _authorize

# Role → flat permission set (matches the PyQt6 ROLES dict)
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "head_teacher": {
        "student.view", "student.promote",
        "teachers.view", "teachers.manage",
        "classes.view", "classes.manage",
        "attendance.view",
        "grades.view", "grades.approve", "grades.publish",
        "grades.change_request.review",
        "finance.view", "finance.structure.view", "finance.billing.generate",
        "finance.waiver.approve", "finance.report",
        "welfare.view", "welfare.classify", "welfare.edit",
        "welfare.verify", "welfare.sponsor.manage",
        "accounting.view", "accounting.report",
        "reports.view", "reports.academic", "reports.finance",
        "reports.welfare", "reports.inventory",
        "settings.view", "settings.school.manage",
        "settings.years.manage", "settings.users.manage",
        "library.view", "transport.view", "transport.manage",
        "health.view", "health.record", "health.report",
        "homework.view", "leave.review",
        "audit.view",
        "enrollment.view", "enrollment.manage",
        "guardian.view", "guardian.manage",
        "timetable.view", "timetable.manage",
        "report_cards.view", "report_cards.generate", "report_cards.publish", "report_cards.comment",
    },
    "academic": {
        "student.view", "student.create", "student.edit",
        "teachers.view",
        "classes.view", "classes.manage",
        "attendance.view", "attendance.mark",
        "grades.view", "grades.approve", "grades.publish",
        "grades.change_request.review",
        "welfare.view", "transport.view",
        "homework.view", "leave.review",
        "reports.view", "reports.academic", "reports.welfare",
        "settings.view",
        "enrollment.view", "enrollment.manage",
        "guardian.view", "guardian.manage",
        "timetable.view", "timetable.manage",
        "report_cards.view", "report_cards.generate", "report_cards.publish", "report_cards.comment",
    },
    "accountant": {
        "student.view",
        "finance.view", "finance.structure.view",
        "finance.payment.record", "finance.payment.void",
        "finance.billing.generate",
        "finance.waiver.create",
        "finance.report",
        "accounting.view", "accounting.expense.record", "accounting.report",
        "transport.view",
        "reports.view", "reports.finance",
    },
    "welfare_officer": {
        "student.view",
        "welfare.view", "welfare.classify", "welfare.edit",
        "welfare.verify", "welfare.sponsor.manage",
        "health.view", "health.record",
        "leave.review",
        "reports.view", "reports.welfare",
    },
    "class_teacher": {
        "student.view",
        "classes.view",
        "attendance.view", "attendance.mark",
        "grades.view",
        "homework.view",
        "leave.review",
        "reports.view", "reports.academic",
        "enrollment.view",
        "timetable.view",
        "report_cards.view", "report_cards.comment",
        "guardian.view",
    },
    "subject_teacher": {
        "student.view",
        "attendance.view",
        "grades.view", "grades.write", "grades.submit",
        "grades.change_request.create",
        "homework.view", "homework.write",
        "reports.view", "reports.academic",
        "timetable.view",
        "report_cards.view",
    },
}

# Conditions that limit row-level access for non-admin roles
ROLE_CONDITIONS: dict[str, dict[str, list[str]]] = {
    "class_teacher": {
        "attendance.mark":  ["own_class"],
        "attendance.view":  ["own_class"],
        "grades.view":      ["own_class"],
        "student.view":     ["own_class"],
    },
    "subject_teacher": {
        "grades.write":     ["own_class", "own_subject"],
        "grades.submit":    ["own_class", "own_subject"],
        "grades.view":      ["own_class", "own_subject"],
        "homework.write":   ["own_subject"],
        "student.view":     ["own_class"],
    },
}


def has_permission(actor: dict, permission: str) -> bool:
    role = actor.get("role", "")
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


def get_conditions(actor: dict, permission: str) -> list[str]:
    role = actor.get("role", "")
    return ROLE_CONDITIONS.get(role, {}).get(permission, [])


def require_permission(actor: dict, permission: str, context: dict | None = None) -> None:
    """
    Raise AppPermError if the actor lacks the permission.
    Delegates to authorize() in backend.core.authz — the single decision point.
    `context` may contain class_id and/or subject_id for scope checks.
    """
    if not _authorize(actor, permission, context):
        raise AppPermError(permission)


def role_filter_sql(actor: dict, permission: str, alias: str = "") -> tuple[str, list]:
    """
    Return (WHERE fragment, params) to filter rows by the actor's scope.
    Used in repositories to apply row-level filtering automatically.

    Example:
        where, params = role_filter_sql(actor, "grades.view", alias="g")
        # → " AND g.class_id IN (SELECT id FROM classes WHERE teacher_id=?)", [actor_id]
    """
    role = actor.get("role", "")
    conditions = ROLE_CONDITIONS.get(role, {}).get(permission, [])
    prefix = f"{alias}." if alias else ""
    where_parts: list[str] = []
    params: list = []

    teacher_id = actor.get("teacher_id") or actor.get("id")

    for cond in conditions:
        if cond == "own_class":
            where_parts.append(
                f"{prefix}class_id IN (SELECT id FROM classes WHERE teacher_id = ?)"
            )
            params.append(teacher_id)
        elif cond == "own_subject":
            where_parts.append(
                f"{prefix}subject_id IN "
                f"(SELECT subject_id FROM teacher_subjects WHERE teacher_id = ?)"
            )
            params.append(teacher_id)

    clause = (" AND " + " AND ".join(where_parts)) if where_parts else ""
    return clause, params
