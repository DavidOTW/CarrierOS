from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import main as main_module
from app.db import db_session, query_one
from app.main import app
from app.ratecons import (
    ExtractedField,
    InMemoryObjectStorageProvider,
    MockDocumentExtractionProvider,
    MockMalwareScanProvider,
    MockOcrProvider,
    RateConError,
    compare_ratecon_to_booking,
    suggest_ratecon_matches,
    validate_ratecon_upload,
)


def _pdf() -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def _signup(client: TestClient, email: str, company: str) -> int:
    main_module.signup_attempts.clear()
    response = client.post(
        "/signup",
        data={
            "full_name": "Fleet Owner",
            "company_name": company,
            "email": email,
            "password": "StrongPassword!42",
            "plan": "owner_operator",
            "accepted_terms": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    user = query_one("SELECT * FROM users WHERE email=?", (email,))
    with db_session() as conn:
        conn.execute(
            "UPDATE organizations SET subscription_status='active' WHERE id=?",
            (user["organization_id"],),
        )
    return int(user["organization_id"])


def _book_load(client: TestClient, organization_id: int) -> dict:
    assert client.post(
        "/vehicles",
        data={"name": "Truck 1", "equipment_type": "Tractor", "active": "on"},
        follow_redirects=False,
    ).status_code == 303
    vehicle = query_one("SELECT * FROM vehicles WHERE organization_id=?", (organization_id,))
    assert client.post(
        "/trailers",
        data={"unit_number": "VAN-101", "trailer_type": "Dry Van", "active": "on"},
        follow_redirects=False,
    ).status_code == 303
    assert client.post(
        "/drivers",
        data={
            "name": "Alex Driver",
            "phone": "6155550199",
            "role": "Driver",
            "pay_model": "Flat Rate per Load",
            "vehicle_id": str(vehicle["id"]),
            "flat_rate_per_load": "300",
            "mpg": "10",
            "maintenance_per_mile": "0.20",
            "active": "on",
        },
        follow_redirects=False,
    ).status_code == 303
    driver = query_one("SELECT * FROM drivers WHERE organization_id=?", (organization_id,))
    assert client.post(
        f"/drivers/{driver['id']}/location",
        data={
            "city": "Memphis",
            "state": "TN",
            "postal_code": "38103",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "return_to": "/drivers",
        },
        follow_redirects=False,
    ).status_code == 303
    assert client.post(
        "/rate-quotes/new",
        data={
            "broker_customer": "Sample Broker",
            "original_offered_rate": "2200",
            "origin_city": "Memphis",
            "origin_state": "TN",
            "origin_postal_code": "38103",
            "destination_city": "Atlanta",
            "destination_state": "GA",
            "destination_postal_code": "30303",
            "pickup_at": "2026-07-22T08:00",
            "delivery_at": "2026-07-23T17:00",
            "loaded_miles": "500",
            "deadhead_miles": "50",
            "selected_driver_id": str(driver["id"]),
            "equipment_type": "Dry Van",
            "tolls": "20",
            "mileage_source": "manual",
        },
        follow_redirects=False,
    ).status_code == 303
    quote = query_one("SELECT * FROM load_opportunities WHERE organization_id=?", (organization_id,))
    booked = client.post(
        f"/rate-quotes/{quote['id']}/book",
        data={"final_agreed_rate": "2250"},
        follow_redirects=False,
    )
    assert booked.status_code == 303
    return dict(query_one("SELECT * FROM loads WHERE opportunity_id=?", (quote["id"],)))


def test_upload_validation_checks_signature_type_size_and_pages() -> None:
    valid = validate_ratecon_upload(
        _pdf(), filename="ratecon.pdf", claimed_content_type="application/pdf"
    )
    assert valid.media_type == "application/pdf"
    assert valid.page_count == 1
    with pytest.raises(RateConError, match="do not match"):
        validate_ratecon_upload(
            _pdf(), filename="photo.jpg", claimed_content_type="image/jpeg"
        )
    with pytest.raises(RateConError, match="valid PDF"):
        validate_ratecon_upload(
            b"not a document", filename="ratecon.pdf", claimed_content_type="application/pdf"
        )


def test_matching_and_material_difference_classification() -> None:
    load = {
        "id": 7,
        "public_uuid": "load-seven",
        "load_number": "CO-2026-00007",
        "broker": "Sample Broker",
        "pickup_date": "2026-07-22",
        "delivery_date": "2026-07-23",
        "final_agreed_rate": "2250.00",
    }
    fields = [
        ExtractedField("load_number", "CO-2026-00007", 0.98, 1, "Load # CO-2026-00007"),
        ExtractedField("total_rate", "2150.00", 0.99, 1, "Total rate $2,150.00"),
        ExtractedField("delivery_date", "2026-07-24", 0.95, 2, "Deliver 07/24/2026"),
        ExtractedField("added_stop", "Second pickup added", 0.9, 2, "Additional pickup"),
        ExtractedField("tracking_penalty", "$100 deduction", 0.9, 2, "Tracking penalty $100"),
    ]
    matches = suggest_ratecon_matches([load], {field.name: field.value for field in fields})
    assert matches[0].load_id == 7 and matches[0].score >= 50
    differences = compare_ratecon_to_booking(load, fields)
    by_name = {item.field_name: item for item in differences}
    assert by_name["total_rate"].classification == "FINANCIAL_DIFFERENCE"
    assert by_name["total_rate"].financial_impact_cents == -10000
    assert by_name["delivery_date"].classification == "OPERATIONAL_CONFLICT"
    assert by_name["added_stop"].material is True
    assert by_name["tracking_penalty"].material is True


def test_ratecon_to_dispatch_to_driver_ack_is_tenant_scoped_and_retry_safe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "phase2.db"))
    storage = InMemoryObjectStorageProvider()
    monkeypatch.setattr(main_module, "configured_storage_provider", lambda: storage)
    monkeypatch.setattr(main_module, "configured_malware_scan_provider", lambda: MockMalwareScanProvider())
    monkeypatch.setattr(main_module, "configured_ocr_provider", lambda: MockOcrProvider("scanned fixture"))
    with TestClient(app) as alpha, TestClient(app) as beta:
        alpha_org = _signup(alpha, "phase2-alpha@example.com", "Phase 2 Alpha")
        load = _book_load(alpha, alpha_org)
        fields = (
            ExtractedField("broker_customer", "Sample Broker", 0.98, 1, "Broker: Sample Broker"),
            ExtractedField("load_number", load["load_number"], 0.99, 1, f"Load: {load['load_number']}"),
            ExtractedField("total_rate", "2250.00", 0.99, 1, "Total rate $2,250.00"),
            ExtractedField("pickup_date", "2026-07-22", 0.97, 1, "Pickup 07/22/2026"),
            ExtractedField("delivery_date", "2026-07-24", 0.97, 2, "Delivery 07/24/2026"),
            ExtractedField("added_stop", "Second pickup added", 0.92, 2, "Additional stop"),
            ExtractedField("tracking_penalty", "$100 deduction", 0.91, 2, "Tracking penalty"),
            ExtractedField("pickup_address", "100 Freight Way, Memphis, TN 38103", 0.95, 1, "Pickup address"),
            ExtractedField("pickup_window_start", "2026-07-22T08:00", 0.95, 1, "Pickup start"),
            ExtractedField("pickup_window_end", "2026-07-22T10:00", 0.95, 1, "Pickup end"),
            ExtractedField("pickup_timezone", "America/Chicago", 0.95, 1, "Pickup time zone"),
            ExtractedField("delivery_address", "200 Logistics Blvd, Atlanta, GA 30303", 0.95, 2, "Delivery address"),
            ExtractedField("delivery_window_start", "2026-07-24T09:00", 0.95, 2, "Delivery start"),
            ExtractedField("delivery_window_end", "2026-07-24T11:00", 0.95, 2, "Delivery end"),
            ExtractedField("delivery_timezone", "America/New_York", 0.95, 2, "Delivery time zone"),
        )
        monkeypatch.setattr(
            main_module,
            "configured_extraction_provider",
            lambda: MockDocumentExtractionProvider(fields),
        )
        uploaded = alpha.post(
            "/ratecons/upload",
            data={"load_public_uuid": load["public_uuid"]},
            files={"ratecon": ("sample-ratecon.pdf", _pdf(), "application/pdf")},
            follow_redirects=False,
        )
        assert uploaded.status_code == 303
        document = query_one("SELECT * FROM operational_documents WHERE organization_id=?", (alpha_org,))
        assert document["storage_key"].startswith(f"organizations/{alpha_org}/ratecons/")
        assert document["malware_status"] == "CLEAN"
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "RATECON_REVIEW"
        difference_names = {
            row["field_name"]
            for row in main_module.query_all("SELECT field_name FROM ratecon_differences WHERE document_id=?", (document["id"],))
        }
        assert {"delivery_date", "added_stop", "tracking_penalty"} <= difference_names

        beta_org = _signup(beta, "phase2-beta@example.com", "Phase 2 Beta")
        assert beta_org != alpha_org
        assert beta.get(f"/ratecons/{document['public_uuid']}").status_code == 404

        approved = alpha.post(
            f"/ratecons/{document['public_uuid']}/approve",
            data={"approve_material": "on"},
            follow_redirects=False,
        )
        assert approved.status_code == 303
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "NEEDS_ASSIGNMENT"

        dispatch_page = alpha.get(approved.headers["location"])
        assert dispatch_page.status_code == 200
        assert "Schedule estimate only" in dispatch_page.text
        driver = query_one("SELECT * FROM drivers WHERE organization_id=?", (alpha_org,))
        power_unit = query_one("SELECT * FROM power_units WHERE organization_id=?", (alpha_org,))
        trailer = query_one("SELECT * FROM trailers WHERE organization_id=?", (alpha_org,))
        assigned = alpha.post(
            f"/loads/{load['public_uuid']}/dispatch/assign",
            data={
                "driver_id": str(driver["id"]),
                "power_unit_id": str(power_unit["id"]),
                "trailer_id": str(trailer["id"]),
            },
            follow_redirects=False,
        )
        assert assigned.status_code == 303
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "DISPATCH_AWAITING_APPROVAL"
        final_approval = alpha.post(
            f"/loads/{load['public_uuid']}/dispatch/approve",
            follow_redirects=False,
        )
        assert final_approval.status_code == 303
        approval = query_one("SELECT * FROM dispatch_approvals WHERE load_id=?", (load["id"],))
        token = main_module._dispatch_token(approval["public_uuid"])
        driver_page = alpha.get(f"/driver/dispatch/{token}")
        assert driver_page.status_code == 200
        assert "Company profit" not in driver_page.text
        acknowledged = alpha.post(
            f"/driver/dispatch/{token}/ack",
            data={"note": "Reviewed while parked"},
        )
        assert acknowledged.status_code == 200
        assert "Dispatch acknowledged" in acknowledged.text
        assert query_one("SELECT status_code FROM loads WHERE id=?", (load["id"],))["status_code"] == "DISPATCH_ACKNOWLEDGED"
        replay = alpha.post(f"/driver/dispatch/{token}/ack", data={"note": "retry"})
        assert replay.status_code == 200
        assert query_one(
            "SELECT COUNT(*) AS total FROM load_status_history WHERE load_id=? AND new_status='DISPATCH_ACKNOWLEDGED'",
            (load["id"],),
        )["total"] == 1
