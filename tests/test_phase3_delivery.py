from __future__ import annotations

import hashlib
import io
import uuid
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


def test_office_pod_upload_is_attached_to_ratecon_and_tenant_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "ratecon-pod.db"))
    storage = InMemoryObjectStorageProvider()
    monkeypatch.setattr(main_module, "configured_storage_provider", lambda: storage)
    monkeypatch.setattr(
        main_module,
        "configured_malware_scan_provider",
        lambda: MockMalwareScanProvider(),
    )
    with TestClient(app) as alpha, TestClient(app) as beta:
        alpha_org = _signup(alpha, "ratecon-pod-alpha@example.com", "RateCon POD Alpha")
        load = _book_load(alpha, alpha_org)
        ratecon_payload = _pdf()
        ratecon_uuid = str(uuid.uuid4())
        ratecon_key = f"organizations/{alpha_org}/ratecons/{ratecon_uuid}.pdf"
        storage.put(ratecon_key, ratecon_payload, content_type="application/pdf")
        with db_session() as conn:
            ratecon_id = int(
                conn.execute(
                    """INSERT INTO operational_documents
                    (public_uuid,organization_id,load_id,document_type,storage_key,storage_provider,
                     original_filename,content_type,size_bytes,page_count,sha256,malware_status,
                     processing_status,retention_date,created_by)
                    VALUES (?,?,?,'RATECON',?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        ratecon_uuid,
                        alpha_org,
                        load["id"],
                        ratecon_key,
                        storage.name,
                        "signed-ratecon.pdf",
                        "application/pdf",
                        len(ratecon_payload),
                        1,
                        hashlib.sha256(ratecon_payload).hexdigest(),
                        "CLEAN",
                        "REVIEWED",
                        main_module.default_retention_date(),
                        query_one("SELECT id FROM users WHERE organization_id=?", (alpha_org,))["id"],
                    ),
                ).lastrowid
            )
        assert ratecon_id
        detail = alpha.get(f"/ratecons/{ratecon_uuid}")
        assert detail.status_code == 200
        assert "Proof of delivery" in detail.text
        assert "No proof of delivery has been attached yet" in detail.text

        pod_payload = _pdf()
        uploaded = alpha.post(
            f"/ratecons/{ratecon_uuid}/pod",
            data={"notes": "Signed by consignee"},
            files={"pod": ("signed-pod.pdf", pod_payload, "application/pdf")},
            follow_redirects=False,
        )
        assert uploaded.status_code == 303
        assert uploaded.headers["location"] == f"/ratecons/{ratecon_uuid}"
        link = query_one(
            "SELECT * FROM delivery_document_links WHERE organization_id=? AND load_id=? AND document_kind='POD'",
            (alpha_org, load["id"]),
        )
        assert link["source"] == "office"
        assert link["notes"] == "Signed by consignee"
        pod = query_one("SELECT * FROM operational_documents WHERE id=?", (link["document_id"],))
        assert pod["document_type"] == "POD"
        assert pod["malware_status"] == "CLEAN"
        assert storage.get(pod["storage_key"]) == pod_payload

        refreshed = alpha.get(f"/ratecons/{ratecon_uuid}")
        assert "signed-pod.pdf" in refreshed.text
        assert "Download POD" in refreshed.text
        downloaded = alpha.get(f"/documents/{pod['public_uuid']}/download")
        assert downloaded.status_code == 200
        assert downloaded.content == pod_payload
        assert downloaded.headers["content-disposition"].endswith("signed-pod.pdf")

        beta_org = _signup(beta, "ratecon-pod-beta@example.com", "RateCon POD Beta")
        assert beta_org != alpha_org
        assert beta.get(f"/ratecons/{ratecon_uuid}").status_code == 404
        assert beta.post(
            f"/ratecons/{ratecon_uuid}/pod",
            files={"pod": ("cross-tenant.pdf", pod_payload, "application/pdf")},
        ).status_code == 404
        assert beta.get(f"/documents/{pod['public_uuid']}/download").status_code == 404
