"""
Paystack payment provider.

Webhook verification: HMAC-SHA512 of raw body using PAYSTACK_SECRET_KEY.
"""

import hashlib, hmac, json, logging
import httpx
from .base import PaymentProvider, CheckoutSession, ParsedWebhookEvent, WebhookSignatureError

log = logging.getLogger(__name__)

BASE_URL = "https://api.paystack.co"


class PaystackProvider(PaymentProvider):

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    # ── Initialize transaction ────────────────────────────────────────────

    async def create_checkout(
        self,
        *,
        tx_ref, amount, currency, plan_name, interval,
        org_id, org_email, org_name, redirect_url, metadata={},
    ) -> CheckoutSession:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                f"{BASE_URL}/transaction/initialize",
                headers={
                    "Authorization": f"Bearer {self.secret_key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "reference":    tx_ref,
                    "amount":       amount,  # Paystack uses kobo/cents
                    "currency":     currency,
                    "email":        org_email,
                    "callback_url": redirect_url,
                    "metadata": {
                        "org_id":     str(org_id),
                        "plan_name":  plan_name,
                        "interval":   interval,
                        "org_name":   org_name,
                        **metadata,
                    },
                },
            )
            data = res.json()

        if not data.get("status"):
            raise RuntimeError(f"Paystack error: {data.get('message', 'Unknown error')}")

        return CheckoutSession(
            session_id=   data["data"]["reference"],
            checkout_url= data["data"]["authorization_url"],
            provider=     "paystack",
            tx_ref=       tx_ref,
        )

    # ── Verify webhook signature (HMAC-SHA512) ───────────────────────────

    def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> ParsedWebhookEvent:
        received_sig = headers.get("x-paystack-signature", "")
        expected_sig = hmac.new(
            self.secret_key.encode("utf-8"),
            raw_body,
            hashlib.sha512,
        ).hexdigest()

        if not hmac.compare_digest(received_sig, expected_sig):
            raise WebhookSignatureError("Invalid Paystack webhook signature")

        try:
            payload = json.loads(raw_body)
        except Exception:
            raise WebhookSignatureError("Invalid JSON payload")

        data      = payload.get("data", {})
        meta      = data.get("metadata", {})
        org_id    = meta.get("org_id")
        plan_name = meta.get("plan_name")
        tx_ref    = data.get("reference", "")

        ps_event   = payload.get("event", "")
        event_type = {
            "charge.success":      "payment.succeeded",
            "transfer.success":    "payment.succeeded",
            "subscription.disable":"subscription.canceled",
        }.get(ps_event, ps_event)

        if ps_event == "charge.success" and data.get("status") != "success":
            event_type = "payment.failed"

        return ParsedWebhookEvent(
            provider=  "paystack",
            event_id=  data.get("id", tx_ref),
            event_type=event_type,
            payload=   payload,
            org_id=    str(org_id) if org_id else None,
            plan_name= plan_name,
            amount=    data.get("amount", 0),
            currency=  data.get("currency", "NGN"),
            tx_ref=    tx_ref,
        )

    # ── Verify transaction ────────────────────────────────────────────────

    async def verify_transaction(self, tx_ref: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{BASE_URL}/transaction/verify/{tx_ref}",
                headers={"Authorization": f"Bearer {self.secret_key}"},
            )
            data = res.json()

        if not data.get("status"):
            return {"status": "not_found"}

        txn  = data.get("data", {})
        meta = txn.get("metadata", {})
        return {
            "status":    "succeeded" if txn.get("status") == "success" else txn.get("status", "pending"),
            "amount":    txn.get("amount", 0),
            "currency":  txn.get("currency", "NGN"),
            "org_id":    meta.get("org_id"),
            "plan_name": meta.get("plan_name"),
            "tx_id":     txn.get("id"),
        }
