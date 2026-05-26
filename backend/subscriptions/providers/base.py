from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CheckoutSession:
    session_id:   str
    checkout_url: str
    provider:     str
    tx_ref:       str = ""


@dataclass
class ParsedWebhookEvent:
    provider:   str
    event_id:   str
    event_type: str
    payload:    dict
    org_id:     str | None = None
    plan_name:  str | None = None
    amount:     int = 0
    currency:   str = "TZS"
    tx_ref:     str = ""


class WebhookSignatureError(ValueError):
    pass


class PaymentProvider(ABC):

    @abstractmethod
    async def create_checkout(
        self,
        *,
        tx_ref:       str,
        amount:       int,
        currency:     str,
        plan_name:    str,
        interval:     str,
        org_id:       str,
        org_email:    str,
        org_name:     str,
        redirect_url: str,
        metadata:     dict = {},
    ) -> CheckoutSession: ...

    @abstractmethod
    def verify_webhook(
        self,
        raw_body: bytes,
        headers:  dict[str, str],
    ) -> ParsedWebhookEvent:
        """Raise WebhookSignatureError if signature is invalid."""
        ...

    @abstractmethod
    async def verify_transaction(self, tx_ref: str) -> dict:
        """Poll provider to confirm a transaction by its reference."""
        ...
