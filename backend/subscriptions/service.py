"""
SubscriptionService — all subscription business logic.
Routers call this; never query DB directly from routers.
"""

import json, secrets, logging
from datetime import datetime, timedelta
from database.db import execute, fetch_one, fetch_all
from .providers.registry import get_provider, available_providers
from .providers.base import CheckoutSession
from .webhooks.handler import WebhookHandler
from .plan_config import PLAN_COLORS, PLAN_DESCRIPTIONS, PLAN_FEATURES

log = logging.getLogger(__name__)

_handler = WebhookHandler()


class SubscriptionService:

    # ── Plans ────────────────────────────────────────────────────────────

    def get_all_plans(self) -> list[dict]:
        rows = fetch_all(
            "SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY sort_order, billing_interval"
        )
        result = []
        for r in rows:
            p = dict(r)
            p["features"]    = json.loads(p.get("features") or "{}")
            p["color"]       = PLAN_COLORS.get(p["name"], "#94A3B8")
            p["description"] = PLAN_DESCRIPTIONS.get(p["name"], "")
            p["feature_list"]= PLAN_FEATURES.get(p["name"], [])
            result.append(p)
        return result

    def get_plan(self, name: str, interval: str) -> dict | None:
        row = fetch_one(
            "SELECT * FROM subscription_plans WHERE name=? AND billing_interval=? AND is_active=1",
            (name, interval),
        )
        return dict(row) if row else None

    # ── Current subscription status ──────────────────────────────────────

    def get_subscription_status(self, org_id) -> dict:
        sub = fetch_one(
            """SELECT s.*, p.name as plan_name, p.display_name, p.billing_interval,
                      p.price_amount, p.currency, p.max_users, p.max_students, p.features
               FROM subscriptions_v2 s
               JOIN subscription_plans p ON s.plan_id=p.id
               WHERE s.organization_id=? AND s.status NOT IN ('canceled')
               ORDER BY s.created_at DESC LIMIT 1""",
            (org_id,),
        )

        if not sub:
            # Fall back to legacy schools table
            school_row = fetch_one("SELECT * FROM schools WHERE id=?", (org_id,))
            if school_row:
                return self._legacy_status(dict(school_row))
            return self._no_subscription_status()

        d = dict(sub)
        d["features"]     = json.loads(d.get("features") or "{}")
        d["color"]        = PLAN_COLORS.get(d["plan_name"], "#94A3B8")
        d["is_active"]    = d["status"] in ("active", "trialing")
        d["days_left"]    = self._days_left(d.get("current_period_end"))
        d["warning"]      = self._compute_warning(d)
        d["grace_active"] = self._grace_active(d)
        d["providers"]    = available_providers()
        return d

    def get_subscription_history(self, org_id, limit=20) -> list[dict]:
        rows = fetch_all(
            """SELECT h.*, p.display_name as plan_display
               FROM subscription_history h
               LEFT JOIN subscription_plans p ON h.to_plan_id=p.id
               WHERE h.organization_id=?
               ORDER BY h.created_at DESC LIMIT ?""",
            (org_id, limit),
        )
        return [dict(r) for r in rows]

    # ── Create checkout session ──────────────────────────────────────────

    async def create_checkout_session(
        self,
        *,
        org_id:    int,
        org_email: str,
        org_name:  str,
        plan_name: str,
        interval:  str,
        provider:  str,
        redirect_url: str,
    ) -> CheckoutSession:
        plan = self.get_plan(plan_name, interval)
        if not plan:
            raise ValueError(f"Plan '{plan_name}' ({interval}) not found")

        prov   = get_provider(provider)
        tx_ref = f"mis-{org_id}-{plan_name}-{secrets.token_hex(6)}"

        session = await prov.create_checkout(
            tx_ref=       tx_ref,
            amount=       plan["price_amount"],
            currency=     plan["currency"],
            plan_name=    plan_name,
            interval=     interval,
            org_id=       str(org_id),
            org_email=    org_email,
            org_name=     org_name,
            redirect_url= redirect_url,
            metadata=     {"interval": interval},
        )
        # Record pending subscription
        self._ensure_pending_subscription(org_id, plan["id"], provider, tx_ref)
        return session

    # ── Verify after redirect (belt-and-suspenders) ──────────────────────

    async def verify_and_activate(self, tx_ref: str, org_id: int) -> dict:
        """
        Called when user returns from checkout page.
        Polls provider to confirm payment, then activates subscription.
        This is a fallback — the webhook should have already activated it.
        """
        # Check if webhook already activated
        sub = fetch_one(
            "SELECT status FROM subscriptions_v2 WHERE organization_id=? AND provider_subscription_id=?",
            (org_id, tx_ref),
        )
        if sub and sub["status"] == "active":
            return {"status": "active", "message": "Subscription is active"}

        # Determine provider from tx_ref format (or check pending subscription)
        pending = fetch_one(
            "SELECT provider FROM subscriptions_v2 WHERE organization_id=? AND provider_subscription_id=? AND status='pending'",
            (org_id, tx_ref),
        )
        if not pending:
            return {"status": "pending", "message": "Payment verification pending. Please wait."}

        try:
            prov   = get_provider(pending["provider"])
            result = await prov.verify_transaction(tx_ref)
        except Exception as e:
            log.error("verify_transaction failed: %s", e)
            return {"status": "pending", "message": "Could not verify payment. Please wait for confirmation."}

        if result.get("status") == "succeeded":
            # Manually trigger the activation flow (same as webhook)
            from .providers.base import ParsedWebhookEvent
            event = ParsedWebhookEvent(
                provider=   pending["provider"],
                event_id=   tx_ref,
                event_type= "payment.succeeded",
                payload=    result,
                org_id=     str(org_id),
                plan_name=  result.get("plan_name"),
                amount=     result.get("amount", 0),
                currency=   result.get("currency", "TZS"),
                tx_ref=     tx_ref,
            )
            await _handler._on_payment_succeeded(event, webhook_id=None)
            return {"status": "active", "message": "Subscription activated successfully!"}

        return {"status": result.get("status", "pending"), "message": "Payment not yet confirmed."}

    # ── Manual activation (admin / testing) ─────────────────────────────

    def manual_activate(
        self,
        org_id:    int,
        plan_name: str,
        interval:  str,
        actor_id:  int,
        days:      int | None = None,
    ) -> dict:
        plan = self.get_plan(plan_name, interval)
        if not plan:
            raise ValueError(f"Plan '{plan_name}' ({interval}) not found")

        now    = datetime.utcnow()
        period = days or (366 if interval == "yearly" else 31)
        end    = now + timedelta(days=period)
        grace  = end + timedelta(days=7)

        sub = fetch_one(
            "SELECT id, status FROM subscriptions_v2 WHERE organization_id=? AND status NOT IN ('canceled') ORDER BY created_at DESC LIMIT 1",
            (org_id,),
        )

        if sub:
            old_status = sub["status"]
            execute(
                """UPDATE subscriptions_v2
                   SET status='active', plan_id=?, provider='manual',
                       cancel_at_period_end=0,
                       current_period_start=?, current_period_end=?,
                       grace_period_end=?, updated_at=?
                   WHERE id=?""",
                (plan["id"], now.isoformat(), end.isoformat(), grace.isoformat(), now.isoformat(), sub["id"]),
            )
            sub_id = sub["id"]
            self._record_history(sub_id, org_id, "activated",
                                 from_status=old_status, to_status="active",
                                 to_plan_id=plan["id"], triggered_by="admin", actor_id=actor_id)
        else:
            execute(
                """INSERT INTO subscriptions_v2
                   (organization_id, plan_id, status, provider,
                    current_period_start, current_period_end, grace_period_end)
                   VALUES (?,?,'active','manual',?,?,?)""",
                (org_id, plan["id"], now.isoformat(), end.isoformat(), grace.isoformat()),
            )
            new_row = fetch_one(
                "SELECT id FROM subscriptions_v2 WHERE organization_id=? ORDER BY created_at DESC LIMIT 1",
                (org_id,),
            )
            sub_id = new_row["id"] if new_row else None
            if sub_id:
                self._record_history(sub_id, org_id, "activated",
                                     to_status="active", to_plan_id=plan["id"],
                                     triggered_by="admin", actor_id=actor_id)

        # Sync legacy schools table
        execute(
            "UPDATE schools SET plan=?, subscription_status='active', is_active=1, trial_ends=? WHERE id=?",
            (plan_name, end.date().isoformat(), org_id),
        )
        return {"status": "active", "plan": plan_name, "expires": end.date().isoformat()}

    # ── Cancel ───────────────────────────────────────────────────────────

    def cancel_subscription(self, org_id: int, actor_id: int, reason: str = "") -> dict:
        sub = fetch_one(
            "SELECT id, status FROM subscriptions_v2 WHERE organization_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
            (org_id,),
        )
        if not sub:
            raise ValueError("No active subscription found")

        execute(
            "UPDATE subscriptions_v2 SET cancel_at_period_end=1, updated_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), sub["id"]),
        )
        self._record_history(sub["id"], org_id, "cancel_requested",
                             from_status="active", triggered_by="admin",
                             actor_id=actor_id, notes=reason)
        return {"status": "will_cancel", "message": "Subscription will cancel at end of current period."}

    # ── Invoices ─────────────────────────────────────────────────────────

    def get_invoices(self, org_id: int, page: int = 1, per_page: int = 20) -> dict:
        offset = (page - 1) * per_page
        _total_row = fetch_one("SELECT COUNT(*) as n FROM sub_invoices WHERE organization_id=?", (org_id,))
        total = _total_row["n"] if _total_row else 0
        rows   = fetch_all(
            "SELECT * FROM sub_invoices WHERE organization_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (org_id, per_page, offset),
        )
        return {"total": total, "page": page, "per_page": per_page, "items": [dict(r) for r in rows]}

    # ── Internal helpers ─────────────────────────────────────────────────

    def _ensure_pending_subscription(self, org_id, plan_id, provider, tx_ref):
        existing = fetch_one(
            "SELECT id FROM subscriptions_v2 WHERE organization_id=? AND status='pending'",
            (org_id,),
        )
        if existing:
            execute(
                "UPDATE subscriptions_v2 SET plan_id=?, provider=?, provider_subscription_id=?, updated_at=? WHERE id=?",
                (plan_id, provider, tx_ref, datetime.utcnow().isoformat(), existing["id"]),
            )
        else:
            execute(
                "INSERT INTO subscriptions_v2 (organization_id, plan_id, status, provider, provider_subscription_id) VALUES (?,?,'pending',?,?)",
                (org_id, plan_id, provider, tx_ref),
            )

    def _record_history(self, sub_id, org_id, event_type,
                        from_status=None, to_status=None,
                        from_plan_id=None, to_plan_id=None,
                        triggered_by="system", actor_id=None, notes=None):
        execute(
            """INSERT INTO subscription_history
               (subscription_id, organization_id, event_type,
                from_status, to_status, from_plan_id, to_plan_id,
                triggered_by, actor_user_id, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (sub_id, org_id, event_type, from_status, to_status,
             from_plan_id, to_plan_id, triggered_by, actor_id, notes),
        )

    def _days_left(self, period_end: str | None) -> int | None:
        if not period_end:
            return None
        try:
            delta = (datetime.fromisoformat(period_end) - datetime.utcnow()).days
            return max(delta, 0)
        except Exception:
            return None

    def _compute_warning(self, sub: dict) -> str | None:
        days = self._days_left(sub.get("current_period_end"))
        if sub["status"] in ("expired", "canceled"):
            return "Subscription has expired. Please renew to restore full access."
        if sub["status"] == "past_due":
            return "Payment failed. Please update your payment method."
        if days is not None and days <= 7:
            return f"Subscription expires in {days} day{'s' if days != 1 else ''}. Renew to avoid interruption."
        return None

    def _grace_active(self, sub: dict) -> bool:
        if sub["status"] not in ("expired", "canceled"):
            return False
        grace_end = sub.get("grace_period_end")
        if not grace_end:
            return False
        try:
            return datetime.utcnow() < datetime.fromisoformat(grace_end)
        except Exception:
            return False

    def _legacy_status(self, school: dict) -> dict:
        """Build status from legacy schools table for backward compatibility."""
        plan   = school.get("plan", "trial")
        status = school.get("subscription_status", "trial")
        return {
            "plan_name":     plan,
            "display_name":  plan.title(),
            "status":        status,
            "is_active":     bool(school.get("is_active", 1)),
            "current_period_end": school.get("trial_ends"),
            "days_left":     self._days_left(school.get("trial_ends")),
            "warning":       None,
            "grace_active":  False,
            "providers":     available_providers(),
            "color":         PLAN_COLORS.get(plan, "#94A3B8"),
        }

    def _no_subscription_status(self) -> dict:
        return {
            "plan_name": "none", "display_name": "No Subscription",
            "status": "inactive", "is_active": False,
            "current_period_end": None, "days_left": None,
            "warning": "No subscription found. Please activate a plan.",
            "grace_active": False, "providers": available_providers(),
            "color": "#94A3B8",
        }
