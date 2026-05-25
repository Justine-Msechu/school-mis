"""
Grade approval state machine.

Enforces valid transitions and required actor roles.
Zero external dependencies — pure Python.
"""

from __future__ import annotations
from backend.domain.shared.enums import GradeStatus
from backend.core.exceptions import StateError, PermissionError as AppPermError


# Valid transitions: {from_status: {to_status, ...}}
VALID_TRANSITIONS: dict[GradeStatus, set[GradeStatus]] = {
    GradeStatus.DRAFT:        {GradeStatus.SUBMITTED},
    GradeStatus.SUBMITTED:    {GradeStatus.UNDER_REVIEW, GradeStatus.DRAFT},
    GradeStatus.UNDER_REVIEW: {GradeStatus.APPROVED, GradeStatus.RETURNED},
    GradeStatus.RETURNED:     {GradeStatus.SUBMITTED},
    GradeStatus.APPROVED:     {GradeStatus.PUBLISHED},
    GradeStatus.PUBLISHED:    {GradeStatus.LOCKED},
    GradeStatus.LOCKED:       set(),
}

# Which roles can trigger which transitions
ROLE_TRANSITIONS: dict[str, list[tuple[GradeStatus, GradeStatus]]] = {
    "subject_teacher": [
        (GradeStatus.DRAFT, GradeStatus.SUBMITTED),
        (GradeStatus.SUBMITTED, GradeStatus.DRAFT),     # recall
        (GradeStatus.RETURNED, GradeStatus.SUBMITTED),  # resubmit after correction
    ],
    "class_teacher": [
        (GradeStatus.DRAFT, GradeStatus.SUBMITTED),
        (GradeStatus.SUBMITTED, GradeStatus.DRAFT),
        (GradeStatus.RETURNED, GradeStatus.SUBMITTED),
    ],
    "academic": [
        (GradeStatus.SUBMITTED, GradeStatus.UNDER_REVIEW),
        (GradeStatus.UNDER_REVIEW, GradeStatus.RETURNED),
        (GradeStatus.UNDER_REVIEW, GradeStatus.APPROVED),
    ],
    "head_teacher": [
        (GradeStatus.SUBMITTED, GradeStatus.UNDER_REVIEW),
        (GradeStatus.UNDER_REVIEW, GradeStatus.APPROVED),
        (GradeStatus.UNDER_REVIEW, GradeStatus.RETURNED),
        (GradeStatus.APPROVED, GradeStatus.PUBLISHED),
        (GradeStatus.PUBLISHED, GradeStatus.LOCKED),
    ],
}
# Admin can do any transition
ADMIN_ROLES = {"admin"}


def transition(current: str, target: str, actor_role: str) -> GradeStatus:
    """
    Validate and return the new status.

    Raises:
        StateError: if the transition is not valid for the current status.
        AppPermError: if the actor's role cannot trigger this transition.
    """
    try:
        c = GradeStatus(current)
        t = GradeStatus(target)
    except ValueError as e:
        raise StateError(current, target) from e

    if t not in VALID_TRANSITIONS.get(c, set()):
        raise StateError(current, f"transition to '{target}'")

    if actor_role in ADMIN_ROLES:
        return t

    allowed = ROLE_TRANSITIONS.get(actor_role, [])
    if (c, t) not in allowed:
        raise AppPermError(f"transition grades from '{current}' to '{target}'")

    return t


def can_transition(current: str, target: str, actor_role: str) -> bool:
    """Non-raising version of transition()."""
    try:
        transition(current, target, actor_role)
        return True
    except (StateError, AppPermError):
        return False


def available_transitions(current: str, actor_role: str) -> list[GradeStatus]:
    """Return the list of states this actor can move `current` to."""
    try:
        c = GradeStatus(current)
    except ValueError:
        return []
    reachable = VALID_TRANSITIONS.get(c, set())
    if actor_role in ADMIN_ROLES:
        return list(reachable)
    allowed_pairs = ROLE_TRANSITIONS.get(actor_role, [])
    return [t for (frm, t) in allowed_pairs if frm == c and t in reachable]
