"""
Webhook receiver — one endpoint per provider.

POST /api/webhooks/flutterwave
POST /api/webhooks/paystack

Always returns 200 on success so providers don't retry.
Returns 500 on processing failure so providers DO retry.
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from ..providers.registry import get_provider
from ..providers.base import WebhookSignatureError
from .handler import WebhookHandler

router  = APIRouter(tags=["webhooks"])
handler = WebhookHandler()
log     = logging.getLogger(__name__)


@router.post("/{provider}")
async def receive_webhook(provider: str, request: Request):
    # ── 1. Raw body (must be read before any parsing) ────────────────────
    raw_body = await request.body()
    headers  = {k.lower(): v for k, v in request.headers.items()}
    client_ip = request.client.host if request.client else None

    # ── 2. Get configured provider ───────────────────────────────────────
    try:
        prov = get_provider(provider)
    except ValueError:
        log.warning("Webhook received for unknown provider: %s", provider)
        raise HTTPException(400, f"Provider '{provider}' is not configured.")

    # ── 3. Verify signature — reject immediately if invalid ──────────────
    try:
        event = prov.verify_webhook(raw_body, headers)
    except WebhookSignatureError as exc:
        log.warning("Webhook signature failed [%s]: %s", provider, exc)
        raise HTTPException(400, "Invalid webhook signature.")

    # ── 4. Dispatch (idempotent, fully logged) ───────────────────────────
    try:
        result = await handler.handle(event, raw_body, ip=client_ip)
        return {"received": True, "result": result}

    except Exception as exc:
        log.exception("Webhook processing error [%s/%s]", provider, event.event_id)
        # Return 500 so provider will retry (important for payment.succeeded)
        raise HTTPException(500, "Processing failed — will retry.")
