from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import db_session, query_one
from app.main import app
from tests.test_phase2_ratecon_dispatch import _book_load, _signup


def _mark_delivered(organization_id: int, load_id: int) -> None:
    with db_session() as conn:
        conn.execute(
            """UPDATE loads SET status_code='DELIVERED_DOCUMENTS_PENDING',status='Delivered - documents pending',
            delivery_date='2026-07-23',revenue=2250 WHERE id=? AND organization_id=?""",
            (load_id, organization_id),
        )


def test_delivery_to_cash_invoice_receipts_and_load_state_are_audited_and_tenant_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "phase4.db"))
    with TestClient(app) as alpha, TestClient(app) as beta:
        alpha_org = _signup(alpha, "phase4-alpha@example.com", "Phase 4 Alpha")
        load = _book_load(alpha, alpha_org)
        _mark_delivered(alpha_org, int(load["id"]))

        ready = alpha.get("/receivables")
        assert ready.status_code == 200
        assert "Ready to invoice" in ready.text
        created = alpha.post(
            f"/invoices/from-load/{load['id']}",
            data={"due_date": "2026-08-22"},
            follow_redirects=False,
        )
        assert created.status_code == 303
        invoice = query_one("SELECT * FROM invoices WHERE organization_id=?", (alpha_org,))
        assert invoice and invoice["status"] == "Unpaid"
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "INVOICED"

        partial = alpha.post(
            f"/invoices/{invoice['id']}/payment",
            data={"amount": "1000", "paid_date": "2026-07-24", "payment_reference": "ACH-1", "idempotency_key": "receipt-1"},
            follow_redirects=False,
        )
        assert partial.status_code == 303
        assert query_one("SELECT status FROM invoices WHERE id=?", (invoice["id"],))["status"] == "Partially Paid"
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "PARTIALLY_PAID"

        replay = alpha.post(
            f"/invoices/{invoice['id']}/payment",
            data={"amount": "1000", "paid_date": "2026-07-24", "payment_reference": "ACH-1", "idempotency_key": "receipt-1"},
            follow_redirects=False,
        )
        assert replay.status_code == 303
        assert query_one("SELECT COUNT(*) AS total FROM invoice_payments WHERE invoice_id=?", (invoice["id"],))["total"] == 1

        final = alpha.post(
            f"/invoices/{invoice['id']}/payment",
            data={"amount": "1250", "paid_date": "2026-07-25", "payment_reference": "ACH-2", "idempotency_key": "receipt-2"},
            follow_redirects=False,
        )
        assert final.status_code == 303
        assert query_one("SELECT status FROM invoices WHERE id=?", (invoice["id"],))["status"] == "Paid"
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "PAID"
        aging = alpha.get("/receivables")
        assert "Paid" in aging.text
        assert query_one(
            "SELECT COUNT(*) AS total FROM audit_events WHERE organization_id=? AND event_type='invoice.payment_recorded'",
            (alpha_org,),
        )["total"] == 2

        beta_org = _signup(beta, "phase4-beta@example.com", "Phase 4 Beta")
        assert beta_org != alpha_org
        assert beta.post(f"/invoices/{invoice['id']}/payment", data={"amount": "1"}).status_code == 404
