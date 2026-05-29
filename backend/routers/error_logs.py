"""
Centralised error log — backend middleware + frontend report endpoint.

Backend errors are captured by the exception middleware in main.py.
Frontend errors are POSTed here by the ErrorBoundary / global handler.
Superadmin can view and resolve errors via GET endpoints.
"""

import json, traceback, logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.deps import require_auth
from backend.core.db import execute, fetch_all, fetch_one

router = APIRouter(tags=["error-logs"])
log    = logging.getLogger(__name__)

Usr = Annotated[dict, Depends(require_auth)]


# ── Models ────────────────────────────────────────────────────────────────────

class FrontendErrorReport(BaseModel):
    message:    str
    stack:      str | None = None
    path:       str | None = None
    error_type: str | None = None
    context:    dict | None = None
    request_id: str | None = None


# ── Internal helper — called from middleware ──────────────────────────────────

def log_backend_error(
    *,
    request:    Request | None = None,
    exc:        Exception,
    user:       dict | None = None,
):
    try:
        path       = str(request.url.path) if request else None
        method     = request.method         if request else None
        request_id = getattr(request.state, "request_id", None) if request else None
        tb         = traceback.format_exc()
        execute(
            """INSERT INTO error_logs
               (source, level, path, method, user_id, school_id, role,
                error_type, message, stack, request_id)
               VALUES ('backend','error',%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                path, method,
                user.get("id")        if user else None,
                user.get("school_id") if user else None,
                user.get("role")      if user else None,
                type(exc).__name__,
                str(exc)[:2000],
                tb[:8000],
                request_id,
            ),
        )
    except Exception as inner:
        log.warning("Could not write to error_logs: %s", inner)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/report", status_code=204)
def report_frontend_error(body: FrontendErrorReport, request: Request, user: Usr):
    """Frontend ErrorBoundary / global handler POSTs here."""
    try:
        execute(
            """INSERT INTO error_logs
               (source, level, path, user_id, school_id, role,
                error_type, message, stack, context, request_id)
               VALUES ('frontend','error',%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                body.path,
                user.get("id"),
                user.get("school_id"),
                user.get("role"),
                body.error_type,
                body.message[:2000],
                (body.stack or "")[:8000],
                json.dumps(body.context or {}),
                body.request_id,
            ),
        )
    except Exception as e:
        log.warning("Failed to store frontend error: %s", e)


@router.get("")
def list_errors(
    user:     Usr,
    source:   str | None = None,
    resolved: int        = 0,
    limit:    int        = 100,
    offset:   int        = 0,
):
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin only")

    where = ["resolved = %s"]
    params: list = [resolved]

    if source:
        where.append("source = %s")
        params.append(source)

    params += [limit, offset]
    rows = fetch_all(
        f"""SELECT id, ts, source, level, path, method, user_id, school_id,
                   role, error_type, message, resolved, resolved_at
            FROM error_logs
            WHERE {' AND '.join(where)}
            ORDER BY ts DESC
            LIMIT %s OFFSET %s""",
        params,
    )
    total_row = fetch_one(
        f"SELECT COUNT(*) AS n FROM error_logs WHERE {' AND '.join(where[:len(where)])}",
        params[:-2],
    )
    return {"total": total_row["n"] if total_row else 0, "items": rows}


@router.get("/{error_id}")
def get_error(error_id: int, user: Usr):
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin only")
    row = fetch_one("SELECT * FROM error_logs WHERE id = %s", (error_id,))
    if not row:
        raise HTTPException(404, "Not found")
    return row


@router.post("/{error_id}/resolve")
def resolve_error(error_id: int, user: Usr):
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin only")
    execute(
        "UPDATE error_logs SET resolved=1, resolved_at=%s, resolved_by=%s WHERE id=%s",
        (datetime.utcnow().isoformat(), user["id"], error_id),
    )
    return {"ok": True}


@router.delete("/resolved")
def clear_resolved(user: Usr):
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin only")
    execute("DELETE FROM error_logs WHERE resolved=1", ())
    return {"ok": True}
