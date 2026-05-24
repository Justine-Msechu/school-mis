from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.inventory_service import inventory_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all, fetch_one

router = APIRouter(tags=["inventory"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/items")
def list_items(user: Usr, search: str = Query("")):
    hydrate_session(user)
    where = ""
    params: list = []
    if search:
        where = "WHERE name LIKE ? OR category LIKE ?"
        params = [f"%{search}%", f"%{search}%"]
    rows = fetch_all(f"SELECT * FROM inventory_items {where} ORDER BY name", params)
    return [dict(r) for r in rows]


@router.get("/low-stock")
def low_stock(user: Usr):
    hydrate_session(user)
    try:
        return [dict(r) for r in inventory_service.get_low_stock_items()]
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class ItemPayload(BaseModel):
    name:          str
    category:      str = ""
    unit:          str = "pcs"
    quantity:      int = 0
    reorder_level: int = 5
    unit_price:    float = 0


@router.post("/items")
def create_item(body: ItemPayload, user: Usr):
    hydrate_session(user)
    try:
        item_id = inventory_service.create_item(
            body.name, body.category, body.unit,
            body.quantity, body.reorder_level, body.unit_price
        )
        return dict(fetch_one("SELECT * FROM inventory_items WHERE id=?", (item_id,)))
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class StockBody(BaseModel):
    item_id:   int
    qty:       int
    reference: str = ""


@router.post("/add-stock")
def add_stock(body: StockBody, user: Usr):
    hydrate_session(user)
    try:
        inventory_service.add_stock(body.item_id, body.qty, body.reference)
        return {"ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


class IssueBody(BaseModel):
    item_id:    int
    qty:        int
    student_id: int | None = None
    purpose:    str = ""


@router.post("/issue")
def issue_item(body: IssueBody, user: Usr):
    hydrate_session(user)
    try:
        inventory_service.issue_item(body.item_id, body.qty, body.student_id, body.purpose)
        return {"ok": True}
    except (ServiceError, PolicyViolation) as e:
        raise HTTPException(400, str(e))


@router.get("/transactions")
def get_transactions(user: Usr, item_id: int = Query(None), limit: int = Query(50)):
    where = "WHERE 1=1"
    params: list = []
    if item_id:
        where += " AND it.item_id=?"
        params.append(item_id)
    rows = fetch_all(
        f"""SELECT it.*, i.name as item_name
            FROM inventory_transactions it
            JOIN inventory_items i ON i.id=it.item_id
            {where} ORDER BY it.created_at DESC LIMIT ?""",
        params + [limit],
    )
    return [dict(r) for r in rows]
