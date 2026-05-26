"""
Cryptographically secure control number generation for school fee invoices.

Format: SCH-YYYY-XXXXXXXXXXXXXXXXXX-CCCCCC
  - SCH        school prefix (3 chars)
  - YYYY       year (4 chars)
  - XXXXXXXXXXXXXXXXXX  18 hex chars = 9 random bytes = 72 bits entropy
  - CCCCCC     6-char HMAC-SHA256 check (prevents forgery / guessing)

Total: ~33 chars. Each control number is cryptographically tied to a specific
invoice ID via the HMAC, so a number issued for invoice 5 is invalid for
invoice 6 even if the random bytes are the same.
"""
import secrets
import hmac as _hmac
import hashlib
import os
import datetime

_PREFIX = "SCH"
_HMAC_KEY = os.environ.get(
    "FINANCE_HMAC_KEY",
    "school-mis-default-key-CHANGE-in-production",
).encode()


def generate_control_number(invoice_id: int, year: int | None = None) -> str:
    """Generate a tamper-evident control number tied to invoice_id."""
    yr = year if year else datetime.date.today().year
    random_part = secrets.token_hex(9).upper()          # 18 hex chars, 72-bit entropy
    payload = f"{_PREFIX}{yr}{invoice_id:08d}{random_part}".encode()
    mac = _hmac.new(_HMAC_KEY, payload, hashlib.sha256).hexdigest()[:6].upper()
    return f"{_PREFIX}-{yr}-{random_part}-{mac}"


def verify_control_number(control_number: str, invoice_id: int) -> bool:
    """Return True only if the control number was issued by this system for invoice_id."""
    try:
        parts = control_number.split("-")
        if len(parts) != 4 or parts[0] != _PREFIX:
            return False
        prefix, yr_str, random_part, mac = parts
        yr = int(yr_str)
        payload = f"{prefix}{yr}{invoice_id:08d}{random_part}".encode()
        expected = _hmac.new(_HMAC_KEY, payload, hashlib.sha256).hexdigest()[:6].upper()
        return _hmac.compare_digest(mac, expected)
    except Exception:
        return False
