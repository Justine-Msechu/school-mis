"""
Provider registry — initialised once at startup from env vars.
Call init_providers() in lifespan, then get_provider(name) anywhere.
"""

import os, logging
from .base import PaymentProvider

log = logging.getLogger(__name__)

_REGISTRY: dict[str, PaymentProvider] = {}


def init_providers():
    """Call once at app startup."""
    global _REGISTRY
    _REGISTRY = {}

    if os.getenv("FLW_SECRET_KEY") and os.getenv("FLW_WEBHOOK_SECRET"):
        from .flutterwave import FlutterwaveProvider
        _REGISTRY["flutterwave"] = FlutterwaveProvider(
            secret_key=     os.environ["FLW_SECRET_KEY"],
            webhook_secret= os.environ["FLW_WEBHOOK_SECRET"],
            public_key=     os.getenv("FLW_PUBLIC_KEY", ""),
        )
        log.info("Flutterwave provider registered")

    if os.getenv("PAYSTACK_SECRET_KEY"):
        from .paystack import PaystackProvider
        _REGISTRY["paystack"] = PaystackProvider(
            secret_key=os.environ["PAYSTACK_SECRET_KEY"],
        )
        log.info("Paystack provider registered")

    if not _REGISTRY:
        log.warning("No payment providers configured. Set FLW_SECRET_KEY or PAYSTACK_SECRET_KEY.")


def get_provider(name: str) -> PaymentProvider:
    if name not in _REGISTRY:
        raise ValueError(f"Payment provider '{name}' is not configured.")
    return _REGISTRY[name]


def available_providers() -> list[str]:
    return list(_REGISTRY.keys())
