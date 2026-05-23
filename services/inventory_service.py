"""
services/inventory_service.py — All inventory business logic.
"""

from __future__ import annotations
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute, db_write


class InventoryService(BaseService):

    # ── Student lookup (used before issuance) ─────────────────────────────────

    def get_student_issuance_status(self, admission_or_ctrl: str) -> dict:
        """
        Look up a student and return their fee/welfare status for issuance gating.

        Returns dict with keys:
          student, unpaid_bills, has_full_waiver, welfare, may_receive
        """
        ref = admission_or_ctrl.strip()

        student = fetch_one(
            "SELECT * FROM students WHERE admission_no=? AND is_active=1", (ref,)
        )
        if not student:
            bill = fetch_one(
                "SELECT student_id FROM student_bills WHERE control_number=?", (ref,)
            )
            if bill:
                student = fetch_one("SELECT * FROM students WHERE id=?",
                                    (bill["student_id"],))
        if not student:
            raise ServiceError(f"No active student found for: {ref}")

        welfare = fetch_one(
            "SELECT * FROM welfare_records WHERE student_id=?", (student["id"],)
        )
        has_full_waiver = bool(
            welfare and welfare["support_type"] == "full_fees"
        )
        unpaid = fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills "
            "WHERE student_id=? AND status IN ('unpaid','partial')",
            (student["id"],)
        )
        unpaid_count = unpaid["n"] if unpaid else 0

        # Pre-evaluate policy (for UI preview — doesn't block yet)
        result = self._evaluate(
            "inventory.issue",
            subject=dict(student),
            extra={"has_full_waiver": has_full_waiver, "unpaid_bills": unpaid_count,
                   "item": {}},
            data={"qty": 1},
        )

        return {
            "student":        dict(student),
            "unpaid_bills":   unpaid_count,
            "has_full_waiver": has_full_waiver,
            "welfare":        dict(welfare) if welfare else None,
            "may_receive":    result.allowed,
            "block_reason":   result.reason if not result.allowed else "",
        }

    # ── Issue an item ─────────────────────────────────────────────────────────

    def issue_item(
        self,
        student_id: int,
        item_id: int,
        qty: int,
        notes: str = "",
    ) -> dict:
        """
        Issue inventory items to a student.

        Flow:
          1. RBAC check
          2. Load student + item
          3. Policy enforce (payment check, stock check, active check)
          4. Write transaction + deduct stock
          5. Audit
        """
        self._require_permission("inventory.*")

        student = fetch_one("SELECT * FROM students WHERE id=? AND is_active=1", (student_id,))
        if not student:
            raise ServiceError("Student not found or inactive.")

        item = fetch_one("SELECT * FROM inventory_items WHERE id=?", (item_id,))
        if not item:
            raise ServiceError("Inventory item not found.")

        welfare = fetch_one(
            "SELECT support_type FROM welfare_records WHERE student_id=?", (student_id,)
        )
        has_full_waiver = bool(welfare and welfare["support_type"] == "full_fees")

        unpaid = fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills "
            "WHERE student_id=? AND status IN ('unpaid','partial')",
            (student_id,)
        )
        unpaid_count = unpaid["n"] if unpaid else 0

        # ── Policy enforcement ────────────────────────────────────────────────
        self._enforce(
            "inventory.issue",
            subject=dict(student),
            data={"qty": qty},
            extra={
                "item":           dict(item),
                "has_full_waiver": has_full_waiver,
                "unpaid_bills":   unpaid_count,
            },
        )

        # ── Write ─────────────────────────────────────────────────────────────
        tx_id = db_write(
            """INSERT INTO inventory_transactions
               (item_id, type, qty, student_id, notes, recorded_by)
               VALUES (?,?,?,?,?,?)""",
            (item_id, "issued", qty, student_id, notes, self._session.user_id),
            action="item_issued", table="inventory_transactions",
            detail=f"Issued {qty}x {item['name']} to {student['admission_no']}",
            user_id=self._session.user_id,
            after_state={"qty": qty, "item_id": item_id, "student_id": student_id},
        )
        execute(
            "UPDATE inventory_items SET stock_qty=stock_qty-? WHERE id=?",
            (qty, item_id),
        )
        return {
            "transaction_id": tx_id,
            "item_name":      item["name"],
            "qty":            qty,
            "student_name":   f"{student['first_name']} {student['last_name']}",
            "admission_no":   student["admission_no"],
        }

    # ── Stock in ──────────────────────────────────────────────────────────────

    def add_stock(self, item_id: int, qty: int, reference: str = "",
                  notes: str = "") -> None:
        self._require_permission("inventory.*")
        item = fetch_one("SELECT * FROM inventory_items WHERE id=?", (item_id,))
        if not item:
            raise ServiceError("Item not found.")
        if qty <= 0:
            raise ServiceError("Quantity must be greater than zero.")

        db_write(
            """INSERT INTO inventory_transactions
               (item_id, type, qty, reference, notes, recorded_by)
               VALUES (?,?,?,?,?,?)""",
            (item_id, "stock_in", qty, reference, notes, self._session.user_id),
            action="stock_in", table="inventory_transactions",
            detail=f"+{qty} {item['name']}",
            user_id=self._session.user_id,
            after_state={"qty": qty, "new_total": item["stock_qty"] + qty},
        )
        execute(
            "UPDATE inventory_items SET stock_qty=stock_qty+? WHERE id=?",
            (qty, item_id),
        )

    # ── Return item ───────────────────────────────────────────────────────────

    def return_item(self, item_id: int, qty: int, student_id: int | None = None,
                    notes: str = "") -> None:
        self._require_permission("inventory.*")
        item = fetch_one("SELECT * FROM inventory_items WHERE id=?", (item_id,))
        if not item:
            raise ServiceError("Item not found.")

        db_write(
            """INSERT INTO inventory_transactions
               (item_id, type, qty, student_id, notes, recorded_by)
               VALUES (?,?,?,?,?,?)""",
            (item_id, "returned", qty, student_id, notes, self._session.user_id),
            action="item_returned", table="inventory_transactions",
            detail=f"Returned {qty}x {item['name']}",
            user_id=self._session.user_id,
        )
        execute(
            "UPDATE inventory_items SET stock_qty=stock_qty+? WHERE id=?",
            (qty, item_id),
        )

    # ── Item management ───────────────────────────────────────────────────────

    def create_item(self, name: str, category: str, unit: str,
                    unit_price: float, reorder_qty: int = 5) -> int:
        self._require_permission("inventory.*")
        if not name.strip():
            raise ServiceError("Item name is required.")
        item_id = execute(
            """INSERT INTO inventory_items
               (name, category, unit, unit_price, stock_qty, reorder_qty)
               VALUES (?,?,?,?,0,?)""",
            (name.strip(), category, unit, unit_price, reorder_qty),
        )
        self._audit("item_created", "inventory_items", item_id,
                    after={"name": name, "category": category, "unit_price": unit_price})
        return item_id

    def get_low_stock_items(self) -> list:
        return [dict(r) for r in fetch_all(
            "SELECT * FROM inventory_items "
            "WHERE is_active=1 AND stock_qty <= reorder_qty ORDER BY name"
        )]


# Singleton
inventory_service = InventoryService()
