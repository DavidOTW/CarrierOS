from __future__ import annotations

import sqlite3


PHASE2_SCHEMA_VERSION = 14

PHASE2_SCHEMA = """
CREATE TABLE IF NOT EXISTS operational_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    load_id INTEGER,
    document_type TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    storage_provider TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 1,
    sha256 TEXT NOT NULL,
    malware_status TEXT NOT NULL,
    processing_status TEXT NOT NULL,
    retention_date TEXT,
    replaces_document_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (organization_id, sha256, document_type, load_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (replaces_document_id) REFERENCES operational_documents(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ratecon_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    extraction_provider TEXT NOT NULL,
    provider_version TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    extracted_at TEXT NOT NULL,
    reviewed_by INTEGER,
    reviewed_at TEXT,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (document_id, extraction_provider, provider_version),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES operational_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ratecon_extracted_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    extraction_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    extracted_value TEXT NOT NULL,
    confidence_millis INTEGER NOT NULL,
    document_page INTEGER,
    evidence_text TEXT NOT NULL,
    bounding_reference TEXT,
    human_review_status TEXT NOT NULL DEFAULT 'PENDING',
    reviewed_value TEXT,
    reviewed_by INTEGER,
    reviewed_at TEXT,
    UNIQUE (extraction_id, field_name),
    CHECK (human_review_status IN ('PENDING','APPROVED','CORRECTED','REJECTED')),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (extraction_id) REFERENCES ratecon_extractions(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ratecon_match_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    reasons_json TEXT NOT NULL DEFAULT '[]',
    selected_at TEXT,
    selected_by INTEGER,
    UNIQUE (document_id, load_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES operational_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (selected_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ratecon_differences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    booked_value TEXT,
    ratecon_value TEXT,
    classification TEXT NOT NULL,
    financial_impact_cents INTEGER,
    operational_impact TEXT,
    confidence_millis INTEGER NOT NULL,
    evidence_text TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'PENDING',
    approved_by INTEGER,
    approved_at TEXT,
    UNIQUE (document_id, load_id, field_name),
    CHECK (classification IN ('MATCH','INFORMATION_ADDED','MINOR_DIFFERENCE','FINANCIAL_DIFFERENCE','OPERATIONAL_CONFLICT','REVIEW_REQUIRED')),
    CHECK (approval_status IN ('NOT_REQUIRED','PENDING','APPROVED','REJECTED')),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES operational_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS dispatch_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    load_assignment_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    approved_by INTEGER,
    approved_at TEXT,
    acknowledgement_nonce_hash TEXT,
    acknowledged_at TEXT,
    acknowledgement_note TEXT,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (load_id, load_assignment_id),
    UNIQUE (acknowledgement_nonce_hash),
    CHECK (status IN ('AWAITING_APPROVAL','AWAITING_DRIVER_ACK','ACKNOWLEDGED','REVOKED')),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (load_assignment_id) REFERENCES load_assignments(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_operational_documents_org_load
ON operational_documents(organization_id, load_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ratecon_extractions_org_document
ON ratecon_extractions(organization_id, document_id, extracted_at);
CREATE INDEX IF NOT EXISTS idx_ratecon_differences_org_load
ON ratecon_differences(organization_id, load_id, approval_status);
CREATE INDEX IF NOT EXISTS idx_dispatch_approvals_org_load
ON dispatch_approvals(organization_id, load_id, status);

CREATE TRIGGER IF NOT EXISTS ratecon_extractions_no_update
BEFORE UPDATE ON ratecon_extractions
BEGIN
    SELECT RAISE(ABORT, 'ratecon extractions are immutable');
END;

CREATE TRIGGER IF NOT EXISTS ratecon_extractions_no_delete
BEFORE DELETE ON ratecon_extractions
BEGIN
    SELECT RAISE(ABORT, 'ratecon extractions are immutable');
END;

PRAGMA user_version = 14;
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
        raise sqlite3.DatabaseError("Incomplete Phase 2 migration statement")


def migrate_phase2_ratecon_dispatch(conn: sqlite3.Connection) -> None:
    conn.execute("SAVEPOINT phase2_ratecon_dispatch")
    try:
        load_columns = {row["name"] for row in conn.execute("PRAGMA table_info(loads)")}
        for column in ("pickup_timezone", "delivery_timezone"):
            if column not in load_columns:
                conn.execute(f"ALTER TABLE loads ADD COLUMN {column} TEXT")
        _execute_script(conn, PHASE2_SCHEMA)
        conn.execute("RELEASE SAVEPOINT phase2_ratecon_dispatch")
    except sqlite3.DatabaseError:
        conn.execute("ROLLBACK TO SAVEPOINT phase2_ratecon_dispatch")
        conn.execute("RELEASE SAVEPOINT phase2_ratecon_dispatch")
        raise


def rollback_phase2_ratecon_dispatch(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TRIGGER IF EXISTS ratecon_extractions_no_update")
    conn.execute("DROP TRIGGER IF EXISTS ratecon_extractions_no_delete")
    for table in (
        "dispatch_approvals",
        "ratecon_differences",
        "ratecon_match_candidates",
        "ratecon_extracted_fields",
        "ratecon_extractions",
        "operational_documents",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.execute("PRAGMA user_version=13")
