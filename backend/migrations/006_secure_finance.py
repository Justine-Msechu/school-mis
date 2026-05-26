"""
Migration 006 — Secure invoice and finance audit tables.

Adds:
  - invoices          full invoice lifecycle with state machine
  - invoice_items     line items linked to invoices
  - finance_audit_log append-only audit trail (never UPDATE/DELETE)

Also adds a partial UNIQUE index on fee_payments.reference_no to prevent
duplicate transaction reference numbers.
"""


def run():
    from backend.core.db import _get_conn
    conn = _get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id                        INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no                TEXT NOT NULL UNIQUE,
            student_id                INTEGER NOT NULL REFERENCES students(id),
            academic_year_id          INTEGER REFERENCES academic_years(id),
            term                      INTEGER CHECK(term IN (1,2,3)),
            status                    TEXT NOT NULL DEFAULT 'draft'
                                      CHECK(status IN
                                           ('draft','approved','partially_paid',
                                            'paid','cancelled','voided')),
            total_amount              REAL NOT NULL DEFAULT 0,
            paid_amount               REAL NOT NULL DEFAULT 0,
            discount_amount           REAL NOT NULL DEFAULT 0,
            control_number            TEXT UNIQUE,
            control_number_expires_at TEXT,
            control_number_issued_at  TEXT,
            notes                     TEXT,
            created_by                INTEGER REFERENCES users(id),
            approved_by               INTEGER REFERENCES users(id),
            approved_at               TEXT,
            voided_by                 INTEGER REFERENCES users(id),
            voided_at                 TEXT,
            void_reason               TEXT,
            created_at                TEXT DEFAULT (datetime('now')),
            updated_at                TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id      INTEGER NOT NULL REFERENCES invoices(id),
            bill_id         INTEGER REFERENCES student_bills(id),
            fee_type_id     INTEGER REFERENCES fee_types(id),
            description     TEXT NOT NULL,
            amount          REAL NOT NULL,
            discount_amount REAL NOT NULL DEFAULT 0,
            quantity        INTEGER NOT NULL DEFAULT 1,
            line_total      REAL NOT NULL,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # Append-only audit log — never UPDATE or DELETE rows from this table.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id   INTEGER,
            action      TEXT NOT NULL,
            actor_id    INTEGER REFERENCES users(id),
            actor_name  TEXT,
            before_json TEXT,
            after_json  TEXT,
            detail      TEXT,
            ip_address  TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # Prevent duplicate bank/mobile reference numbers (NULL values are exempt
    # from UNIQUE constraints in SQLite, so this only fires on non-empty refs).
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_fee_payments_ref "
            "ON fee_payments(reference_no) "
            "WHERE reference_no IS NOT NULL AND reference_no != ''"
        )
    except Exception:
        pass

    conn.commit()
