from backend.deps import rate_limit
from fastapi import Depends
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["inventory"], dependencies=[Depends(rate_limit(max_calls=150, window_secs=60, scope="inventory"))])
Usr = Annotated[dict, Depends(require_auth)]

ITEM_SELECT = """
    SELECT id, name,
           COALESCE(main_category,'') AS main_category,
           COALESCE(subcategory,'')   AS subcategory,
           COALESCE(item_type,'consumable') AS item_type,
           unit,
           COALESCE(unit_price,0)  AS unit_price,
           stock_qty               AS quantity,
           reorder_qty,
           COALESCE(location,'')   AS location,
           COALESCE(status,'available') AS status,
           is_active
    FROM inventory_items
"""


# ── Items ──────────────────────────────────────────────────────────────────────

@router.get("/items")
def list_items(
    user: Usr,
    search:        str = Query(""),
    main_category: str = Query(""),
    item_type:     str = Query(""),
    status:        str = Query(""),
):
    where = ["is_active=1"]
    params: list = []
    if search:
        where.append("(name LIKE ? OR main_category LIKE ? OR subcategory LIKE ? OR location LIKE ?)")
        params += [f"%{search}%"] * 4
    if main_category:
        where.append("main_category=?"); params.append(main_category)
    if item_type:
        where.append("item_type=?"); params.append(item_type)
    if status:
        where.append("status=?"); params.append(status)
    rows = fetch_all(
        f"{ITEM_SELECT} WHERE {' AND '.join(where)} ORDER BY name", params
    )
    return [dict(r) for r in rows]


@router.get("/items/{item_id}")
def get_item(item_id: int, user: Usr):
    row = fetch_one(f"{ITEM_SELECT} WHERE id=?", (item_id,))
    if not row:
        raise HTTPException(404, "Item not found")
    return dict(row)


@router.get("/low-stock")
def low_stock(user: Usr):
    rows = fetch_all(
        f"{ITEM_SELECT} WHERE is_active=1 AND stock_qty <= reorder_qty ORDER BY name"
    )
    return [dict(r) for r in rows]


@router.get("/stats")
def get_stats(user: Usr):
    total   = fetch_one("SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1")
    low     = fetch_one("SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1 AND stock_qty <= reorder_qty")
    value   = fetch_one("SELECT COALESCE(SUM(stock_qty * unit_price),0) AS v FROM inventory_items WHERE is_active=1")
    pending = fetch_one("SELECT COUNT(*) AS n FROM inventory_requests WHERE status='pending'")
    today   = fetch_one("SELECT COUNT(*) AS n FROM inventory_transactions WHERE DATE(created_at)=DATE('now')")
    return {
        "total_items":      dict(total)["n"]   if total   else 0,
        "low_stock_count":  dict(low)["n"]     if low     else 0,
        "stock_value":      dict(value)["v"]   if value   else 0,
        "pending_requests": dict(pending)["n"] if pending else 0,
        "today_movements":  dict(today)["n"]   if today   else 0,
    }


@router.get("/categories")
def list_categories(user: Usr):
    rows = fetch_all(
        "SELECT DISTINCT main_category FROM inventory_items WHERE is_active=1 AND main_category IS NOT NULL ORDER BY main_category"
    )
    return [dict(r)["main_category"] for r in rows]


class ItemPayload(BaseModel):
    name:          str
    item_type:     str = "consumable"
    main_category: str = ""
    subcategory:   str = ""
    unit:          str = "pcs"
    quantity:      int = 0
    reorder_qty:   int = 5
    unit_price:    float = 0
    location:      str = ""
    status:        str = "available"


@router.post("/items")
def create_item(body: ItemPayload, user: Usr):
    existing = fetch_one("SELECT id FROM inventory_items WHERE name=? AND is_active=1", (body.name,))
    if existing:
        raise HTTPException(400, f"Item '{body.name}' already exists")
    item_id = execute(
        """INSERT INTO inventory_items
           (name, item_type, main_category, subcategory, unit, stock_qty, reorder_qty, unit_price, location, status, is_active)
           VALUES (?,?,?,?,?,?,?,?,?,?,1)""",
        (body.name, body.item_type, body.main_category or None, body.subcategory or None,
         body.unit, body.quantity, body.reorder_qty, body.unit_price,
         body.location or None, body.status),
    )
    if body.quantity > 0:
        execute(
            """INSERT INTO inventory_transactions (item_id, type, qty, notes, recorded_by)
               VALUES (?, 'stock_in', ?, 'Opening stock', ?)""",
            (item_id, body.quantity, user.get("id")),
        )
    return dict(fetch_one(f"{ITEM_SELECT} WHERE id=?", (item_id,)))


@router.put("/items/{item_id}")
def update_item(item_id: int, body: ItemPayload, user: Usr):
    row = fetch_one("SELECT id FROM inventory_items WHERE id=? AND is_active=1", (item_id,))
    if not row:
        raise HTTPException(404, "Item not found")
    execute(
        """UPDATE inventory_items SET
           name=?, item_type=?, main_category=?, subcategory=?,
           unit=?, reorder_qty=?, unit_price=?, location=?, status=?
           WHERE id=?""",
        (body.name, body.item_type, body.main_category or None, body.subcategory or None,
         body.unit, body.reorder_qty, body.unit_price, body.location or None, body.status,
         item_id),
    )
    return dict(fetch_one(f"{ITEM_SELECT} WHERE id=?", (item_id,)))


@router.delete("/items/{item_id}")
def deactivate_item(item_id: int, user: Usr):
    row = fetch_one("SELECT id FROM inventory_items WHERE id=? AND is_active=1", (item_id,))
    if not row:
        raise HTTPException(404, "Item not found")
    execute("UPDATE inventory_items SET is_active=0 WHERE id=?", (item_id,))
    return {"ok": True}


# ── Receive stock (stock in) ──────────────────────────────────────────────────

class ReceiveBody(BaseModel):
    item_id:   int
    quantity:  int
    supplier:  str = ""
    unit_cost: float = 0
    reference: str = ""
    notes:     str = ""


@router.post("/receive")
def receive_stock(body: ReceiveBody, user: Usr):
    item = fetch_one("SELECT * FROM inventory_items WHERE id=? AND is_active=1", (body.item_id,))
    if not item:
        raise HTTPException(404, "Item not found")
    if body.quantity <= 0:
        raise HTTPException(400, "Quantity must be positive")
    execute(
        "UPDATE inventory_items SET stock_qty = stock_qty + ?, unit_price = CASE WHEN ? > 0 THEN ? ELSE unit_price END WHERE id=?",
        (body.quantity, body.unit_cost, body.unit_cost, body.item_id),
    )
    execute(
        """INSERT INTO inventory_transactions
           (item_id, type, qty, supplier, unit_cost, reference, notes, recorded_by)
           VALUES (?, 'stock_in', ?, ?, ?, ?, ?, ?)""",
        (body.item_id, body.quantity, body.supplier or None, body.unit_cost or None,
         body.reference or None, body.notes or None, user.get("id")),
    )
    return dict(fetch_one(f"{ITEM_SELECT} WHERE id=?", (body.item_id,)))


# Keep old endpoint for backward compat
@router.post("/add-stock")
def add_stock(body: ReceiveBody, user: Usr):
    return receive_stock(body, user)


# ── Direct issue ──────────────────────────────────────────────────────────────

class IssueBody(BaseModel):
    item_id:    int
    quantity:   int
    issued_to:  str = ""
    department: str = ""
    purpose:    str = ""
    notes:      str = ""


@router.post("/issue")
def issue_item(body: IssueBody, user: Usr):
    item = fetch_one("SELECT * FROM inventory_items WHERE id=? AND is_active=1", (body.item_id,))
    if not item:
        raise HTTPException(404, "Item not found")
    if body.quantity <= 0:
        raise HTTPException(400, "Quantity must be positive")
    if item["stock_qty"] < body.quantity:
        raise HTTPException(400, f"Insufficient stock. Available: {item['stock_qty']}")
    execute(
        "UPDATE inventory_items SET stock_qty = stock_qty - ? WHERE id=?",
        (body.quantity, body.item_id),
    )
    execute(
        """INSERT INTO inventory_transactions
           (item_id, type, qty, issued_to, department, reference, notes, recorded_by)
           VALUES (?, 'issued', ?, ?, ?, ?, ?, ?)""",
        (body.item_id, body.quantity, body.issued_to or None, body.department or None,
         body.purpose or None, body.notes or None, user.get("id")),
    )
    return dict(fetch_one(f"{ITEM_SELECT} WHERE id=?", (body.item_id,)))


# ── Stocktake ─────────────────────────────────────────────────────────────────

class StocktakeEntry(BaseModel):
    item_id:       int
    physical_qty:  int


class StocktakeBody(BaseModel):
    entries: list[StocktakeEntry]
    notes:   str = ""


@router.post("/stocktake")
def do_stocktake(body: StocktakeBody, user: Usr):
    results = []
    for entry in body.entries:
        item = fetch_one("SELECT * FROM inventory_items WHERE id=? AND is_active=1", (entry.item_id,))
        if not item:
            continue
        diff = entry.physical_qty - item["stock_qty"]
        if diff == 0:
            results.append({"item_id": entry.item_id, "name": item["name"], "system_qty": item["stock_qty"], "physical_qty": entry.physical_qty, "diff": 0})
            continue
        execute(
            "UPDATE inventory_items SET stock_qty=? WHERE id=?",
            (entry.physical_qty, entry.item_id),
        )
        execute(
            """INSERT INTO inventory_transactions
               (item_id, type, qty, notes, recorded_by)
               VALUES (?, 'adjusted', ?, ?, ?)""",
            (entry.item_id, abs(diff),
             f"Stocktake adjustment {'+' if diff > 0 else ''}{diff}. {body.notes}".strip(),
             user.get("id")),
        )
        results.append({"item_id": entry.item_id, "name": item["name"], "system_qty": item["stock_qty"], "physical_qty": entry.physical_qty, "diff": diff})
    return results


# ── Issue requests ────────────────────────────────────────────────────────────

class RequestBody(BaseModel):
    item_id:    int
    quantity:   int
    purpose:    str = ""
    department: str = ""
    notes:      str = ""


@router.get("/requests")
def list_requests(user: Usr, status: str = Query(""), my_only: bool = Query(False)):
    where = ["1=1"]
    params: list = []
    if status:
        where.append("r.status=?"); params.append(status)
    if my_only:
        where.append("r.requested_by=?"); params.append(user.get("id"))
    rows = fetch_all(
        f"""SELECT r.*,
                   i.name AS item_name, i.unit,
                   u.username AS requester_name,
                   rv.username AS reviewer_name
            FROM inventory_requests r
            JOIN inventory_items i ON i.id=r.item_id
            JOIN users u ON u.id=r.requested_by
            LEFT JOIN users rv ON rv.id=r.reviewed_by
            WHERE {' AND '.join(where)}
            ORDER BY r.created_at DESC""",
        params,
    )
    return [dict(r) for r in rows]


@router.post("/requests")
def create_request(body: RequestBody, user: Usr):
    item = fetch_one("SELECT * FROM inventory_items WHERE id=? AND is_active=1", (body.item_id,))
    if not item:
        raise HTTPException(404, "Item not found")
    if body.quantity <= 0:
        raise HTTPException(400, "Quantity must be positive")
    req_id = execute(
        """INSERT INTO inventory_requests (item_id, requested_by, quantity, purpose, department, notes)
           VALUES (?,?,?,?,?,?)""",
        (body.item_id, user.get("id"), body.quantity,
         body.purpose or None, body.department or None, body.notes or None),
    )
    row = fetch_one(
        """SELECT r.*, i.name AS item_name, i.unit, u.username AS requester_name
           FROM inventory_requests r
           JOIN inventory_items i ON i.id=r.item_id
           JOIN users u ON u.id=r.requested_by
           WHERE r.id=?""",
        (req_id,),
    )
    return dict(row)


class ReviewBody(BaseModel):
    notes: str = ""


@router.post("/requests/{req_id}/approve")
def approve_request(req_id: int, body: ReviewBody, user: Usr):
    req = fetch_one("SELECT * FROM inventory_requests WHERE id=?", (req_id,))
    if not req:
        raise HTTPException(404, "Request not found")
    req = dict(req)
    if req["status"] != "pending":
        raise HTTPException(400, f"Request is already {req['status']}")
    item = fetch_one("SELECT * FROM inventory_items WHERE id=? AND is_active=1", (req["item_id"],))
    if not item:
        raise HTTPException(404, "Item not found")
    if item["stock_qty"] < req["quantity"]:
        raise HTTPException(400, f"Insufficient stock. Available: {item['stock_qty']}")
    execute(
        "UPDATE inventory_items SET stock_qty = stock_qty - ? WHERE id=?",
        (req["quantity"], req["item_id"]),
    )
    execute(
        """INSERT INTO inventory_transactions
           (item_id, type, qty, issued_to, department, notes, request_id, recorded_by)
           VALUES (?, 'issued', ?, ?, ?, ?, ?, ?)""",
        (req["item_id"], req["quantity"], None, req.get("department"),
         f"Request #{req_id}: {req.get('purpose') or ''}".strip(": "),
         req_id, user.get("id")),
    )
    execute(
        """UPDATE inventory_requests SET status='issued', reviewed_by=?, reviewed_at=datetime('now'), notes=?
           WHERE id=?""",
        (user.get("id"), body.notes or req.get("notes"), req_id),
    )
    return {"ok": True}


@router.post("/requests/{req_id}/reject")
def reject_request(req_id: int, body: ReviewBody, user: Usr):
    req = fetch_one("SELECT * FROM inventory_requests WHERE id=?", (req_id,))
    if not req:
        raise HTTPException(404, "Request not found")
    if dict(req)["status"] != "pending":
        raise HTTPException(400, f"Request is already {dict(req)['status']}")
    execute(
        """UPDATE inventory_requests SET status='rejected', reviewed_by=?, reviewed_at=datetime('now'), notes=?
           WHERE id=?""",
        (user.get("id"), body.notes or None, req_id),
    )
    return {"ok": True}


# ── Transactions (movement history) ──────────────────────────────────────────

@router.get("/transactions")
def get_transactions(
    user: Usr,
    item_id:  int = Query(None),
    type:     str = Query(""),
    limit:    int = Query(100),
):
    where = ["1=1"]
    params: list = []
    if item_id:
        where.append("t.item_id=?"); params.append(item_id)
    if type:
        where.append("t.type=?"); params.append(type)
    rows = fetch_all(
        f"""SELECT t.*,
                   i.name   AS item_name,
                   i.unit   AS item_unit,
                   u.username AS recorded_by_name
            FROM inventory_transactions t
            JOIN inventory_items i ON i.id=t.item_id
            LEFT JOIN users u ON u.id=t.recorded_by
            WHERE {' AND '.join(where)}
            ORDER BY t.created_at DESC LIMIT ?""",
        params + [limit],
    )
    return [dict(r) for r in rows]
