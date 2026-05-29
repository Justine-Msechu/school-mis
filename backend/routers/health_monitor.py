"""Platform health monitor API — superadmin only."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from backend.deps import require_auth
from backend.core.db import execute, fetch_all, fetch_one

router = APIRouter(tags=["health-monitor"])
Usr    = Annotated[dict, Depends(require_auth)]


def _super(user: dict):
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin only")


@router.get("/count")
def alert_count(user: Usr):
    """Badge counter — total active alerts and critical count."""
    _super(user)
    total = fetch_one("SELECT count(*) AS n FROM platform_health_alerts WHERE resolved=0")
    crit  = fetch_one(
        "SELECT count(*) AS n FROM platform_health_alerts WHERE resolved=0 AND level='critical'"
    )
    return {
        "total":    total["n"] if total else 0,
        "critical": crit["n"]  if crit  else 0,
    }


@router.get("/alerts")
def list_alerts(user: Usr, resolved: int = 0):
    _super(user)
    rows = fetch_all(
        "SELECT * FROM platform_health_alerts WHERE resolved=%s ORDER BY ts DESC LIMIT 100",
        (resolved,),
    )
    return {"items": rows, "total": len(rows)}


@router.get("/status")
def live_status(user: Usr):
    """Runs all checks immediately and returns a fresh snapshot."""
    _super(user)
    from backend.monitoring.health_monitor import get_live_status
    return get_live_status()


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, user: Usr):
    _super(user)
    execute(
        "UPDATE platform_health_alerts SET resolved=1, resolved_at=NOW()::text WHERE id=%s",
        (alert_id,),
    )
    return {"ok": True}


@router.delete("/alerts/resolved")
def clear_resolved_alerts(user: Usr):
    _super(user)
    execute("DELETE FROM platform_health_alerts WHERE resolved=1", ())
    return {"ok": True}
