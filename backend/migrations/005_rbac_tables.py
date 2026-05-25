"""
Migration 005 — RBAC tables

Creates roles, permissions, role_permissions, user_roles,
user_permission_overrides, teacher_assignments, class_teacher_assignments
and seeds them from the ROLES dict in database/db.py.

Safe to run multiple times (idempotent).
"""
import sys
from pathlib import Path

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db import ROLES, get_connection


def run():
    conn = get_connection()
    cur  = conn.cursor()

    # ── Tables ────────────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL,
        color TEXT DEFAULT '#6B7280',
        is_system INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        domain TEXT NOT NULL,
        action TEXT NOT NULL,
        description TEXT,
        scope_type TEXT DEFAULT 'GLOBAL'
            CHECK(scope_type IN ('GLOBAL','SCHOOL','CLASS','DEPARTMENT','OWN')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS role_permissions (
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
        PRIMARY KEY (role_id, permission_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_roles (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        granted_by INTEGER REFERENCES users(id),
        granted_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, role_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_scopes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        scope_type TEXT NOT NULL
            CHECK(scope_type IN ('GLOBAL','SCHOOL','CLASS','DEPARTMENT','OWN')),
        scope_value TEXT,
        permission_code TEXT,
        created_at TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS policy_overrides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_rule  TEXT NOT NULL,
        entity_type  TEXT NOT NULL,
        entity_id    INTEGER NOT NULL,
        decision     TEXT NOT NULL CHECK(decision IN ('allow','deny')),
        reason       TEXT,
        granted_by   INTEGER REFERENCES users(id),
        expires_at   TEXT,
        created_at   TEXT DEFAULT (datetime('now')),
        UNIQUE(policy_rule, entity_type, entity_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_permission_overrides (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        permission  TEXT NOT NULL,
        effect      TEXT NOT NULL CHECK(effect IN ('ALLOW','DENY')),
        reason      TEXT,
        granted_by  INTEGER REFERENCES users(id),
        expires_at  TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, permission))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS teacher_assignments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_id         INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        subject_id       INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        academic_year_id INTEGER REFERENCES academic_years(id),
        is_active        INTEGER NOT NULL DEFAULT 1,
        assigned_by      INTEGER REFERENCES users(id),
        assigned_at      TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, class_id, subject_id, academic_year_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS class_teacher_assignments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_id         INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        academic_year_id INTEGER REFERENCES academic_years(id),
        is_active        INTEGER NOT NULL DEFAULT 1,
        assigned_by      INTEGER REFERENCES users(id),
        assigned_at      TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, class_id, academic_year_id))""")

    # ── Seed permissions ───────────────────────────────────────────────────────
    _ALL_PERMISSIONS = [
        ("*",                           "system",     "*",             "Full system access",                "GLOBAL"),
        ("student.view",                "student",    "view",          "View student records",              "GLOBAL"),
        ("student.view.eligibility",    "student",    "eligibility",   "Eligibility check only",            "GLOBAL"),
        ("student.create",              "student",    "create",        "Create student records",            "GLOBAL"),
        ("student.edit",                "student",    "edit",          "Edit student records",              "GLOBAL"),
        ("student.delete",              "student",    "delete",        "Delete/deactivate students",        "GLOBAL"),
        ("student.promote",             "student",    "promote",       "Promote students",                  "GLOBAL"),
        ("teachers.view",               "teachers",   "view",          "View teacher records",              "GLOBAL"),
        ("teachers.manage",             "teachers",   "manage",        "Create and edit teachers",          "GLOBAL"),
        ("classes.view",                "classes",    "view",          "View class information",            "GLOBAL"),
        ("classes.manage",              "classes",    "manage",        "Create and edit classes",           "GLOBAL"),
        ("timetable.view",              "timetable",  "view",          "View class timetables",             "GLOBAL"),
        ("timetable.manage",            "timetable",  "manage",        "Create and edit timetable slots",   "GLOBAL"),
        ("attendance.view",             "attendance", "view",          "View attendance records",           "CLASS"),
        ("attendance.mark",             "attendance", "mark",          "Mark student attendance",           "CLASS"),
        ("attendance.edit",             "attendance", "edit",          "Edit past attendance",              "CLASS"),
        ("attendance.report",           "attendance", "report",        "Attendance reports",                "GLOBAL"),
        ("grades.view",                 "grades",     "view",          "View grades",                       "CLASS"),
        ("grades.enter",                "grades",     "enter",         "Enter and submit grades",           "CLASS"),
        ("grades.write",                "grades",     "write",         "Write grades",                      "CLASS"),
        ("grades.submit",               "grades",     "submit",        "Submit grades for approval",        "CLASS"),
        ("grades.approve",              "grades",     "approve",       "Approve submitted grades",          "GLOBAL"),
        ("grades.publish",              "grades",     "publish",       "Publish approved grades",           "GLOBAL"),
        ("grades.change_request",       "grades",     "change_req",    "Submit grade change requests",      "GLOBAL"),
        ("grades.change_request.create","grades",     "change_create", "Create grade change requests",      "GLOBAL"),
        ("grades.change_request.review","grades",     "change_review", "Approve grade change requests",     "GLOBAL"),
        ("finance.view",                "finance",    "view",          "View billing and payment status",   "GLOBAL"),
        ("finance.structure.view",      "finance",    "struct.view",   "View fee structures",               "GLOBAL"),
        ("finance.structure.manage",    "finance",    "struct.manage", "Create/edit fee structures",        "GLOBAL"),
        ("finance.billing.generate",    "finance",    "billing",       "Run billing engine",                "GLOBAL"),
        ("finance.payment.record",      "finance",    "pay.record",    "Record fee payments",               "GLOBAL"),
        ("finance.payment.void",        "finance",    "pay.void",      "Void payments",                     "GLOBAL"),
        ("finance.waiver.create",       "finance",    "waiver.create", "Create fee waivers",                "GLOBAL"),
        ("finance.waiver.approve",      "finance",    "waiver.approve","Approve fee waivers",               "GLOBAL"),
        ("finance.report",              "finance",    "report",        "View financial reports",            "GLOBAL"),
        ("inventory.view",              "inventory",  "view",          "View inventory stock",              "GLOBAL"),
        ("inventory.stock.add",         "inventory",  "stock.add",     "Record incoming stock",             "GLOBAL"),
        ("inventory.stock.adjust",      "inventory",  "stock.adjust",  "Adjust stock levels",               "GLOBAL"),
        ("inventory.stock.manage",      "inventory",  "stock.manage",  "Manage inventory items",            "GLOBAL"),
        ("inventory.issue",             "inventory",  "issue",         "Issue items to students",           "GLOBAL"),
        ("inventory.return",            "inventory",  "return",        "Record item returns",               "GLOBAL"),
        ("inventory.report",            "inventory",  "report",        "View inventory reports",            "GLOBAL"),
        ("welfare.view",                "welfare",    "view",          "View welfare records",              "GLOBAL"),
        ("welfare.classify",            "welfare",    "classify",      "Classify students",                 "GLOBAL"),
        ("welfare.edit",                "welfare",    "edit",          "Edit welfare records",              "GLOBAL"),
        ("welfare.verify",              "welfare",    "verify",        "Verify welfare status",             "GLOBAL"),
        ("welfare.sponsor.manage",      "welfare",    "sponsor",       "Manage sponsorships",               "GLOBAL"),
        ("accounting.view",             "accounting", "view",          "View accounting records",           "GLOBAL"),
        ("accounting.expense.record",   "accounting", "expense",       "Record school expenses",            "GLOBAL"),
        ("accounting.report",           "accounting", "report",        "View accounting reports",           "GLOBAL"),
        ("reports.view",                "reports",    "view",          "Access reports module",             "GLOBAL"),
        ("reports.academic",            "reports",    "academic",      "Academic reports",                  "GLOBAL"),
        ("reports.finance",             "reports",    "finance",       "Finance reports",                   "GLOBAL"),
        ("reports.welfare",             "reports",    "welfare",       "Welfare reports",                   "GLOBAL"),
        ("reports.inventory",           "reports",    "inventory",     "Inventory reports",                 "GLOBAL"),
        ("settings.view",               "settings",   "view",          "View settings",                     "GLOBAL"),
        ("settings.school.manage",      "settings",   "school",        "Manage school info",                "GLOBAL"),
        ("settings.years.manage",       "settings",   "years",         "Manage academic years",             "GLOBAL"),
        ("settings.users.manage",       "settings",   "users",         "Manage all user accounts",          "GLOBAL"),
        ("settings.teachers.manage",    "settings",   "teachers",      "Create and manage teacher accounts","GLOBAL"),
        ("settings.roles.manage",       "settings",   "roles",         "Manage roles and permissions",      "GLOBAL"),
        ("library.view",                "library",    "view",          "View library catalogue",            "GLOBAL"),
        ("library.checkout",            "library",    "checkout",      "Issue and return books",            "GLOBAL"),
        ("library.manage",              "library",    "manage",        "Add and edit books",                "GLOBAL"),
        ("transport.view",              "transport",  "view",          "View routes and subscriptions",     "GLOBAL"),
        ("transport.manage",            "transport",  "manage",        "Add and edit transport routes",     "GLOBAL"),
        ("transport.assign",            "transport",  "assign",        "Assign students to routes",         "GLOBAL"),
        ("health.view",                 "health",     "view",          "View health visit records",         "GLOBAL"),
        ("health.record",               "health",     "record",        "Record health visits",              "GLOBAL"),
        ("health.report",               "health",     "report",        "View health reports",               "GLOBAL"),
        ("homework.view",               "homework",   "view",          "View homework assignments",         "CLASS"),
        ("homework.assign",             "homework",   "assign",        "Create homework assignments",       "CLASS"),
        ("homework.write",              "homework",   "write",         "Write homework",                    "CLASS"),
        ("homework.grade",              "homework",   "grade",         "Grade homework submissions",        "CLASS"),
        ("leave.review",                "leave",      "review",        "Review student leave requests",     "GLOBAL"),
        ("enrollment.view",             "enrollment", "view",          "View enrollments",                  "GLOBAL"),
        ("enrollment.manage",           "enrollment", "manage",        "Manage enrollments",                "GLOBAL"),
        ("guardian.view",               "guardian",   "view",          "View guardian records",             "GLOBAL"),
        ("guardian.manage",             "guardian",   "manage",        "Manage guardian records",           "GLOBAL"),
        ("report_cards.view",           "report_cards","view",         "View report cards",                 "GLOBAL"),
        ("report_cards.generate",       "report_cards","generate",     "Generate report cards",             "GLOBAL"),
        ("report_cards.publish",        "report_cards","publish",      "Publish report cards",              "GLOBAL"),
        ("report_cards.comment",        "report_cards","comment",      "Add comments to report cards",      "GLOBAL"),
        ("audit.view",                  "audit",      "view",          "View audit log",                    "GLOBAL"),
        ("portal.student.grades",       "portal",     "student.grades",   "Student: view own grades",       "OWN"),
        ("portal.student.homework",     "portal",     "student.homework", "Student: view and submit homework","OWN"),
        ("portal.parent.grades",        "portal",     "parent.grades",    "Parent: view children's grades", "OWN"),
        ("portal.parent.fees",          "portal",     "parent.fees",      "Parent: view fee balances",      "OWN"),
        ("portal.parent.leave",         "portal",     "parent.leave",     "Parent: submit leave requests",  "OWN"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO permissions(code,domain,action,description,scope_type) VALUES(?,?,?,?,?)",
        _ALL_PERMISSIONS,
    )

    # ── Seed roles from ROLES dict ─────────────────────────────────────────────
    for role_name, info in ROLES.items():
        cur.execute(
            "INSERT OR IGNORE INTO roles(name,label,color) VALUES(?,?,?)",
            (role_name, info["label"], info["color"]),
        )
        cur.execute(
            "UPDATE roles SET label=?,color=? WHERE name=?",
            (info["label"], info["color"], role_name),
        )

    # ── Rebuild role_permissions from ROLES dict ───────────────────────────────
    cur.execute("DELETE FROM role_permissions")
    for role_name, info in ROLES.items():
        role_row = cur.execute("SELECT id FROM roles WHERE name=?", (role_name,)).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for perm_code in info.get("permissions", []):
            perm_row = cur.execute("SELECT id FROM permissions WHERE code=?", (perm_code,)).fetchone()
            if perm_row:
                cur.execute(
                    "INSERT OR IGNORE INTO role_permissions(role_id,permission_id) VALUES(?,?)",
                    (role_id, perm_row[0]),
                )

    # ── Migrate existing users into user_roles (only if table was empty) ───────
    count = cur.execute("SELECT COUNT(*) FROM user_roles").fetchone()[0]
    if count == 0:
        for u_row in cur.execute("SELECT id, role FROM users WHERE is_active=1").fetchall():
            u_id, role_name = u_row
            r = cur.execute("SELECT id FROM roles WHERE name=?", (role_name,)).fetchone()
            if r:
                cur.execute(
                    "INSERT OR IGNORE INTO user_roles(user_id, role_id) VALUES(?,?)",
                    (u_id, r[0]),
                )

    conn.commit()
    conn.close()
    print("  [005] RBAC tables ready")


if __name__ == "__main__":
    run()
