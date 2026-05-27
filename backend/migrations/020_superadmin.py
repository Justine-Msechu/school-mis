"""
Migration 020 — Multi-tenancy: superadmin role + school registration columns.

- Adds email / contact_phone / admin_name columns to schools table
- Seeds a platform superadmin user (username: platform, must_change_pw=1)
  Only created if no superadmin exists yet.
"""

import bcrypt
from backend.core.db import execute, fetch_one, fetch_all


def run():
    # ── Extend schools table ───────────────────────────────────────────────────
    cols = {r["name"] for r in fetch_all("PRAGMA table_info(schools)", ())}
    for col, defn in [
        ("email",         "TEXT"),
        ("contact_phone", "TEXT"),
        ("admin_name",    "TEXT"),
    ]:
        if col not in cols:
            execute(f"ALTER TABLE schools ADD COLUMN {col} {defn}", ())

    # ── Seed platform superadmin (once only) ──────────────────────────────────
    existing = fetch_one("SELECT id FROM users WHERE role='superadmin' LIMIT 1", ())
    if not existing:
        pw_hash = bcrypt.hashpw(b"Platform@123", bcrypt.gensalt(rounds=12)).decode()
        execute(
            """INSERT INTO users
               (username, password_hash, salt, pw_scheme, full_name, role,
                is_active, must_change_pw, school_id)
               VALUES ('platform', ?, '', 'bcrypt', 'Platform Admin', 'superadmin',
                       1, 1, NULL)""",
            (pw_hash,),
        )
