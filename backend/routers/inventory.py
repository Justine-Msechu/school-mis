from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["inventory"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/items")
def list_items(user: Usr, search: str = Query("")):
    where = ""
    params: list = []
    if search:
        where = "WHERE (name LIKE ? OR category LIKE ?)"
        params = [f"%{search}%", f"%{search}%"]
    rows = fetch_all(f"SELECT * FROM inventory_items {where} ORDER BY name", params)
    return [dict(r) for r in rows]


@router.get("/low-stock")
def low_stock(user: Usr):
    rows = fetch_all(
        "SELECT * FROM inventory_items WHERE stock_qty <= reorder_qty AND is_active=1 ORDER BY name"
    )
    return [dict(r) for r in rows]


class ItemPayload(BaseModel):
    name:          str
    category:      str = ""
    unit:          str = "pcs"
    stock_qty:     int = 0
    reorder_qty:   int = 5
    unit_price:    float = 0


@router.post("/items")
def create_item(body: ItemPayload, user: Usr):
    existing = fetch_one("SELECT id FROM inventory_items WHERE name=? AND is_active=1", (body.name,))
    if existing:
        raise HTTPException(400, f"Item '{body.name}' already exists")
    item_id = execute(
        "INSERT INTO inventory_items (name, category, unit, stock_qty, reorder_qty, unit_price, is_active) VALUES (?,?,?,?,?,?,1)",
        (body.name, body.category or None, body.unit, body.stock_qty, body.reorder_qty, body.unit_price),
    )
    return dict(fetch_one("SELECT * FROM inventory_items WHERE id=?", (item_id,)))


@router.put("/items/{item_id}")
def update_item(item_id: int, body: ItemPayload, user: Usr):
    row = fetch_one("SELECT id FROM inventory_items WHERE id=?", (item_id,))
    if not row:
        raise HTTPException(404, "Item not found")
    execute(
        "UPDATE inventory_items SET name=?, category=?, unit=?, reorder_qty=?, unit_price=? WHERE id=?",
        (body.name, body.category or None, body.unit, body.reorder_qty, body.unit_price, item_id),
    )
    return dict(fetch_one("SELECT * FROM inventory_items WHERE id=?", (item_id,)))


class StockBody(BaseModel):
    item_id:   int
    qty:       int
    reference: str = ""
    notes:     str = ""


@router.post("/add-stock")
def add_stock(body: StockBody, user: Usr):
    item = fetch_one("SELECT * FROM inventory_items WHERE id=? AND is_active=1", (body.item_id,))
    if not item:
        raise HTTPException(404, "Item not found")
    if body.qty <= 0:
        raise HTTPException(400, "Quantity must be positive")
    execute(
        "UPDATE inventory_items SET stock_qty = stock_qty + ? WHERE id=?",
        (body.qty, body.item_id),
    )
    execute(
        """INSERT INTO inventory_transactions (item_id, type, qty, reference, notes, recorded_by)
           VALUES (?, 'stock_in', ?, ?, ?, ?)""",
        (body.item_id, body.qty, body.reference or None, body.notes or None, user.get("id")),
    )
    return dict(fetch_one("SELECT * FROM inventory_items WHERE id=?", (body.item_id,)))


class IssueBody(BaseModel):
    item_id:    int
    qty:        int
    student_id: int | None = None
    purpose:    str = ""


@router.post("/issue")
def issue_item(body: IssueBody, user: Usr):
    item = fetch_one("SELECT * FROM inventory_items WHERE id=? AND is_active=1", (body.item_id,))
    if not item:
        raise HTTPException(404, "Item not found")
    if body.qty <= 0:
        raise HTTPException(400, "Quantity must be positive")
    if item["stock_qty"] < body.qty:
        raise HTTPException(400, f"Insufficient stock. Available: {item['stock_qty']}")
    execute(
        "UPDATE inventory_items SET stock_qty = stock_qty - ? WHERE id=?",
        (body.qty, body.item_id),
    )
    execute(
        """INSERT INTO inventory_transactions (item_id, type, qty, reference, notes, student_id, recorded_by)
           VALUES (?, 'issued', ?, ?, ?, ?, ?)""",
        (body.item_id, body.qty, body.purpose or None, None, body.student_id, user.get("id")),
    )
    return dict(fetch_one("SELECT * FROM inventory_items WHERE id=?", (body.item_id,)))


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
