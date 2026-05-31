"""
Migration 028 — PostgreSQL compatibility fixes.

Re-applies schema changes from migrations 012–017 that silently failed
on PostgreSQL because they used conn.execute() (psycopg2 cursor-based API).

Idempotent: uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS throughout.
"""
from backend.core.db import execute, fetch_all
import logging

log = logging.getLogger(__name__)


def _cols(table: str) -> set:
    rows = fetch_all("PRAGMA table_info(" + table + ")", ())
    return {r["name"] for r in rows}


def run():
    # ── inventory_items: rename category → main_category, add new columns ──────
    try:
        cols = _cols("inventory_items")
        if "category" in cols and "main_category" not in cols:
            execute("ALTER TABLE inventory_items RENAME COLUMN category TO main_category", ())
        for ddl in [
            "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS main_category TEXT",
            "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS subcategory  TEXT",
            "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS item_type    TEXT NOT NULL DEFAULT 'consumable'",
            "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS location     TEXT",
            "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS status       TEXT NOT NULL DEFAULT 'available'",
            "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS supplier     TEXT",
        ]:
            try:
                execute(ddl, ())
            except Exception:
                pass
    except Exception as e:
        log.warning("028 inventory_items: %s", e)

    # ── inventory_transactions: add new columns ──────────────────────────────────
    for ddl in [
        "ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS supplier    TEXT",
        "ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS unit_cost   DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS issued_to   TEXT",
        "ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS department  TEXT",
        "ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS request_id  INTEGER",
    ]:
        try:
            execute(ddl, ())
        except Exception as e:
            log.warning("028 inventory_transactions col: %s", e)

    # ── inventory_requests ───────────────────────────────────────────────────────
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS inventory_requests (
                id           SERIAL PRIMARY KEY,
                item_id      INTEGER NOT NULL REFERENCES inventory_items(id),
                requested_by INTEGER NOT NULL REFERENCES users(id),
                quantity     INTEGER NOT NULL,
                purpose      TEXT,
                department   TEXT,
                status       TEXT NOT NULL DEFAULT 'pending',
                notes        TEXT,
                reviewed_by  INTEGER REFERENCES users(id),
                reviewed_at  TEXT,
                created_at   TEXT DEFAULT NOW()::text
            )
        """, ())
    except Exception as e:
        log.warning("028 inventory_requests: %s", e)

    # ── ngos ─────────────────────────────────────────────────────────────────────
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS ngos (
                id             SERIAL PRIMARY KEY,
                name           TEXT NOT NULL UNIQUE,
                contact_person TEXT,
                phone          TEXT,
                email          TEXT,
                address        TEXT,
                website        TEXT,
                notes          TEXT,
                is_active      INTEGER DEFAULT 1,
                created_at     TEXT DEFAULT NOW()::text
            )
        """, ())
    except Exception as e:
        log.warning("028 ngos: %s", e)

    # ── student_sponsorships ──────────────────────────────────────────────────────
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS student_sponsorships (
                id            SERIAL PRIMARY KEY,
                student_id    INTEGER NOT NULL REFERENCES students(id),
                ngo_id        INTEGER NOT NULL REFERENCES ngos(id),
                support_types TEXT DEFAULT '',
                fee_amount    DOUBLE PRECISION DEFAULT 0,
                start_date    TEXT,
                end_date      TEXT,
                notes         TEXT,
                is_active     INTEGER DEFAULT 1,
                created_at    TEXT DEFAULT NOW()::text,
                UNIQUE(student_id, ngo_id)
            )
        """, ())
    except Exception as e:
        log.warning("028 student_sponsorships: %s", e)

    # ── students: sponsorship columns ────────────────────────────────────────────
    for ddl in [
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS student_type           TEXT DEFAULT 'Day'",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS sponsorship_type       TEXT DEFAULT 'none'",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS sponsor_ngo_id         INTEGER",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS sponsor_name           TEXT",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS sponsor_phone          TEXT",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS sponsor_relationship   TEXT",
    ]:
        try:
            execute(ddl, ())
        except Exception as e:
            log.warning("028 students col: %s", e)

    # ── welfare_cases: additional columns from migration 017 ─────────────────────
    for ddl in [
        "ALTER TABLE welfare_cases ADD COLUMN IF NOT EXISTS risk_level    TEXT DEFAULT 'low'",
        "ALTER TABLE welfare_cases ADD COLUMN IF NOT EXISTS support_plan  TEXT",
        "ALTER TABLE welfare_cases ADD COLUMN IF NOT EXISTS follow_up_date TEXT",
    ]:
        try:
            execute(ddl, ())
        except Exception as e:
            log.warning("028 welfare_cases col: %s", e)

    # ── permissions: inventory and ngo (idempotent) ──────────────────────────────
    perms = [
        ("inventory.view",    "inventory", "view",    "View inventory items and stock levels",         "GLOBAL"),
        ("inventory.manage",  "inventory", "manage",  "Add/edit items and receive stock deliveries",   "GLOBAL"),
        ("inventory.issue",   "inventory", "issue",   "Issue items directly and manage requests",      "GLOBAL"),
        ("inventory.request", "inventory", "request", "Submit item requests to the storekeeper",       "GLOBAL"),
        ("ngo.view",          "ngo",       "view",    "View NGO partners and beneficiary lists",       "GLOBAL"),
        ("ngo.manage",        "ngo",       "manage",  "Create and edit NGO partners and sponsorships", "GLOBAL"),
    ]
    for code, domain, action, desc, scope in perms:
        try:
            execute(
                "INSERT INTO permissions (code, domain, action, description, scope_type) VALUES (?,?,?,?,?) "
                "ON CONFLICT (code) DO NOTHING",
                (code, domain, action, desc, scope),
            )
        except Exception as e:
            log.warning("028 perm %s: %s", code, e)

    log.info("Migration 028 (pg_compat) complete")
