from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import main as main_module
from app.db import db_session, query_one
from app.main import app
from app.ratecons import InMemoryObjectStorageProvider, MockMalwareScanProvider
from tests.test_phase2_ratecon_dispatch import _book_load, _signup


def _pdf() -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def _dispatch_ready_load(organization_id: int, load_id: int) -> dict:
    driver = query_one("SELECT * FROM drivers WHERE organization_id=?", (organization_id,))
    power_unit = query_one("SELECT * FROM power_units WHERE organization_id=?", (organization_id,))
    trailer = query_one("SELECT * FROM trailers WHERE organization_id=?", (organization_id,))
    assert driver and power_unit and trailer
    with db_session() as conn:
        assignment_id = int(
            conn.execute(
                """INSERT INTO load_assignments
                (public_uuid,organization_id,load_id,driver_id,power_unit_id,trailer_id,
                 assignment_stage,provisional,approved_by,approved_at)
                VALUES (?,?,?,?,?,?, 'RATECON_APPROVED',0,NULL,CURRENT_TIMESTAMP)""",
                (
                    "assignment-phase3",
                    organization_id,
                    load_id,
                    driver["id"],
                    power_unit["id"],
                    trailer["id"],
                ),
            ).lastrowid
        )
        approval_id = int(
            conn.execute(
                """INSERT INTO dispatch_approvals
                (public_uuid,organization_id,load_id,load_assignment_id,status,
                 approved_at,acknowledged_at)
                VALUES (?,?,?,?, 'ACKNOWLEDGED',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""",
                ("approval-phase3", organization_id, load_id, assignment_id),
            ).lastrowid
        )
        conn.execute(
            """UPDATE loads SET status_code='DISPATCH_ACKNOWLEDGED',
            status='Dispatch Acknowledged', ratecon_received_at=CURRENT_TIMESTAMP,
            ratecon_reference='RC-PHASE3', pickup_address='100 Freight Way, Memphis, TN 38103',
            pickup_window_start='2026-07-22T08:00', pickup_window_end='2026-07-22T10:00',
            pickup_timezone='America/Chicago', delivery_address='200 Logistics Blvd, Atlanta, GA 30303',
            delivery_window_start='2026-07-24T09:00', delivery_window_end='2026-07-24T11:00',
            delivery_timezone='America/New_York' WHERE id=? AND organization_id=?""",
            (load_id, organization_id),
        )
    return dict(query_one("SELECT * FROM dispatch_approvals WHERE id=?", (approval_id,)))


def test_driver_delivery_status_and_documents_are_retry_safe_and_private(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "phase3.db"))
    storage = InMemoryObjectStorageProvider()
    monkeypatch.setattr(main_module, "configured_storage_provider", lambda: storage)
    monkeypatch.setattr(
        main_module,
        "configured_malware_scan_provider",
        lambda: MockMalwareScanProvider(),
    )
    with TestClient(app) as client:
        organization_id = _signup(client, "phase3-delivery@example.com", "Phase 3 Delivery")
        load = _book_load(client, organization_id)
        approval = _dispatch_ready_load(organization_id, int(load["id"]))
        token = main_module._dispatch_token(approval["public_uuid"])

        page = client.get(f"/driver/dispatch/{token}")
        assert page.status_code == 200
        assert "Live trip status" in page.text
        assert "Delivery documents" in page.text

        status = client.post(
            f"/driver/dispatch/{token}/status",
            data={
                "status": "AT_PICKUP",
                "idempotency_key": "pickup-1",
                "reason": "Arrived and checked in",
            },
        )
        assert status.status_code == 200
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "AT_PICKUP"
        replay = client.post(
            f"/driver/dispatch/{token}/status",
            data={"status": "AT_PICKUP", "idempotency_key": "pickup-1"},
        )
        assert replay.status_code == 200
        assert query_one(
            """SELECT COUNT(*) AS total FROM load_status_history
            WHERE load_id=? AND new_status='AT_PICKUP'""",
            (load["id"],),
        )["total"] == 1
        invalid = client.post(
            f"/driver/dispatch/{token}/status",
            data={"status": "AT_DELIVERY", "idempotency_key": "skip-delivery"},
        )
        assert invalid.status_code == 409
        office = client.post(
            f"/loads/{load['public_uuid']}/status",
            data={
                "status": "IN_TRANSIT",
                "idempotency_key": "office-transit-1",
                "reason": "Dispatcher confirmed departure",
            },
            follow_redirects=False,
        )
        assert office.status_code == 303
        assert office.headers["location"] == f"/loads/{load['id']}"
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "IN_TRANSIT"

        bol_payload = _pdf()
        uploaded = client.post(
            f"/driver/dispatch/{token}/documents",
            data={"document_kind": "BOL", "notes": "Signed at pickup"},
            files={"document": ("signed-bol.pdf", bol_payload, "application/pdf")},
        )
        assert uploaded.status_code == 200
        link = query_one(
            "SELECT * FROM delivery_document_links WHERE organization_id=? AND load_id=?",
            (organization_id, load["id"]),
        )
        assert link["document_kind"] == "BOL"
        document = query_one("SELECT * FROM operational_documents WHERE id=?", (link["document_id"],))
        assert document["malware_status"] == "CLEAN"
        assert storage.get(document["storage_key"]) == bol_payload
