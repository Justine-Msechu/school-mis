"""
Migration 013 — Inventory item classification fields.

- Rename category → main_category (SQLite 3.25+ supports RENAME COLUMN)
- Add: subcategory, item_type (consumable/asset), location, status
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    # Rename category → main_category (idempotent: check first)
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(inventory_items)").fetchall()]

    if "category" in cols and "main_category" not in cols:
        conn.execute("ALTER TABLE inventory_items RENAME COLUMN category TO main_category")

    for ddl in [
        "ALTER TABLE inventory_items ADD COLUMN subcategory TEXT",
        "ALTER TABLE inventory_items ADD COLUMN item_type   TEXT NOT NULL DEFAULT 'consumable'",
        "ALTER TABLE inventory_items ADD COLUMN location    TEXT",
        "ALTER TABLE inventory_items ADD COLUMN status      TEXT NOT NULL DEFAULT 'available'",
    ]:
        try:
            conn.execute(ddl)
        except Exception:
            pass  # column already exists

    conn.commit()
