"""
policy/engine.py — Central Policy Engine singleton.

Usage (registering a rule):
    from policy.engine import policy_engine

    @policy_engine.register("payment.record")
    def my_rule(ctx: PolicyContext) -> PolicyResult:
        ...

Usage (enforcing in a service):
    policy_engine.enforce(ctx)  # raises PolicyViolation on deny
    result = policy_engine.evaluate(ctx)  # returns PolicyResult, never raises
"""

from __future__ import annotations
import logging
from typing import Callable
from policy.result import PolicyContext, PolicyResult

log = logging.getLogger(__name__)


class PolicyViolation(Exception):
    """Raised when the policy engine denies an action."""
    def __init__(self, message: str, rule: str = ""):
        super().__init__(message)
        self.rule = rule


class PolicyEngine:
    """
    Central rule-evaluation engine.

    ALL rules registered for an action are evaluated in registration order.
    The first DENY short-circuits — remaining rules are skipped (AND logic).

    For OR logic, combine conditions inside a single rule function.
    """

    def __init__(self):
        self._rules: dict[str, list[Callable]] = {}
        # Per-entity overrides: (rule_name, entity_type, entity_id) → "allow"|"deny"
        self._overrides: dict[tuple, str] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, *actions: str) -> Callable:
        """Decorator: register a rule function for one or more actions."""
        def decorator(fn: Callable) -> Callable:
            for action in actions:
                self._rules.setdefault(action, []).append(fn)
            return fn
        return decorator

    # ── Override management ───────────────────────────────────────────────────

    def add_override(self, rule_name: str, entity_type: str,
                     entity_id: int, decision: str):
        """Add a run-time override (e.g. grant a specific student an exemption)."""
        self._overrides[(rule_name, entity_type, entity_id)] = decision

    def load_overrides_from_db(self):
        """Pull active overrides from the policy_overrides table."""
        try:
            from database.db import fetch_all
            rows = fetch_all(
                "SELECT policy_rule, entity_type, entity_id, decision "
                "FROM policy_overrides "
                "WHERE (expires_at IS NULL OR expires_at > date('now'))"
            )
            self._overrides.clear()
            for r in rows:
                key = (r["policy_rule"], r["entity_type"], r["entity_id"])
                self._overrides[key] = r["decision"]
        except Exception:
            pass  # table may not exist yet on first run

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, ctx: PolicyContext) -> PolicyResult:
        """
        Evaluate all rules for ctx.action. Returns first deny, or final allow.
        Never raises — use enforce() to get exceptions.
        """
        rules = self._rules.get(ctx.action, [])
        for rule_fn in rules:
            key = (rule_fn.__name__,
                   ctx.subject.get("_entity_type", ""),
                   ctx.subject.get("id", 0))
            override = self._overrides.get(key)
            if override == "allow":
                continue   # skip this rule for this entity
            if override == "deny":
                return PolicyResult.deny(
                    "Policy override (deny) applied for this entity.",
                    rule_name=rule_fn.__name__
                )

            try:
                result = rule_fn(ctx)
            except Exception as exc:
                log.exception("Policy rule %s raised", rule_fn.__name__)
                return PolicyResult.deny(
                    f"Policy evaluation error in {rule_fn.__name__}: {exc}",
                    rule_name=rule_fn.__name__
                )

            if not result.allowed:
                log.debug("DENY [%s] action=%s actor=%s — %s",
                          result.rule_name, ctx.action, ctx.actor_role, result.reason)
                return result

        return PolicyResult.allow(reason="All policies passed")

    def enforce(self, ctx: PolicyContext) -> PolicyResult:
        """Like evaluate() but raises PolicyViolation on deny."""
        result = self.evaluate(ctx)
        if not result.allowed:
            raise PolicyViolation(result.reason, rule=result.rule_name)
        return result

    def registered_actions(self) -> list[str]:
        return sorted(self._rules.keys())

    def rules_for(self, action: str) -> list[str]:
        return [fn.__name__ for fn in self._rules.get(action, [])]


# ── Singleton ─────────────────────────────────────────────────────────────────
policy_engine = PolicyEngine()
