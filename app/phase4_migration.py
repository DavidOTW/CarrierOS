from __future__ import annotations

import sqlite3


PHASE4_SCHEMA_VERSION = 16

PHASE4_SCHEMA = """
CREATE TABLE IF NOT EXISTS invoice_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    paid_date TEXT NOT NULL,
    payment_reference TEXT,
    notes TEXT,
    idempotency_key TEXT NOT NULL,
    recorded_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, idempotency_key),
    CHECK (amount > 0),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_invoice_payments_org_invoice
ON invoice_payments(organization_id, invoice_id, paid_date, id);

PRAGMA user_version = 16;
"""


def _execute_script(conn: sqlite3.Connection, script: str) -> None:
    statement = ""
    for line in script.splitlines():
        statement += line + "\n"
        if sqlite3.complete_statement(statement):
            sql = statement.strip()
            statement = ""
            if sql:
                conn.execute(sql)
    if statement.strip():
        raise sqlite3.DatabaseError("Incomplete Phase 4 migration statement")


def migrate_phase4_delivery_to_cash(conn: sqlite3.Connection) -> None:
    conn.execute("SAVEPOINT phase4_delivery_to_cash")
    try:
        _execute_script(conn, PHASE4_SCHEMA)
        conn.execute("RELEASE SAVEPOINT phase4_delivery_to_cash")
    except sqlite3.DatabaseError:
        conn.execute("ROLLBACK TO SAVEPOINT phase4_delivery_to_cash")
        conn.execute("RELEASE SAVEPOINT phase4_delivery_to_cash")
        raise


def rollback_phase4_delivery_to_cash(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS invoice_payments")
    conn.execute("PRAGMA user_version=15")
