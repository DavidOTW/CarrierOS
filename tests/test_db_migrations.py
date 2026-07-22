from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db import connect, init_db


def test_existing_organization_gets_launch_columns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as conn:
        conn.execute(
            """CREATE TABLE organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_code TEXT NOT NULL DEFAULT 'owner_operator',
            active_unit_limit INTEGER NOT NULL DEFAULT 2,
            subscription_status TEXT NOT NULL DEFAULT 'trialing',
            trial_ends_at TEXT,
            billing_customer_reference TEXT
            )"""
        )
    monkeypatch.setenv("CARRIEROS_DB", str(database))
    init_db()
    with connect() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(organizations)")}
        indexes = {row["name"] for row in conn.execute("PRAGMA index_list(organizations)")}
    assert {
        "billing_subscription_reference",
        "billing_price_reference",
        "subscription_current_period_end",
        "subscription_cancel_at_period_end",
        "terms_accepted_at",
        "terms_version",
    } <= columns
    assert {"idx_org_billing_customer", "idx_org_billing_subscription"} <= indexes
    with connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert "audit_events" in tables
    assert "password_reset_tokens" in tables
    assert "quick_links" in tables
    assert {"load_opportunities", "opportunity_snapshots", "opportunity_negotiations", "driver_locations"} <= tables
    assert {"document_audits", "startup_checklist_progress"} <= tables
    assert user_version == 12
    with connect() as conn:
        payment_columns = {row["name"] for row in conn.execute("PRAGMA table_info(payments)")}
    assert {"voided_at", "voided_by", "void_reason"} <= payment_columns
    with connect() as conn:
        load_columns = {row["name"] for row in conn.execute("PRAGMA table_info(loads)")}
    assert {
        "opportunity_id", "original_offered_rate", "final_agreed_rate",
        "quote_snapshot_id", "booking_snapshot_id", "ratecon_due_at",
        "pickup_address", "pickup_window_start", "pickup_window_end",
        "pickup_contact_name", "pickup_contact_phone", "pickup_instructions",
        "delivery_address", "delivery_window_start", "delivery_window_end",
        "delivery_contact_name", "delivery_contact_phone", "delivery_instructions",
        "ratecon_reference", "ratecon_received_at",
    } <= load_columns
    with connect() as conn:
        onboarding_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(onboarding_applications)")
        }
    assert "expires_at" in onboarding_columns
