"""
Migration 019 — Full subscription management tables v2.

Adds production-ready tables:
  subscription_plans, subscriptions_v2, invoices, payments,
  webhook_events, subscription_history

Keeps existing `schools` table intact (backward-compatible).
"""

from database.db import execute, fetch_one


def run():
    # ── subscription_plans ───────────────────────────────────────────────
    execute("""
    CREATE TABLE IF NOT EXISTS subscription_plans (
        id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        name             TEXT NOT NULL,
        display_name     TEXT NOT NULL,
        billing_interval TEXT NOT NULL CHECK(billing_interval IN ('monthly','yearly')),
        price_amount     INTEGER NOT NULL,
        currency         TEXT DEFAULT 'TZS',
        max_users        INTEGER NOT NULL,
        max_students     INTEGER NOT NULL,
        features         TEXT DEFAULT '{}',
        is_active        INTEGER DEFAULT 1,
        sort_order       INTEGER DEFAULT 0,
        created_at       TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── subscriptions_v2 ─────────────────────────────────────────────────
    execute("""
    CREATE TABLE IF NOT EXISTS subscriptions_v2 (
        id                       TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        organization_id          INTEGER NOT NULL REFERENCES schools(id),
        plan_id                  TEXT NOT NULL REFERENCES subscription_plans(id),

        status                   TEXT NOT NULL DEFAULT 'pending',

        provider                 TEXT,
        provider_subscription_id TEXT,
        provider_customer_id     TEXT,

        current_period_start     TEXT,
        current_period_end       TEXT,
        trial_end                TEXT,

        cancel_at_period_end     INTEGER DEFAULT 0,
        canceled_at              TEXT,

        grace_period_days        INTEGER DEFAULT 7,
        grace_period_end         TEXT,

        pending_plan_id          TEXT REFERENCES subscription_plans(id),

        metadata                 TEXT DEFAULT '{}',
        created_at               TEXT DEFAULT (datetime('now')),
        updated_at               TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── invoices ─────────────────────────────────────────────────────────
    execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id                   TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        organization_id      INTEGER NOT NULL REFERENCES schools(id),
        subscription_id      TEXT REFERENCES subscriptions_v2(id),

        provider             TEXT,
        provider_invoice_id  TEXT UNIQUE,

        status               TEXT NOT NULL DEFAULT 'open',

        amount_due           INTEGER NOT NULL,
        amount_paid          INTEGER DEFAULT 0,
        currency             TEXT DEFAULT 'TZS',

        billing_period_start TEXT,
        billing_period_end   TEXT,
        due_date             TEXT,
        paid_at              TEXT,

        invoice_number       TEXT UNIQUE,
        invoice_pdf_url      TEXT,
        notes                TEXT,
        metadata             TEXT DEFAULT '{}',
        created_at           TEXT DEFAULT (datetime('now')),
        updated_at           TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── payments ─────────────────────────────────────────────────────────
    execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        organization_id     INTEGER NOT NULL REFERENCES schools(id),
        invoice_id          TEXT REFERENCES invoices(id),
        subscription_id     TEXT REFERENCES subscriptions_v2(id),

        provider            TEXT NOT NULL,
        provider_payment_id TEXT UNIQUE NOT NULL,

        status              TEXT NOT NULL,

        amount              INTEGER NOT NULL,
        currency            TEXT DEFAULT 'TZS',
        payment_method      TEXT,
        failure_code        TEXT,
        failure_reason      TEXT,

        metadata            TEXT DEFAULT '{}',
        created_at          TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── webhook_events ───────────────────────────────────────────────────
    execute("""
    CREATE TABLE IF NOT EXISTS webhook_events (
        id                   TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        provider             TEXT NOT NULL,
        event_id             TEXT NOT NULL,
        event_type           TEXT NOT NULL,

        raw_payload          TEXT NOT NULL,
        parsed_payload       TEXT NOT NULL,
        signature_header     TEXT,

        status               TEXT DEFAULT 'pending',

        processing_attempts  INTEGER DEFAULT 0,
        last_error           TEXT,
        processed_at         TEXT,

        ip_address           TEXT,
        created_at           TEXT DEFAULT (datetime('now')),

        UNIQUE(provider, event_id)
    )
    """)

    # ── subscription_history ─────────────────────────────────────────────
    execute("""
    CREATE TABLE IF NOT EXISTS subscription_history (
        id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        subscription_id  TEXT NOT NULL REFERENCES subscriptions_v2(id),
        organization_id  INTEGER NOT NULL REFERENCES schools(id),

        event_type       TEXT NOT NULL,

        from_status      TEXT,
        to_status        TEXT,
        from_plan_id     TEXT REFERENCES subscription_plans(id),
        to_plan_id       TEXT REFERENCES subscription_plans(id),

        triggered_by     TEXT DEFAULT 'system',
        actor_user_id    INTEGER,
        webhook_event_id TEXT REFERENCES webhook_events(id),

        notes            TEXT,
        metadata         TEXT DEFAULT '{}',
        created_at       TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── Indexes ──────────────────────────────────────────────────────────
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_sub2_org       ON subscriptions_v2(organization_id)",
        "CREATE INDEX IF NOT EXISTS idx_sub2_status    ON subscriptions_v2(status)",
        "CREATE INDEX IF NOT EXISTS idx_sub2_period    ON subscriptions_v2(current_period_end)",
        "CREATE INDEX IF NOT EXISTS idx_sub2_provider  ON subscriptions_v2(provider, provider_subscription_id)",
        "CREATE INDEX IF NOT EXISTS idx_inv_org        ON invoices(organization_id)",
        "CREATE INDEX IF NOT EXISTS idx_inv_status     ON invoices(status)",
        "CREATE INDEX IF NOT EXISTS idx_pay_org        ON payments(organization_id)",
        "CREATE INDEX IF NOT EXISTS idx_wh_status      ON webhook_events(status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_hist_sub       ON subscription_history(subscription_id)",
        "CREATE INDEX IF NOT EXISTS idx_hist_org       ON subscription_history(organization_id, created_at)",
    ]:
        try:
            execute(idx_sql)
        except Exception:
            pass

    # ── Seed plan data if empty ──────────────────────────────────────────
    import json
    existing = fetch_one("SELECT COUNT(*) as n FROM subscription_plans")
    if existing and existing["n"] == 0:
        plans = [
            ("basic",    "Basic",    "monthly", 50_000,     "TZS", 25,  300,  json.dumps({"payroll": False, "ai_chat": False, "welfare": False, "transport": False}),      1, 1),
            ("basic",    "Basic",    "yearly",  480_000,    "TZS", 25,  300,  json.dumps({"payroll": False, "ai_chat": False, "welfare": False, "transport": False}),      1, 1),
            ("standard", "Standard", "monthly", 120_000,    "TZS", 100, 1000, json.dumps({"payroll": True,  "ai_chat": False, "welfare": True,  "transport": True}),       1, 2),
            ("standard", "Standard", "yearly",  1_150_000,  "TZS", 100, 1000, json.dumps({"payroll": True,  "ai_chat": False, "welfare": True,  "transport": True}),       1, 2),
            ("premium",  "Premium",  "monthly", 250_000,    "TZS", 500, 5000, json.dumps({"payroll": True,  "ai_chat": True,  "welfare": True,  "transport": True, "all": True}), 1, 3),
            ("premium",  "Premium",  "yearly",  2_400_000,  "TZS", 500, 5000, json.dumps({"payroll": True,  "ai_chat": True,  "welfare": True,  "transport": True, "all": True}), 1, 3),
        ]
        for p in plans:
            execute(
                """INSERT OR IGNORE INTO subscription_plans
                   (name, display_name, billing_interval, price_amount, currency,
                    max_users, max_students, features, is_active, sort_order)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                p,
            )
