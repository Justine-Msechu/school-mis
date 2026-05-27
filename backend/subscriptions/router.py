from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from .service import SubscriptionService
from .providers.registry import available_providers

router = APIRouter(tags=["subscriptions"])
Usr    = Annotated[dict, Depends(require_auth)]
svc    = SubscriptionService()


# ── Request models ────────────────────────────────────────────────────────────

class CreateCheckoutRequest(BaseModel):
    plan_name:    str
    interval:     str = "monthly"
    provider:     str
    redirect_url: str

class ManualActivateRequest(BaseModel):
    plan_name: str
    interval:  str = "monthly"
    days:      int | None = None

class CancelRequest(BaseModel):
    reason: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans():
    """All available plans with pricing. Public."""
    return svc.get_all_plans()

@router.get("/providers")
def list_providers():
    """Available configured payment providers."""
    return {"providers": available_providers()}

@router.get("/status")
def subscription_status(user: Usr):
    org_id = user.get("school_id") or _default_org_id()
    return svc.get_subscription_status(org_id)

@router.get("/history")
def subscription_history(user: Usr):
    org_id = user.get("school_id") or _default_org_id()
    return svc.get_subscription_history(org_id)

@router.post("/create-checkout")
async def create_checkout(body: CreateCheckoutRequest, user: Usr):
    if user.get("role") != "admin":
        raise HTTPException(403, "Only admins can manage subscriptions")
    if body.provider not in available_providers():
        raise HTTPException(400, f"Provider '{body.provider}' is not configured on this server.")
    if body.interval not in ("monthly", "yearly"):
        raise HTTPException(400, "interval must be 'monthly' or 'yearly'")

    school = _get_school(user)
    try:
        session = await svc.create_checkout_session(
            org_id=       user["school_id"],
            org_email=    school.get("email") or user.get("email", ""),
            org_name=     school.get("name", "School"),
            plan_name=    body.plan_name,
            interval=     body.interval,
            provider=     body.provider,
            redirect_url= body.redirect_url,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Payment gateway error: {e}")

    return {
        "checkout_url": session.checkout_url,
        "session_id":   session.session_id,
        "tx_ref":       session.tx_ref,
        "provider":     session.provider,
    }

@router.post("/verify")
async def verify_payment(tx_ref: str, user: Usr):
    """
    Call after returning from checkout page.
    Verifies payment status before the webhook arrives.
    """
    result = await svc.verify_and_activate(tx_ref, user["school_id"])
    return result

@router.post("/activate")
def manual_activate(body: ManualActivateRequest, user: Usr):
    """
    Admin manual activation — for testing or offline payments.
    In production, use this for bank transfer payments after manual verification.
    """
    if user.get("role") != "admin":
        raise HTTPException(403, "Only admins can activate subscriptions")
    org_id = user.get("school_id") or _default_org_id()
    if not org_id:
        raise HTTPException(400, "No school configured for this account")
    try:
        return svc.manual_activate(
            org_id=   org_id,
            plan_name=body.plan_name,
            interval= body.interval,
            actor_id= user["id"],
            days=     body.days,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/cancel")
def cancel_subscription(body: CancelRequest, user: Usr):
    if user.get("role") != "admin":
        raise HTTPException(403, "Only admins can cancel subscriptions")
    try:
        return svc.cancel_subscription(
            org_id=   user["school_id"],
            actor_id= user["id"],
            reason=   body.reason,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/invoices")
def invoice_history(user: Usr, page: int = 1):
    return svc.get_invoices(user["school_id"], page=page)


def _get_school(user: dict) -> dict:
    from database.db import fetch_one
    org_id = user.get("school_id") or _default_org_id()
    row = fetch_one("SELECT * FROM schools WHERE id=?", (org_id,))
    return dict(row) if row else {}


def _default_org_id() -> int | None:
    from database.db import fetch_one
    row = fetch_one("SELECT id FROM schools ORDER BY id LIMIT 1", ())
    return row["id"] if row else None
