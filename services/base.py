"""
services/base.py — Base class for all domain services.

Every service inherits from BaseService which provides:
  _enforce(action, subject, data, extra)  — policy check + raise on deny
  _audit(action, table, record_id, ...)   — write audit log entry
  _session                                — current session singleton
  _engine                                 — policy engine singleton
"""

from __future__ import annotations
import json
import logging
from typing import Optional

log = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised when a service action fails due to validation or business rules."""
    pass


class PolicyViolation(ServiceError):
    """Raised when the policy engine denies an action."""
    def __init__(self, message: str, rule: str = ""):
        super().__init__(message)
        self.rule = rule


class BaseService:

    def __init__(self):
        from policy.engine import policy_engine
        from auth.session import session
        self._engine = policy_engine
        self._session = session

    # ── Policy enforcement ────────────────────────────────────────────────────

    def _enforce(self, action: str, subject: dict,
                 data: dict | None = None,
                 extra: dict | None = None):
        """
        Build a PolicyContext and call policy_engine.enforce().
        Translates PolicyViolation from engine → services.PolicyViolation.
        """
        from policy.result import PolicyContext
        from policy.engine import PolicyViolation as EngineViolation

        ctx = PolicyContext(
            action=action,
            actor_id=self._session.user_id,
            actor_role=self._session.role or "",
            subject=subject,
            data=data or {},
            extra=extra or {},
        )
        try:
            return self._engine.enforce(ctx)
        except EngineViolation as exc:
            raise PolicyViolation(str(exc), rule=getattr(exc, "rule", ""))

    def _evaluate(self, action: str, subject: dict,
                  data: dict | None = None,
                  extra: dict | None = None):
        """Like _enforce but returns PolicyResult without raising."""
        from policy.result import PolicyContext
        ctx = PolicyContext(
            action=action,
            actor_id=self._session.user_id,
            actor_role=self._session.role or "",
            subject=subject,
            data=data or {},
            extra=extra or {},
        )
        return self._engine.evaluate(ctx)

    # ── Audit ─────────────────────────────────────────────────────────────────

    def _audit(self, action: str, table: str,
               record_id: Optional[int] = None, detail: str = "",
               before: Optional[dict] = None, after: Optional[dict] = None):
        from database.db import db_write_audit
        db_write_audit(
            user_id=self._session.user_id,
            action=action,
            table_name=table,
            record_id=record_id,
            detail=detail,
            before_state=before,
            after_state=after,
        )

    # ── RBAC guard ────────────────────────────────────────────────────────────

    def _require_permission(self, permission: str):
        """Raise ServiceError if the current user lacks a permission."""
        if not self._session.can(permission):
            raise ServiceError(
                f"Your role ({self._session.role_label}) does not have "
                f"permission: {permission}"
            )
