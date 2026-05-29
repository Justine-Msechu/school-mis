"""
AuditService — writes every significant state change to audit_log.

Every service method that mutates data should call audit.log() after the write.
The audit_log table already exists in the DB (from the PyQt6 layer).
This service extends it with structured before/after snapshots.

Usage:
    audit.log("grades", result_id, "APPROVE", actor, before=old_dict, after=new_dict)
    audit.log("payments", payment_id, "INSERT", actor, after=payment_dict)
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


class AuditService:

    def log(
        self,
        table_name: str,
        record_id: int | None,
        action: str,
        actor: dict,
        before: dict | Any = None,
        after: dict | Any = None,
        detail: str = "",
    ) -> None:
        try:
            from backend.core.db import execute as db_execute
            db_execute(
                """INSERT INTO audit_log
                       (user_id, action, table_name, record_id, detail, ts, before_state, after_state)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    actor.get("id") if isinstance(actor, dict) else actor,
                    action,
                    table_name,
                    record_id,
                    detail,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(before) if before is not None else None,
                    json.dumps(after) if after is not None else None,
                ),
            )
        except Exception:
            log.exception(
                "AuditService.log failed — table=%s action=%s record=%s",
                table_name, action, record_id,
            )

    def get_history(
        self,
        table_name: str,
        record_id: int,
        limit: int = 50,
    ) -> list[dict]:
        from backend.core.db import fetch_all
        return fetch_all(
            """SELECT al.*, u.username, u.full_name
               FROM audit_log al
               LEFT JOIN users u ON u.id = al.user_id
               WHERE al.table_name = ? AND al.record_id = ?
               ORDER BY al.ts DESC
               LIMIT ?""",
            (table_name, record_id, limit),
        )

    def get_recent(
        self,
        limit: int = 100,
        actor_id: int | None = None,
        table_name: str | None = None,
        action: str | None = None,
    ) -> list[dict]:
        from backend.core.db import fetch_all
        where: list[str] = ["1=1"]
        params: list = []
        if actor_id:
            where.append("al.user_id = ?")
            params.append(actor_id)
        if table_name:
            where.append("al.table_name = ?")
            params.append(table_name)
        if action:
            where.append("al.action = ?")
            params.append(action)
        params.append(limit)
        return fetch_all(
            f"""SELECT al.*, u.username, u.full_name, u.role
                FROM audit_log al
                LEFT JOIN users u ON u.id = al.user_id
                WHERE {' AND '.join(where)}
                ORDER BY al.ts DESC
                LIMIT ?""",
            params,
        )


# Singleton instance
audit = AuditService()
