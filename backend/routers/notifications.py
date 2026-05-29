"""Notifications router — read/mark-read notification records."""

from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from backend.deps import require_auth
from backend.core.db import fetch_one, fetch_all, execute as db_execute

router = APIRouter(tags=["notifications"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("")
def get_notifications(user: Usr, unread_only: bool = Query(False), limit: int = Query(50)):
    where = "nr.user_id = ?"
    params: list = [user["id"]]
    if unread_only:
        where += " AND nr.read_at IS NULL AND nr.dismissed_at IS NULL"
    rows = fetch_all(
        f"""SELECT n.*, nr.read_at, nr.dismissed_at
            FROM notifications n
            JOIN notification_recipients nr ON nr.notification_id = n.id
            WHERE {where}
            ORDER BY n.created_at DESC
            LIMIT ?""",
        params + [limit],
    )
    return rows


@router.get("/unread-count")
def unread_count(user: Usr):
    row = fetch_one(
        """SELECT COUNT(*) AS n FROM notification_recipients
           WHERE user_id=? AND read_at IS NULL AND dismissed_at IS NULL""",
        (user["id"],),
    )
    return {"count": row["n"] if row else 0}


@router.post("/{notif_id}/read")
def mark_read(notif_id: int, user: Usr):
    db_execute(
        "UPDATE notification_recipients SET read_at=? WHERE notification_id=? AND user_id=? AND read_at IS NULL",
        (datetime.now(timezone.utc).isoformat(), notif_id, user["id"]),
    )
    return {"ok": True}


@router.post("/mark-all-read")
def mark_all_read(user: Usr):
    db_execute(
        "UPDATE notification_recipients SET read_at=? WHERE user_id=? AND read_at IS NULL",
        (datetime.now(timezone.utc).isoformat(), user["id"]),
    )
    return {"ok": True}
