"""
Platform health monitor — runs as a background asyncio task.

Checks every 60 seconds:
  1. db_connections   — PG active connections vs max_connections
  2. error_spike      — unresolved errors in the last 5 minutes
  3. expired_schools  — schools with expired subscriptions

Each check fires, updates, or auto-resolves a row in platform_health_alerts.
Only one unresolved alert per metric exists at any time — no flooding.
"""

import asyncio
import logging

from backend.core.db import execute, fetch_one

log = logging.getLogger(__name__)

# ── thresholds ────────────────────────────────────────────────────────────────
DB_WARN_PCT  = 70
DB_CRIT_PCT  = 85
ERR_WARN     = 10   # errors in 5-min window
ERR_CRIT     = 25
EXP_WARN     = 1    # any expired school triggers a warning


# ── alert persistence helpers ─────────────────────────────────────────────────

def _upsert_alert(metric: str, level: str, value: float, threshold: float, message: str):
    """
    Create a new alert OR update the existing open one for this metric.
    If the level escalates/de-escalates, close the old alert and open a new one.
    """
    existing = fetch_one(
        "SELECT id, level FROM platform_health_alerts WHERE metric=%s AND resolved=0 ORDER BY id DESC LIMIT 1",
        (metric,),
    )
    if existing:
        if existing["level"] == level:
            # Same severity — just refresh value + message so the timestamp stays live
            execute(
                "UPDATE platform_health_alerts SET value=%s, message=%s, ts=NOW()::text WHERE id=%s",
                (float(value), message, existing["id"]),
            )
            return
        # Level changed — auto-close old, fall through to insert new
        execute(
            "UPDATE platform_health_alerts SET resolved=1, auto_resolved=1, resolved_at=NOW()::text WHERE id=%s",
            (existing["id"],),
        )
    execute(
        """INSERT INTO platform_health_alerts (metric, level, value, threshold, message)
           VALUES (%s,%s,%s,%s,%s)""",
        (metric, level, float(value), float(threshold), message),
    )


def _auto_resolve(metric: str):
    execute(
        """UPDATE platform_health_alerts
           SET resolved=1, auto_resolved=1, resolved_at=NOW()::text
           WHERE metric=%s AND resolved=0""",
        (metric,),
    )


# ── individual checks ─────────────────────────────────────────────────────────

def check_db_connections():
    active = fetch_one(
        "SELECT count(*) AS n FROM pg_stat_activity "
        "WHERE datname=current_database() AND state!='idle'"
    )
    mx = fetch_one("SELECT setting::int AS n FROM pg_settings WHERE name='max_connections'")
    if not active or not mx:
        return

    current  = active["n"]
    max_conn = mx["n"] or 100
    pct      = current / max_conn * 100

    if pct >= DB_CRIT_PCT:
        _upsert_alert(
            "db_connections", "critical", pct, DB_CRIT_PCT,
            f"DB connections critical: {current}/{max_conn} ({pct:.0f}%). "
            f"Install PgBouncer immediately to prevent outages.",
        )
    elif pct >= DB_WARN_PCT:
        _upsert_alert(
            "db_connections", "warning", pct, DB_WARN_PCT,
            f"DB connections high: {current}/{max_conn} ({pct:.0f}%). "
            f"Consider installing PgBouncer before load increases.",
        )
    else:
        _auto_resolve("db_connections")


def check_error_spike():
    row = fetch_one(
        "SELECT count(*) AS n FROM error_logs "
        "WHERE ts::timestamp > NOW() - interval '5 minutes' AND resolved=0"
    )
    if not row:
        return
    count = row["n"]

    if count >= ERR_CRIT:
        _upsert_alert(
            "error_spike", "critical", count, ERR_CRIT,
            f"{count} unresolved errors in the last 5 minutes. "
            f"Check the Error Logs page immediately.",
        )
    elif count >= ERR_WARN:
        _upsert_alert(
            "error_spike", "warning", count, ERR_WARN,
            f"{count} errors in the last 5 minutes. Check the Error Logs page.",
        )
    else:
        _auto_resolve("error_spike")


def check_expired_schools():
    row = fetch_one("SELECT count(*) AS n FROM schools WHERE subscription_status='expired'")
    if not row:
        return
    count = row["n"]

    if count >= EXP_WARN:
        s = "s" if count > 1 else ""
        _upsert_alert(
            "expired_schools", "warning", count, EXP_WARN,
            f"{count} school{s} with expired subscription{s}. "
            f"Reach out to renew or they will lose access.",
        )
    else:
        _auto_resolve("expired_schools")


# ── public API ────────────────────────────────────────────────────────────────

def run_all_checks():
    for fn in (check_db_connections, check_error_spike, check_expired_schools):
        try:
            fn()
        except Exception as exc:
            log.warning("Health check %s failed: %s", fn.__name__, exc)


def get_live_status() -> dict:
    """Snapshot of current metrics — runs checks first so the data is fresh."""
    run_all_checks()

    conn  = fetch_one("SELECT count(*) AS n FROM pg_stat_activity WHERE datname=current_database() AND state!='idle'")
    mx    = fetch_one("SELECT setting::int AS n FROM pg_settings WHERE name='max_connections'")
    errs  = fetch_one("SELECT count(*) AS n FROM error_logs WHERE ts::timestamp > NOW() - interval '5 minutes' AND resolved=0")
    exps  = fetch_one("SELECT count(*) AS n FROM schools WHERE subscription_status='expired'")

    current  = conn["n"] if conn else 0
    max_conn = mx["n"]   if mx   else 100
    pct      = round(current / max(max_conn, 1) * 100, 1)

    return {
        "db": {
            "connections": current,
            "max":         max_conn,
            "pct":         pct,
            "status":      "critical" if pct >= DB_CRIT_PCT else "warning" if pct >= DB_WARN_PCT else "ok",
        },
        "errors_5min":     errs["n"] if errs else 0,
        "expired_schools": exps["n"] if exps else 0,
    }


async def monitor_loop():
    """Infinite loop — start once from FastAPI lifespan."""
    log.info("Health monitor started (interval=60s)")
    while True:
        await asyncio.sleep(60)
        try:
            await asyncio.to_thread(run_all_checks)
        except Exception as exc:
            log.warning("Health monitor iteration error: %s", exc)
