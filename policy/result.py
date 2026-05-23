"""
policy/result.py — Data structures for the Policy Engine.

PolicyContext  carries everything the rule function needs to make a decision.
PolicyResult   is what every rule function returns (allow or deny + reason).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PolicyContext:
    """Everything a rule needs to evaluate a business decision."""
    action: str               # e.g. "payment.record", "inventory.issue"
    actor_id: Optional[int]   # user performing the action (None = system)
    actor_role: str           # role string from ROLES dict
    subject: dict             # primary entity: bill, student, item, …
    data: dict = field(default_factory=dict)   # action payload (amounts, dates, …)
    extra: dict = field(default_factory=dict)  # supplementary context (look-ups)


@dataclass
class PolicyResult:
    """Decision returned by a rule function."""
    allowed: bool
    reason: str = ""
    rule_name: str = ""
    metadata: dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.allowed

    # ── Convenience constructors ──────────────────────────────────────────────
    @classmethod
    def allow(cls, reason: str = "", rule_name: str = "") -> "PolicyResult":
        return cls(allowed=True, reason=reason, rule_name=rule_name)

    @classmethod
    def deny(cls, reason: str, rule_name: str = "") -> "PolicyResult":
        return cls(allowed=False, reason=reason, rule_name=rule_name)
