"""
Migration 014 — Inventory category management tables.

Creates inventory_categories and inventory_subcategories tables and seeds
the default categories that were previously hardcoded in the frontend.
"""

DEFAULT_CATEGORIES = {
    "Stationery":            ["Writing Materials", "Paper Products", "Filing & Binding", "Art Supplies"],
    "Cleaning & Sanitation": ["Cleaning Agents", "Cleaning Equipment", "Hygiene Products"],
    "Lab & Science":         ["Chemistry", "Biology", "Physics", "General Lab"],
    "Furniture":             ["Chairs", "Desks & Tables", "Storage", "Other Furniture"],
    "IT & Electronics":      ["Computers", "Peripherals", "Audio/Visual", "Other Electronics"],
    "Sports & PE":           ["Ball Games", "Athletics", "Indoor Games", "Other Sports"],
    "Medical & First Aid":   ["Medicines", "First Aid Equipment", "PPE"],
    "Books & Learning":      ["Textbooks", "Exercise Books", "Reference Books", "Teaching Aids"],
    "Food & Catering":       ["Food Items", "Utensils", "Catering Equipment"],
    "Other":                 ["General"],
}


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            is_active  INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_subcategories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES inventory_categories(id),
            name        TEXT NOT NULL,
            sort_order  INTEGER DEFAULT 0,
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(category_id, name)
        )
    """)

    # Seed defaults only if empty
    existing = conn.execute("SELECT COUNT(*) FROM inventory_categories").fetchone()[0]
    if existing == 0:
        for order, (cat_name, subcats) in enumerate(DEFAULT_CATEGORIES.items()):
            cur = conn.execute(
                "INSERT OR IGNORE INTO inventory_categories (name, sort_order) VALUES (?,?)",
                (cat_name, order),
            )
            cat_id = cur.lastrowid or conn.execute(
                "SELECT id FROM inventory_categories WHERE name=?", (cat_name,)
            ).fetchone()["id"]
            for sub_order, sub_name in enumerate(subcats):
                conn.execute(
                    "INSERT OR IGNORE INTO inventory_subcategories (category_id, name, sort_order) VALUES (?,?,?)",
                    (cat_id, sub_name, sub_order),
                )

    conn.commit()
