"""
School MIS — Database Layer  (v3)
Added: finance, welfare, inventory, accounting, reporting domains.
"""

import sqlite3, os, hashlib, secrets

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "school_mis.db")

ROLES = {
    "admin": {
        "label": "Administrator", "color": "#7C3AED",
        "permissions": ["*"],
    },
    "head_teacher": {
        "label": "Head Teacher", "color": "#059669",
        "permissions": ["students.*","teachers.*","classes.*",
                        "attendance.*","grades.*","grades.approve",
                        "finance.*","welfare.*","reports.*","settings.view"],
    },
    "accountant": {
        "label": "Accountant", "color": "#DC2626",
        "permissions": ["finance.*","accounting.*","students.view",
                        "reports.finance","reports.welfare","inventory.view"],
    },
    "welfare_officer": {
        "label": "Welfare Officer", "color": "#9333EA",
        "permissions": ["welfare.*","students.view","finance.view",
                        "reports.welfare","reports.finance"],
    },
    "storekeeper": {
        "label": "Store Keeper", "color": "#D97706",
        "permissions": ["inventory.*","students.view","finance.view",
                        "reports.inventory"],
    },
    "academic": {
        "label": "Academic Officer", "color": "#0891B2",
        "permissions": ["students.view","classes.view","teachers.view",
                        "grades.*","grades.approve","grades.publish",
                        "attendance.view","reports.*"],
    },
    "class_teacher": {
        "label": "Class Teacher", "color": "#2563EB",
        "permissions": ["students.view","classes.view",
                        "attendance.*","grades.view","grades.enter","reports.view"],
    },
    "subject_teacher": {
        "label": "Subject Teacher", "color": "#0891B2",
        "permissions": ["students.view","grades.enter","grades.view","attendance.view"],
    },
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS school_config (
        key TEXT PRIMARY KEY, value TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS academic_years (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL UNIQUE,
        start_date TEXT NOT NULL, end_date TEXT NOT NULL,
        is_current INTEGER DEFAULT 0)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL, last_name TEXT NOT NULL,
        gender TEXT CHECK(gender IN ('Male','Female','Other')),
        phone TEXT, email TEXT,
        role TEXT DEFAULT 'Teacher',
        qualification TEXT, hire_date TEXT,
        is_active INTEGER DEFAULT 1, notes TEXT,
        created_at TEXT DEFAULT (date('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'subject_teacher',
        teacher_id INTEGER REFERENCES teachers(id),
        full_name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        must_change_pw INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, grade_level INTEGER NOT NULL,
        academic_year_id INTEGER REFERENCES academic_years(id),
        teacher_id INTEGER REFERENCES teachers(id),
        capacity INTEGER DEFAULT 40, room TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission_no TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL, last_name TEXT NOT NULL,
        gender TEXT CHECK(gender IN ('Male','Female','Other')),
        date_of_birth TEXT,
        class_id INTEGER REFERENCES classes(id),
        parent_name TEXT, parent_phone TEXT, parent_email TEXT,
        address TEXT, photo_path TEXT,
        enrollment_date TEXT DEFAULT (date('now')),
        is_active INTEGER DEFAULT 1, notes TEXT,
        created_at TEXT DEFAULT (date('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, code TEXT UNIQUE,
        grade_level INTEGER)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS teacher_subjects (
        teacher_id INTEGER REFERENCES teachers(id),
        subject_id INTEGER REFERENCES subjects(id),
        class_id   INTEGER REFERENCES classes(id),
        PRIMARY KEY (teacher_id, subject_id, class_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER REFERENCES classes(id),
        subject_id INTEGER REFERENCES subjects(id),
        teacher_id INTEGER REFERENCES teachers(id),
        day_of_week TEXT CHECK(day_of_week IN ('Mon','Tue','Wed','Thu','Fri')),
        start_time TEXT, end_time TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id),
        class_id INTEGER REFERENCES classes(id),
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late','Excused')),
        notes TEXT,
        recorded_by INTEGER REFERENCES users(id),
        UNIQUE(student_id, date))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        academic_year_id INTEGER REFERENCES academic_years(id),
        term INTEGER CHECK(term IN (1,2,3)),
        start_date TEXT, end_date TEXT,
        status TEXT DEFAULT 'open' CHECK(status IN ('open','locked','published')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id),
        exam_id INTEGER NOT NULL REFERENCES exams(id),
        subject_id INTEGER NOT NULL REFERENCES subjects(id),
        score REAL, max_score REAL DEFAULT 100,
        grade_letter TEXT, remarks TEXT,
        entered_by INTEGER REFERENCES users(id),
        approved_by INTEGER REFERENCES users(id),
        status TEXT DEFAULT 'draft' CHECK(status IN ('draft','submitted','approved')),
        UNIQUE(student_id, exam_id, subject_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fee_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, amount REAL NOT NULL,
        term INTEGER, description TEXT)""")

    # ── Finance domain ──────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS fee_structures (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        class_id         INTEGER REFERENCES classes(id),
        fee_type_id      INTEGER NOT NULL REFERENCES fee_types(id),
        amount           REAL NOT NULL,
        term             INTEGER CHECK(term IN (1,2,3)),
        due_date         TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS student_bills (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        fee_structure_id INTEGER NOT NULL REFERENCES fee_structures(id),
        academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
        control_number   TEXT NOT NULL UNIQUE,
        amount_due       REAL NOT NULL,
        amount_paid      REAL NOT NULL DEFAULT 0,
        discount_amount  REAL NOT NULL DEFAULT 0,
        status           TEXT NOT NULL DEFAULT 'unpaid'
                         CHECK(status IN ('unpaid','partial','paid','waived')),
        due_date         TEXT,
        created_at       TEXT DEFAULT (datetime('now')),
        UNIQUE(student_id, fee_structure_id))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fee_payments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id          INTEGER REFERENCES student_bills(id),
        student_id       INTEGER NOT NULL REFERENCES students(id),
        fee_type_id      INTEGER REFERENCES fee_types(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        amount_paid      REAL NOT NULL,
        payment_date     TEXT NOT NULL DEFAULT (date('now')),
        control_number   TEXT,
        receipt_no       TEXT UNIQUE,
        payment_method   TEXT DEFAULT 'Cash'
                         CHECK(payment_method IN
                              ('Cash','Mobile Money','Bank Transfer','Cheque')),
        reference_no     TEXT,
        notes            TEXT,
        recorded_by      INTEGER REFERENCES users(id),
        created_at       TEXT DEFAULT (datetime('now')))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fee_waivers (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id       INTEGER NOT NULL REFERENCES students(id),
        bill_id          INTEGER REFERENCES student_bills(id),
        academic_year_id INTEGER REFERENCES academic_years(id),
        waiver_type      TEXT NOT NULL
                         CHECK(waiver_type IN ('orphan_exemption','scholarship',
                                               'partial_discount','staff_child','other')),
        discount_percent REAL NOT NULL DEFAULT 100,
        approved_by      INTEGER REFERENCES users(id),
        reason           TEXT,
        created_at       TEXT DEFAULT (datetime('now')))""")

    # ── Welfare domain ──────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS welfare_records (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL UNIQUE REFERENCES students(id),
        category        TEXT NOT NULL
                        CHECK(category IN ('orphan','half_orphan','sponsored','vulnerable')),
        verified        INTEGER DEFAULT 0,
        verified_by     INTEGER REFERENCES users(id),
        verified_date   TEXT,
        sponsor_name    TEXT,
        sponsor_org     TEXT,
        support_type    TEXT
                        CHECK(support_type IN ('full_fees','partial','non_financial')),
        notes           TEXT,
        created_at      TEXT DEFAULT (datetime('now')))""")

    # ── Inventory domain ────────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS inventory_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        category    TEXT CHECK(category IN
                        ('uniform','book','stationery','equipment','other')),
        unit        TEXT DEFAULT 'pcs',
        unit_price  REAL NOT NULL DEFAULT 0,
        stock_qty   INTEGER NOT NULL DEFAULT 0,
        reorder_qty INTEGER DEFAULT 5,
        is_active   INTEGER DEFAULT 1)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS inventory_transactions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id     INTEGER NOT NULL REFERENCES inventory_items(id),
        type        TEXT NOT NULL
                    CHECK(type IN ('stock_in','issued','adjusted','returned')),
        qty         INTEGER NOT NULL,
        student_id  INTEGER REFERENCES students(id),
        bill_id     INTEGER REFERENCES student_bills(id),
        reference   TEXT,
        notes       TEXT,
        recorded_by INTEGER REFERENCES users(id),
        created_at  TEXT DEFAULT (datetime('now')))""")

    # ── Accounting domain ───────────────────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        category     TEXT NOT NULL
                     CHECK(category IN
                          ('salaries','utilities','supplies','maintenance',
                           'transport','welfare','other')),
        description  TEXT NOT NULL,
        amount       REAL NOT NULL,
        expense_date TEXT NOT NULL DEFAULT (date('now')),
        receipt_ref  TEXT,
        approved_by  INTEGER REFERENCES users(id),
        recorded_by  INTEGER REFERENCES users(id),
        created_at   TEXT DEFAULT (datetime('now')))""")

    # ── Migrate existing students table ────────────────────────────────────────
    for col_def in [
        ("student_category", "TEXT DEFAULT 'regular' CHECK(student_category IN ('regular','orphan','sponsored'))"),
        ("sponsor_name",     "TEXT"),
        ("sponsor_org",      "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE students ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass  # column already exists

    cur.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL, table_name TEXT, record_id INTEGER,
        detail TEXT, ts TEXT DEFAULT (datetime('now')))""")

    # Seed defaults on first run
    cur.execute("SELECT COUNT(*) FROM academic_years")
    if cur.fetchone()[0] == 0:
        cur.execute("""INSERT INTO academic_years(label,start_date,end_date,is_current)
            VALUES('2024/2025','2024-09-01','2025-07-31',1)""")
        cur.executemany("INSERT OR IGNORE INTO subjects(name,code) VALUES(?,?)", [
            ("Mathematics","MATH"),("English Language","ENG"),
            ("Kiswahili","KSW"),("Science","SCI"),
            ("Social Studies","SST"),("Religious Education","RE"),
            ("Physical Education","PE"),("Arts & Craft","ART"),
        ])

    conn.commit()
    conn.close()


# ── Auth helpers ──────────────────────────────────────────────────────────────
def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt

def verify_password(password, stored_hash, salt):
    h, _ = hash_password(password, salt)
    return h == stored_hash

def create_user(username, password, role, full_name, teacher_id=None, must_change=False):
    h, salt = hash_password(password)
    return execute("""INSERT INTO users(username,password_hash,salt,role,full_name,teacher_id,must_change_pw)
        VALUES(?,?,?,?,?,?,?)""", (username, h, salt, role, full_name, teacher_id, 1 if must_change else 0))

def authenticate(username: str, password: str):
    user = fetch_one("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
    if not user: return None
    if verify_password(password, user["password_hash"], user["salt"]):
        execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],))
        return dict(user)
    return None

# ── Config helpers ────────────────────────────────────────────────────────────
def get_config(key, default=None):
    row = fetch_one("SELECT value FROM school_config WHERE key=?", (key,))
    return row["value"] if row else default

def set_config(key, value):
    execute("INSERT INTO school_config(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value) if value is not None else ""))

def is_setup_complete():
    return get_config("setup_complete") == "1"

# ── Generic query helpers ─────────────────────────────────────────────────────
def fetch_all(sql, params=()):
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows

def fetch_one(sql, params=()):
    conn = get_connection()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row

def execute(sql, params=()):
    conn = get_connection()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def execute_many(sql, data):
    conn = get_connection()
    conn.executemany(sql, data)
    conn.commit()
    conn.close()


def db_write(sql, params=(), action="", table="", record_id=None, detail="", user_id=None):
    """Write + audit in a single transaction."""
    conn = get_connection()
    cur  = conn.execute(sql, params)
    rid  = cur.lastrowid
    if action:
        conn.execute(
            "INSERT INTO audit_log(user_id,action,table_name,record_id,detail) VALUES(?,?,?,?,?)",
            (user_id, action, table, record_id or rid, detail)
        )
    conn.commit()
    conn.close()
    return rid


def gen_control_number(student_admission: str, year_label: str, term: int, seq: int) -> str:
    yr = year_label.split("/")[0]
    adm = student_admission.replace(" ", "")
    return f"SCH-{yr}-{adm}-T{term}-{seq:03d}"


def gen_receipt_number() -> str:
    import datetime, random
    d = datetime.date.today().strftime("%Y%m%d")
    seq = random.randint(1, 9999)
    return f"RCP-{d}-{seq:04d}"
