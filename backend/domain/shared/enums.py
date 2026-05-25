"""Shared enums used across multiple domain modules."""
from enum import Enum


class GradeStatus(str, Enum):
    DRAFT        = "draft"
    SUBMITTED    = "submitted"
    UNDER_REVIEW = "under_review"
    RETURNED     = "returned"
    APPROVED     = "approved"
    PUBLISHED    = "published"
    LOCKED       = "locked"


class InvoiceStatus(str, Enum):
    DRAFT    = "draft"
    ISSUED   = "issued"
    PARTIAL  = "partial"
    PAID     = "paid"
    OVERDUE  = "overdue"
    VOID     = "void"


class PaymentMethod(str, Enum):
    CASH   = "cash"
    MPESA  = "mpesa"
    BANK   = "bank"
    CHEQUE = "cheque"
    WAIVER = "waiver"


class PaymentStatus(str, Enum):
    CONFIRMED = "confirmed"
    REVERSED  = "reversed"


class LeaveStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WaiverStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED  = "applied"


class ExpenseStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    VOIDED   = "voided"
