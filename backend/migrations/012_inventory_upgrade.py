"""
Migration 012 — Full inventory upgrade.

- Recreate inventory_items without the restrictive category CHECK constraint
- Add supplier / unit_cost / issued_to / department / request_id to inventory_transactions
- Create inventory_requests table (staff → storekeeper issue workflow)
- Insert inventory permissions
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    # ── 1. Recreate inventory_items (drop CHECK constraint on category) ─────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items_v2 (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT,
            unit        TEXT DEFAULT 'pcs',
            unit_price  REAL NOT NULL DEFAULT 0,
            stock_qty   INTEGER NOT NULL DEFAULT 0,
            reorder_qty INTEGER DEFAULT 5,
            is_active   INTEGER DEFAULT 1
        )
    """)

    # Copy only if the new table is empty (first run)
    count = conn.execute("SELECT COUNT(*) FROM inventory_items_v2").fetchone()[0]
    if count == 0:
        conn.execute("""
            INSERT INTO inventory_items_v2 (id, name, category, unit, unit_price, stock_qty, reorder_qty, is_active)
            SELECT id, name, category, unit,
                   COALESCE(unit_price, 0),
                   COALESCE(stock_qty, 0),
                   COALESCE(reorder_qty, 5),
                   COALESCE(is_active, 1)
            FROM inventory_items
        """)
        # Disable FKs temporarily so we can drop the referenced table.
        # Must commit any open transaction first — PRAGMA foreign_keys is a
        # no-op inside a transaction.
        conn.commit()
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE inventory_items")
        conn.execute("ALTER TABLE inventory_items_v2 RENAME TO inventory_items")
        conn.execute("PRAGMA foreign_keys=ON")
    else:
        # Already migrated — drop temp table if it exists
        conn.execute("DROP TABLE IF EXISTS inventory_items_v2")

    # ── 2. Add new columns to inventory_transactions ────────────────────────────
    for ddl in [
        "ALTER TABLE inventory_transactions ADD COLUMN supplier    TEXT",
        "ALTER TABLE inventory_transactions ADD COLUMN unit_cost   REAL DEFAULT 0",
        "ALTER TABLE inventory_transactions ADD COLUMN issued_to   TEXT",
        "ALTER TABLE inventory_transactions ADD COLUMN department  TEXT",
        "ALTER TABLE inventory_transactions ADD COLUMN request_id  INTEGER",
    ]:
        try:
            conn.execute(ddl)
        except Exception:
            pass  # column already exists

    # ── 3. Create inventory_requests ────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id      INTEGER NOT NULL REFERENCES inventory_items(id),
            requested_by INTEGER NOT NULL REFERENCES users(id),
            quantity     INTEGER NOT NULL,
            purpose      TEXT,
            department   TEXT,
            status       TEXT NOT NULL DEFAULT 'pending',
            notes        TEXT,
            reviewed_by  INTEGER REFERENCES users(id),
            reviewed_at  TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── 4. Insert inventory permissions ─────────────────────────────────────────
    perms = [
        ("inventory.view",    "inventory", "view",    "View inventory items and stock levels"),
        ("inventory.manage",  "inventory", "manage",  "Add/edit items and receive stock deliveries"),
        ("inventory.issue",   "inventory", "issue",   "Issue items directly and manage requests"),
        ("inventory.request", "inventory", "request", "Submit item requests to the storekeeper"),
    ]
    perm_ids = {}
    for code, domain, action, desc in perms:
        row = conn.execute("SELECT id FROM permissions WHERE code=?", (code,)).fetchone()
        if row:
            perm_ids[code] = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO permissions (code, domain, action, description, scope_type) VALUES (?,?,?,?,?)",
                (code, domain, action, desc, "GLOBAL"),
            )
            perm_ids[code] = cur.lastrowid

    # Grant to roles
    grants = {
        "admin":        ["inventory.view", "inventory.manage", "inventory.issue", "inventory.request"],
        "head_teacher": ["inventory.view", "inventory.manage", "inventory.issue", "inventory.request"],
        "accountant":   ["inventory.view", "inventory.request"],
        "class_teacher":["inventory.view", "inventory.request"],
        "subject_teacher": ["inventory.view", "inventory.request"],
    }
    roles = conn.execute(
        "SELECT id, name FROM roles WHERE name IN ('admin','head_teacher','accountant','class_teacher','subject_teacher')"
    ).fetchall()
    for role in roles:
        for code in grants.get(role["name"], []):
            pid = perm_ids.get(code)
            if pid:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?,?)",
                        (role["id"], pid),
                    )
                except Exception:
                    pass

    conn.commit()
