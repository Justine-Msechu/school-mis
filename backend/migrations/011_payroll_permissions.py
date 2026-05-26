"""
Migration 011 — Insert payroll permissions using correct schema.

Migration 009 used wrong column names (key/module/scope instead of
code/domain/scope_type) so the INSERT OR IGNORE silently did nothing.
This migration inserts the payroll permissions correctly.
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    perms = [
        ("payroll.view",    "payroll", "view",    "View payroll runs and payslips"),
        ("payroll.manage",  "payroll", "manage",  "Configure staff salaries and run payroll"),
        ("payroll.approve", "payroll", "approve", "Approve and finalise payroll runs"),
    ]

    perm_ids = {}
    for code, domain, action, desc in perms:
        existing = conn.execute(
            "SELECT id FROM permissions WHERE code=?", (code,)
        ).fetchone()
        if existing:
            perm_ids[code] = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO permissions (code, domain, action, description, scope_type) VALUES (?,?,?,?,?)",
                (code, domain, action, desc, "GLOBAL"),
            )
            perm_ids[code] = cur.lastrowid

    # Grant to admin (id=1), head_teacher (id=2), accountant (id=3)
    grant_to = {"admin", "head_teacher", "accountant"}
    roles = conn.execute(
        "SELECT id, name FROM roles WHERE name IN ('admin','head_teacher','accountant')"
    ).fetchall()

    for role in roles:
        for code in ("payroll.view", "payroll.manage", "payroll.approve"):
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
