from __future__ import annotations

import sqlite3


PHASE3_SCHEMA_VERSION = 15

PHASE3_SCHEMA = """
CREATE TABLE IF NOT EXISTS delivery_document_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    document_kind TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'driver_portal',
    captured_by_user INTEGER,
    captured_by_driver INTEGER,
    review_status TEXT NOT NULL DEFAULT 'PENDING',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    reviewed_by INTEGER,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (organization_id, document_id),
    CHECK (document_kind IN ('BOL','POD','RECEIPT','DETENTION_EVIDENCE')),
    CHECK (source IN ('driver_portal','office')),
    CHECK (review_status IN ('PENDING','ACCEPTED','REJECTED')),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES operational_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (captured_by_user) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (captured_by_driver) REFERENCES drivers(id) ON DELETE SET NULL,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_delivery_documents_org_load
ON delivery_document_links(organization_id, load_id, document_kind, created_at);

PRAGMA user_version = 15;
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
        raise sqlite3.DatabaseError("Incomplete Phase 3 migration statement")


def migrate_phase3_delivery_to_cash(conn: sqlite3.Connection) -> None:
    conn.execute("SAVEPOINT phase3_delivery_to_cash")
    try:
        _execute_script(conn, PHASE3_SCHEMA)
        conn.execute("RELEASE SAVEPOINT phase3_delivery_to_cash")
    except sqlite3.DatabaseError:
        conn.execute("ROLLBACK TO SAVEPOINT phase3_delivery_to_cash")
        conn.execute("RELEASE SAVEPOINT phase3_delivery_to_cash")
        raise


def rollback_phase3_delivery_to_cash(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS delivery_document_links")
    conn.execute("PRAGMA user_version=14")
