"""
Flutterwave payment provider.

Tanzania mobile money: M-Pesa, Tigo Pesa, Airtel, Halo Pesa.
Card payments and bank transfers also supported.

Webhook verification: compare X-Verif-Hash header against FLUTTERWAVE_WEBHOOK_SECRET.
"""

import hashlib, hmac, json, time, logging
import httpx
from .base import PaymentProvider, CheckoutSession, ParsedWebhookEvent, WebhookSignatureError

log = logging.getLogger(__name__)

BASE_URL = "https://api.flutterwave.com/v3"


class FlutterwaveProvider(PaymentProvider):

    def __init__(self, secret_key: str, webhook_secret: str, public_key: str = ""):
        self.secret_key     = secret_key
        self.webhook_secret = webhook_secret
        self.public_key     = public_key

    # ── Create payment link ───────────────────────────────────────────────

    async def create_checkout(
        self,
        *,
        tx_ref, amount, currency, plan_name, interval,
        org_id, org_email, org_name, redirect_url, metadata={},
    ) -> CheckoutSession:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                f"{BASE_URL}/payments",
                headers={
                    "Authorization": f"Bearer {self.secret_key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "tx_ref":       tx_ref,
                    "amount":       amount / 100,  # Flutterwave uses full TZS, not cents
                    "currency":     currency,
                    "redirect_url": redirect_url,
                    "payment_options": "mobilemoneytz,card,banktransfer",
                    "customer": {
                        "email": org_email,
                        "name":  org_name,
                    },
                    "customizations": {
                        "title":       "School MIS Subscription",
                        "description": f"{plan_name.title()} Plan — {interval}",
                        "logo":        "",
                    },
                    "meta": {
                        "org_id":    str(org_id),
                        "plan_name": plan_name,
                        "interval":  interval,
                        **metadata,
                    },
                },
            )
            data = res.json()

        if data.get("status") != "success":
            raise RuntimeError(f"Flutterwave error: {data.get('message', 'Unknown error')}")

        link = data["data"]["link"]
        return CheckoutSession(
            session_id=   data["data"].get("id", tx_ref),
            checkout_url= link,
            provider=     "flutterwave",
            tx_ref=       tx_ref,
        )

    # ── Verify webhook signature ──────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> ParsedWebhookEvent:
        received = headers.get("verif-hash") or headers.get("x-verif-hash") or ""
        if not received or received != self.webhook_secret:
            raise WebhookSignatureError("Invalid Flutterwave webhook hash")

        try:
            payload = json.loads(raw_body)
        except Exception:
            raise WebhookSignatureError("Invalid JSON payload")

        data    = payload.get("data", {})
        meta    = data.get("meta", {})
        org_id  = meta.get("org_id")
        plan_name = meta.get("plan_name")
        tx_ref  = data.get("tx_ref", "")

        # Map Flutterwave event types to our internal event types
        flw_event = payload.get("event", "")
        event_type = {
            "charge.completed": "payment.succeeded",
        }.get(flw_event, flw_event)

        # Only treat as success if status is "successful"
        if flw_event == "charge.completed" and data.get("status") != "successful":
            event_type = "payment.failed"

        return ParsedWebhookEvent(
            provider=   "flutterwave",
            event_id=   str(data.get("id", tx_ref)),
            event_type= event_type,
            payload=    payload,
            org_id=     str(org_id) if org_id else None,
            plan_name=  plan_name,
            amount=     int(float(data.get("amount", 0)) * 100),  # convert to minor units
            currency=   data.get("currency", "TZS"),
            tx_ref=     tx_ref,
        )

    # ── Verify transaction by reference ──────────────────────────────────

    async def verify_transaction(self, tx_ref: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{BASE_URL}/transactions",
                headers={"Authorization": f"Bearer {self.secret_key}"},
                params={"tx_ref": tx_ref},
            )
            data = res.json()

        txns = data.get("data", [])
        if not txns:
            return {"status": "not_found"}

        txn = txns[0]
        return {
            "status":   "succeeded" if txn.get("status") == "successful" else txn.get("status", "pending"),
            "amount":   int(float(txn.get("amount", 0)) * 100),
            "currency": txn.get("currency", "TZS"),
            "org_id":   (txn.get("meta") or {}).get("org_id"),
            "plan_name":(txn.get("meta") or {}).get("plan_name"),
            "tx_id":    txn.get("id"),
        }
