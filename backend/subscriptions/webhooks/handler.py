"""
WebhookHandler — idempotent, audit-logged, retry-safe.

Call handle() from the webhook router after signature verification.
Returns: "processed" | "already_processed" | "ignored"
Raises on unexpected errors so the HTTP caller returns 500 → provider retries.
"""

import json, logging
from datetime import datetime, timedelta
from database.db import execute, fetch_one, fetch_all
from ..providers.base import ParsedWebhookEvent

log = logging.getLogger(__name__)


class WebhookHandler:

    async def handle(self, event: ParsedWebhookEvent, raw_body: bytes, ip: str | None = None) -> str:
        # ── 1. Idempotency ──────────────────────────────────────────────
        existing = fetch_one(
            "SELECT id, status FROM webhook_events WHERE provider=? AND event_id=?",
            (event.provider, str(event.event_id)),
        )
        if existing and existing["status"] == "processed":
            log.info("Webhook %s/%s already processed — skip", event.provider, event.event_id)
            return "already_processed"

        # ── 2. Persist event ────────────────────────────────────────────
        if not existing:
            record_id = execute(
                """INSERT OR IGNORE INTO webhook_events
                   (provider, event_id, event_type, raw_payload, parsed_payload,
                    status, ip_address)
                   VALUES (?,?,?,?,?,'pending',?)""",
                (event.provider, str(event.event_id), event.event_type,
                 raw_body.decode("utf-8", "replace"),
                 json.dumps(event.payload), ip),
            )
        else:
            record_id = existing["id"]

        # ── 3. Increment attempt counter ────────────────────────────────
        execute(
            "UPDATE webhook_events SET processing_attempts=processing_attempts+1 WHERE id=?",
            (record_id,),
        )

        # ── 4. Dispatch ─────────────────────────────────────────────────
        try:
            result = await self._dispatch(event, record_id)
            execute(
                "UPDATE webhook_events SET status=?, processed_at=? WHERE id=?",
                (result, _now(), record_id),
            )
            log.info("Webhook %s/%s → %s", event.provider, event.event_id, result)
            return result

        except Exception as exc:
            execute(
                "UPDATE webhook_events SET status='failed', last_error=? WHERE id=?",
                (str(exc)[:1000], record_id),
            )
            log.exception("Webhook %s/%s failed", event.provider, event.event_id)
            raise

    # ── Dispatcher ──────────────────────────────────────────────────────

    async def _dispatch(self, event: ParsedWebhookEvent, webhook_id: str) -> str:
        if event.event_type == "payment.succeeded":
            await self._on_payment_succeeded(event, webhook_id)
            return "processed"
        elif event.event_type == "payment.failed":
            await self._on_payment_failed(event, webhook_id)
            return "processed"
        elif event.event_type == "subscription.canceled":
            await self._on_subscription_canceled(event, webhook_id)
            return "processed"
        else:
            log.info("Webhook event type '%s' not handled — ignoring", event.event_type)
            return "ignored"

    # ── Event handlers ──────────────────────────────────────────────────

    async def _on_payment_succeeded(self, event: ParsedWebhookEvent, webhook_id: str):
        org_id = event.org_id
        if not org_id:
            log.warning("payment.succeeded webhook missing org_id — cannot activate")
            return

        plan_name = event.plan_name
        if not plan_name:
            log.warning("payment.succeeded webhook missing plan_name for org %s", org_id)
            return

        # Find plan
        plan = fetch_one(
            "SELECT * FROM subscription_plans WHERE name=? ORDER BY price_amount ASC LIMIT 1",
            (plan_name,),
        )
        if not plan:
            log.error("Plan '%s' not found in subscription_plans", plan_name)
            return

        # Determine billing period
        interval = "monthly"
        try:
            meta = event.payload.get("data", {}).get("meta", {}) or \
                   event.payload.get("data", {}).get("metadata", {})
            interval = meta.get("interval", "monthly")
        except Exception:
            pass

        now        = datetime.utcnow()
        period_end = (now + timedelta(days=366) if interval == "yearly" else now + timedelta(days=31))
        grace_end  = period_end + timedelta(days=7)

        # Upsert subscription
        sub = fetch_one(
            """SELECT id, status FROM subscriptions_v2
               WHERE organization_id=? AND status NOT IN ('canceled')
               ORDER BY created_at DESC LIMIT 1""",
            (org_id,),
        )

        if sub:
            old_status = sub["status"]
            execute(
                """UPDATE subscriptions_v2
                   SET status='active', plan_id=?, provider=?,
                       provider_subscription_id=?,
                       current_period_start=?, current_period_end=?,
                       grace_period_end=?, updated_at=?
                   WHERE id=?""",
                (plan["id"], event.provider, event.tx_ref,
                 now.isoformat(), period_end.isoformat(),
                 grace_end.isoformat(), now.isoformat(), sub["id"]),
            )
            sub_id = sub["id"]
            self._record_history(sub_id, org_id, "payment_succeeded",
                                 from_status=old_status, to_status="active",
                                 to_plan_id=plan["id"], webhook_id=webhook_id)
        else:
            sub_id = execute(
                """INSERT INTO subscriptions_v2
                   (organization_id, plan_id, status, provider,
                    provider_subscription_id,
                    current_period_start, current_period_end, grace_period_end)
                   VALUES (?,?,'active',?,?,?,?,?)""",
                (org_id, plan["id"], event.provider, event.tx_ref,
                 now.isoformat(), period_end.isoformat(), grace_end.isoformat()),
            )
            self._record_history(sub_id, org_id, "activated",
                                 to_status="active", to_plan_id=plan["id"],
                                 webhook_id=webhook_id)

        # Create payment record
        execute(
            """INSERT OR IGNORE INTO payments
               (organization_id, subscription_id, provider, provider_payment_id,
                status, amount, currency, payment_method)
               VALUES (?,?,?,?,'succeeded',?,?,?)""",
            (org_id, sub_id, event.provider, event.tx_ref or str(event.event_id),
             event.amount, event.currency, "mobile_money"),
        )

        # Create invoice
        inv_num = f"INV-{now.strftime('%Y%m')}-{str(sub_id)[:6].upper()}"
        inv_id  = execute(
            """INSERT OR IGNORE INTO invoices
               (organization_id, subscription_id, provider, provider_invoice_id,
                status, amount_due, amount_paid, currency,
                billing_period_start, billing_period_end,
                due_date, paid_at, invoice_number)
               VALUES (?,?,?,?,'paid',?,?,?,?,?,?,?,?)""",
            (org_id, sub_id, event.provider, event.tx_ref or str(event.event_id),
             event.amount, event.amount, event.currency,
             now.date().isoformat(), period_end.date().isoformat(),
             now.isoformat(), now.isoformat(), inv_num),
        )

        # Sync schools table (backward compat)
        self._sync_schools_table(org_id, plan_name, "active", period_end.date().isoformat())
        log.info("Subscription activated for org %s — plan %s until %s", org_id, plan_name, period_end.date())

    async def _on_payment_failed(self, event: ParsedWebhookEvent, webhook_id: str):
        org_id = event.org_id
        if not org_id:
            return

        sub = fetch_one(
            "SELECT id, status FROM subscriptions_v2 WHERE organization_id=? AND status IN ('active','trialing','past_due') ORDER BY created_at DESC LIMIT 1",
            (org_id,),
        )
        if sub:
            execute(
                "UPDATE subscriptions_v2 SET status='past_due', updated_at=? WHERE id=?",
                (_now(), sub["id"]),
            )
            self._record_history(sub["id"], org_id, "payment_failed",
                                 from_status=sub["status"], to_status="past_due",
                                 webhook_id=webhook_id)

        # Record failed payment
        execute(
            """INSERT OR IGNORE INTO payments
               (organization_id, provider, provider_payment_id, status, amount, currency)
               VALUES (?,?,?,'failed',?,?)""",
            (org_id, event.provider, event.tx_ref or str(event.event_id),
             event.amount, event.currency),
        )

    async def _on_subscription_canceled(self, event: ParsedWebhookEvent, webhook_id: str):
        org_id = event.org_id
        if not org_id:
            return
        sub = fetch_one(
            "SELECT id FROM subscriptions_v2 WHERE organization_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
            (org_id,),
        )
        if sub:
            execute(
                "UPDATE subscriptions_v2 SET status='canceled', canceled_at=?, updated_at=? WHERE id=?",
                (_now(), _now(), sub["id"]),
            )
            self._record_history(sub["id"], org_id, "canceled",
                                 to_status="canceled", webhook_id=webhook_id)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _record_history(self, sub_id, org_id, event_type,
                        from_status=None, to_status=None,
                        from_plan_id=None, to_plan_id=None,
                        webhook_id=None, triggered_by="webhook"):
        execute(
            """INSERT INTO subscription_history
               (subscription_id, organization_id, event_type,
                from_status, to_status, from_plan_id, to_plan_id,
                triggered_by, webhook_event_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (sub_id, org_id, event_type,
             from_status, to_status, from_plan_id, to_plan_id,
             triggered_by, webhook_id),
        )

    def _sync_schools_table(self, org_id, plan_name, status, trial_ends=None):
        """Keep the legacy schools table fields in sync for backward compatibility."""
        try:
            execute(
                """UPDATE schools SET plan=?, subscription_status=?, is_active=1, trial_ends=?
                   WHERE id=?""",
                (plan_name, status, trial_ends, org_id),
            )
        except Exception as e:
            log.warning("Failed to sync schools table: %s", e)


def _now() -> str:
    return datetime.utcnow().isoformat()
