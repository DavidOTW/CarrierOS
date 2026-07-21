from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import db_session, query_one
from app import main as main_module
from app.main import app
from app.services import get_state


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()
    yield
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()


def signup(client: TestClient, email: str, company: str = "Editing Fleet") -> int:
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


def create_operating_records(client: TestClient) -> tuple[int, int, int]:
    assert client.post(
        "/vehicles",
        data={"name": "Truck 1", "equipment_type": "Tractor", "active": "on"},
    ).status_code == 200
    vehicle_id = int(query_one("SELECT id FROM vehicles WHERE name='Truck 1'")["id"])
    assert client.post(
        "/drivers",
        data={
            "name": "Casey Driver",
            "role": "Driver",
            "pay_model": "Flat Rate per Load",
            "vehicle_id": str(vehicle_id),
            "flat_rate_per_load": "500",
            "mpg": "10",
            "maintenance_per_mile": "0.20",
            "active": "on",
        },
        follow_redirects=False,
    ).status_code == 303
    driver_id = int(query_one("SELECT id FROM drivers WHERE name='Casey Driver'")["id"])
    assert client.post(
        "/loads/new",
        data={
            "load_number": "EDIT-101",
            "status": "Delivered",
            "include_in_model": "on",
            "pickup_date": date.today().isoformat(),
            "delivery_date": date.today().isoformat(),
            "driver_id": str(driver_id),
            "vehicle_id": str(vehicle_id),
            "revenue": "2500",
            "loaded_miles": "500",
            "deadhead_miles": "50",
        },
        follow_redirects=False,
    ).status_code == 303
    load_id = int(query_one("SELECT id FROM loads WHERE load_number='EDIT-101'")["id"])
    return vehicle_id, driver_id, load_id


def test_load_cancellation_and_payment_corrections_recalculate_balances(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "editing.db"))
    with TestClient(app) as client:
        organization_id = signup(client, "editing@example.com")
        _, driver_id, load_id = create_operating_records(client)
        created = client.post(
            "/payments",
            data={
                "driver_id": str(driver_id),
                "load_id": str(load_id),
                "paid_at": date.today().isoformat(),
                "payment_type": "Regular payout",
                "amount": "100",
                "method": "ACH",
                "counts_against_load_pay": "on",
                "include_in_reports": "on",
            },
            follow_redirects=False,
        )
        assert created.status_code == 303
        payment_id = int(query_one("SELECT id FROM payments")["id"])

        edited = client.post(
            f"/payments/{payment_id}/edit",
            data={
                "driver_id": str(driver_id),
                "load_id": str(load_id),
                "paid_at": date.today().isoformat(),
                "payment_type": "Regular payout",
                "amount": "125",
                "method": "ACH",
                "counts_against_load_pay": "on",
                "include_in_reports": "on",
            },
            follow_redirects=False,
        )
        assert edited.status_code == 303
        assert query_one("SELECT amount FROM payments WHERE id=?", (payment_id,))["amount"] == pytest.approx(125)
        _, state = get_state(organization_id)
        assert state["driver_balances"][0]["payments_applied"] == pytest.approx(125)

        voided = client.post(
            f"/payments/{payment_id}/void",
            data={"void_reason": "Duplicate payment"},
            follow_redirects=False,
        )
        assert voided.status_code == 303
        assert query_one("SELECT voided_at FROM payments WHERE id=?", (payment_id,))["voided_at"]
        _, state = get_state(organization_id)
        assert state["driver_balances"][0]["payments_applied"] == pytest.approx(0)
        assert "Voided" in client.get("/payments").text

        cancelled = client.post(f"/loads/{load_id}/cancel", follow_redirects=False)
        assert cancelled.status_code == 303
        load = query_one("SELECT status,include_in_model FROM loads WHERE id=?", (load_id,))
        assert load["status"] == "Cancelled"
        assert load["include_in_model"] == 0
        _, state = get_state(organization_id)
        assert state["summary"]["included_loads"] == 0


def test_other_operating_records_can_be_corrected_and_are_tenant_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "other-editing.db"))
    with TestClient(app) as client_a:
        signup(client_a, "alpha-edit@example.com", "Alpha Fleet")
        vehicle_id, driver_id, _ = create_operating_records(client_a)
        assert client_a.post(
            f"/vehicles/{vehicle_id}/update",
            data={"name": "Truck 1A", "equipment_type": "Box Truck", "active": "on"},
            follow_redirects=False,
        ).status_code == 303
        vehicle = query_one("SELECT * FROM vehicles WHERE id=?", (vehicle_id,))
        assert vehicle["name"] == "Truck 1A"
        assert vehicle["equipment_type"] == "Box Truck"

        assert client_a.post(
            "/fuel",
            data={
                "week_start": date.today().isoformat(),
                "average_price": "3.50",
                "source_notes": "Fuel card",
                "entered_by": "Owner",
            },
        ).status_code == 200
        fuel_id = int(query_one("SELECT id FROM weekly_fuel")["id"])
        assert "Fuel card" in client_a.get(f"/fuel?edit_id={fuel_id}").text

        assert client_a.post(
            "/idle",
            data={
                "driver_id": str(driver_id),
                "vehicle_id": str(vehicle_id),
                "start_date": date.today().isoformat(),
                "end_date": date.today().isoformat(),
                "situation": "Company Responsibility",
                "include_in_model": "on",
                "notes": "Initial",
            },
        ).status_code == 200
        idle_id = int(query_one("SELECT id FROM idle_periods")["id"])
        assert client_a.post(
            f"/idle/{idle_id}/edit",
            data={
                "driver_id": str(driver_id),
                "vehicle_id": str(vehicle_id),
                "start_date": date.today().isoformat(),
                "end_date": date.today().isoformat(),
                "situation": "Company Responsibility",
                "notes": "Corrected",
            },
            follow_redirects=False,
        ).status_code == 303
        assert query_one("SELECT notes,include_in_model FROM idle_periods WHERE id=?", (idle_id,))["notes"] == "Corrected"

        assert client_a.post(
            "/compliance",
            data={
                "subject_type": "Vehicle",
                "subject_id": str(vehicle_id),
                "subject_name": "Truck 1A",
                "document_type": "Inspection",
                "expiration_date": "2027-01-01",
            },
        ).status_code == 200
        item_id = int(query_one("SELECT id FROM compliance_items")["id"])
        assert client_a.post(
            f"/compliance/{item_id}/edit",
            data={
                "subject_type": "Vehicle",
                "subject_id": str(vehicle_id),
                "subject_name": "Truck 1A",
                "document_type": "Annual inspection",
                "expiration_date": "2027-02-01",
            },
            follow_redirects=False,
        ).status_code == 303
        assert query_one("SELECT document_type FROM compliance_items WHERE id=?", (item_id,))["document_type"] == "Annual inspection"

    with TestClient(app) as client_b:
        main_module.signup_attempts.clear()
        signup(client_b, "beta-edit@example.com", "Beta Fleet")
        assert client_b.post(
            f"/vehicles/{vehicle_id}/update",
            data={"name": "Stolen", "equipment_type": "Truck", "active": "on"},
            follow_redirects=False,
        ).status_code == 404
        assert client_b.post(f"/idle/{idle_id}/edit", data={}, follow_redirects=False).status_code == 404
        assert client_b.post(f"/compliance/{item_id}/delete", follow_redirects=False).status_code == 404
