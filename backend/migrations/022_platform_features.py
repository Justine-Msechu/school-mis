"""Migration 022 — Platform feature flags + announcements tables."""
from backend.core.db import execute, fetch_one, fetch_all

MODULES = [
    "grades", "attendance", "finance", "library", "accounting",
    "transport", "inventory", "health", "welfare", "promotion",
    "reports", "enrollment", "guardians", "report_cards", "payroll", "ngo",
]

PLAN_DEFAULTS = {
    "trial": {
        "grades", "attendance", "finance", "promotion",
        "reports", "enrollment", "guardians", "report_cards",
    },
    "basic": {
        "grades", "attendance", "finance", "promotion",
        "reports", "enrollment", "guardians", "report_cards",
        "library", "payroll",
    },
    "standard": {
        "grades", "attendance", "finance", "promotion",
        "reports", "enrollment", "guardians", "report_cards",
        "library", "payroll", "accounting", "transport", "inventory",
    },
    "premium": set(MODULES),
}


def run():
    # ── Feature flags table ───────────────────────────────────────────────────
    execute("""CREATE TABLE IF NOT EXISTS platform_feature_flags (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        plan    TEXT NOT NULL,
        module  TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        UNIQUE(plan, module)
    )""", ())

    for plan, enabled_set in PLAN_DEFAULTS.items():
        for module in MODULES:
            enabled = 1 if module in enabled_set else 0
            execute(
                "INSERT OR IGNORE INTO platform_feature_flags (plan, module, enabled) VALUES (?, ?, ?)",
                (plan, module, enabled),
            )

    # ── Platform announcements table ──────────────────────────────────────────
    execute("""CREATE TABLE IF NOT EXISTS platform_announcements (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        body        TEXT NOT NULL,
        priority    TEXT NOT NULL DEFAULT 'normal',
        target_plan TEXT NOT NULL DEFAULT 'all',
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        expires_at  TEXT,
        is_active   INTEGER NOT NULL DEFAULT 1
    )""", ())

    # ── suspended status: add to schools if needed (no schema change required,
    #    SQLite is schemaless for TEXT columns) ──────────────────────────────
    # Just ensure is_active=0 for suspended schools so login is blocked
    execute(
        "UPDATE schools SET is_active=0 WHERE subscription_status='suspended' AND is_active=1",
        (),
    )
