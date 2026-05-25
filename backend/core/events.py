"""
Internal synchronous event bus.

Modules emit events; other modules subscribe without knowing about each other.
This is the primary mechanism for cross-module side effects.

Usage:
    # Subscribe at startup (e.g., in a service's __init__ or module-level):
    event_bus.subscribe("payment.recorded", notification_service.on_payment_received)

    # Emit when something happens:
    event_bus.emit("payment.recorded", {"student_id": 1, "amount": 50000, ...})
"""

from __future__ import annotations
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger(__name__)


@dataclass
class Event:
    type: str
    payload: dict = field(default_factory=dict)
    actor_id: int | None = None
    actor_role: str | None = None


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._middleware: list[Callable[[Event], None]] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._handlers[event_type].append(handler)
        log.debug("EventBus: subscribed %s → %s", event_type, handler.__qualname__)

    def subscribe_many(self, event_types: list[str], handler: Callable[[Event], None]) -> None:
        for et in event_types:
            self.subscribe(et, handler)

    def use(self, middleware: Callable[[Event], None]) -> None:
        """Add middleware that runs before all handlers (logging, metrics, etc.)."""
        self._middleware.append(middleware)

    def emit(self, event_type: str, payload: dict | None = None,
             actor_id: int | None = None, actor_role: str | None = None) -> None:
        event = Event(type=event_type, payload=payload or {}, actor_id=actor_id, actor_role=actor_role)
        for mw in self._middleware:
            try:
                mw(event)
            except Exception:
                log.exception("EventBus middleware error for %s", event_type)

        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                log.exception("EventBus handler error: %s → %s", event_type, handler.__qualname__)

    def handlers_for(self, event_type: str) -> list[Callable]:
        return list(self._handlers.get(event_type, []))


# Module-level singleton — import this everywhere
event_bus = EventBus()


# Standard event type constants (prevents typos)
class Events:
    # Finance
    PAYMENT_RECORDED    = "payment.recorded"
    PAYMENT_REVERSED    = "payment.reversed"
    INVOICE_GENERATED   = "invoice.generated"
    INVOICE_VOIDED      = "invoice.voided"
    WAIVER_APPROVED     = "waiver.approved"
    EXPENSE_RECORDED    = "expense.recorded"

    # Grades
    GRADES_SUBMITTED    = "grades.submitted"
    GRADES_APPROVED     = "grades.approved"
    GRADES_RETURNED     = "grades.returned"
    GRADES_PUBLISHED    = "grades.published"
    GRADES_LOCKED       = "grades.locked"
    CHANGE_REQUEST_CREATED   = "grade_change.requested"
    CHANGE_REQUEST_RESOLVED  = "grade_change.resolved"

    # Attendance
    ATTENDANCE_MARKED   = "attendance.marked"
    LEAVE_REQUESTED     = "leave.requested"
    LEAVE_REVIEWED      = "leave.reviewed"

    # Students
    STUDENT_ENROLLED    = "student.enrolled"
    STUDENT_PROMOTED    = "student.promoted"
    STUDENT_TRANSFERRED = "student.transferred"

    # Auth
    USER_LOGIN          = "auth.login"
    USER_LOGOUT         = "auth.logout"
    USER_CREATED        = "auth.user_created"
