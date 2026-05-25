"""Audit log router — read-only access to the audit trail."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query
from backend.deps import require_auth
from backend.core.security import require_permission
from backend.core.audit import audit

router = APIRouter(tags=["audit"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("")
def get_audit_log(
    user:       Usr,
    table_name: str = Query(None),
    actor_id:   int = Query(None),
    action:     str = Query(None),
    limit:      int = Query(100),
):
    require_permission(user, "audit.view")
    return audit.get_recent(
        limit=limit,
        actor_id=actor_id,
        table_name=table_name,
        action=action,
    )


@router.get("/record/{table_name}/{record_id}")
def get_record_history(table_name: str, record_id: int, user: Usr):
    require_permission(user, "audit.view")
    return audit.get_history(table_name, record_id)
