from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.db import db_session, query_one
from app.main import app


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()
    yield
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()


def signup(client: TestClient) -> None:
    response = client.post(
        "/signup",
        data={
            "full_name": "Fleet Owner",
            "company_name": "Reporting Fleet",
            "email": "reporting@example.com",
            "password": "StrongPassword!42",
            "plan": "owner_operator",
            "accepted_terms": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    user = query_one("SELECT organization_id FROM users WHERE email='reporting@example.com'")
    with db_session() as conn:
        conn.execute(
            "UPDATE organizations SET subscription_status='active',owner_distribution_pct=25 WHERE id=?",
            (user["organization_id"],),
        )


def create_driver(client: TestClient, name: str, vehicle_id: int) -> int:
    response = client.post(
        "/drivers",
        data={
            "name": name,
            "role": "Driver",
            "pay_model": "Flat Rate per Load",
            "vehicle_id": str(vehicle_id),
            "flat_rate_per_load": "200",
            "mpg": "10",
            "maintenance_per_mile": "0.20",
            "active": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(query_one("SELECT id FROM drivers WHERE name=?", (name,))["id"])


def create_load(
    client: TestClient,
    *,
    number: str,
    driver_id: int,
    vehicle_id: int,
    pickup: str,
    delivery: str,
    revenue: str,
    broker: str = "Broker",
) -> int:
    response = client.post(
        "/loads/new",
        data={
            "load_number": number,
            "status": "Delivered",
            "include_in_model": "on",
            "pickup_date": pickup,
            "delivery_date": delivery,
            "driver_id": str(driver_id),
            "vehicle_id": str(vehicle_id),
            "broker": broker,
            "origin": "Nashville, TN",
            "destination": "Atlanta, GA",
            "revenue": revenue,
            "loaded_miles": "250",
            "deadhead_miles": "25",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(query_one("SELECT id FROM loads WHERE load_number=?", (number,))["id"])


def test_load_ledger_filters_dates_drivers_specific_loads_and_sorting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "reporting.db"))
    with TestClient(app) as client:
        signup(client)
        assert client.post(
            "/vehicles", data={"name": "Truck 1", "equipment_type": "Tractor", "active": "on"}
        ).status_code == 200
        vehicle_id = int(query_one("SELECT id FROM vehicles WHERE name='Truck 1'")["id"])
        alice_id = create_driver(client, "Alice Driver", vehicle_id)
        bob_id = create_driver(client, "Bob Driver", vehicle_id)
        first_id = create_load(
            client,
            number="ALPHA-100",
            driver_id=alice_id,
            vehicle_id=vehicle_id,
            pickup="2026-06-01",
            delivery="2026-06-03",
            revenue="1500",
            broker="=NOT_A_FORMULA",
        )
        create_load(
            client,
            number="BETA-200",
            driver_id=bob_id,
            vehicle_id=vehicle_id,
            pickup="2026-07-10",
            delivery="2026-07-12",
            revenue="2500",
        )

        page = client.get(f"/loads?driver_id={alice_id}")
        assert page.status_code == 200
        ledger = page.text.split("Selected load ledger", 1)[1]
        assert "ALPHA-100" in ledger
        assert "BETA-200" not in ledger
        assert "1 load record shown" in page.text

        page = client.get("/loads?date_from=2026-07-01&date_to=2026-07-31")
        ledger = page.text.split("Selected load ledger", 1)[1]
        assert "BETA-200" in ledger
        assert "ALPHA-100" not in ledger

        page = client.get(f"/financials?load_id={first_id}")
        assert page.status_code == 200
        selected_report = page.text.split("Selected results by driver", 1)[1]
        assert "Alice Driver" in selected_report
        assert "Bob Driver" not in selected_report
        assert "Owner profit distribution" in page.text

        exported = client.get("/loads/export.csv?sort=driver_asc")
        assert exported.status_code == 200
        assert "attachment;" in exported.headers["content-disposition"]
        csv_text = exported.content.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        assert [row["Driver"] for row in rows] == ["Alice Driver", "Bob Driver"]
        assert rows[0]["Broker"] == "'=NOT_A_FORMULA"


def test_reversed_report_dates_are_normalized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "reversed-dates.db"))
    with TestClient(app) as client:
        signup(client)
        response = client.get("/loads?date_from=2026-07-31&date_to=2026-06-01")
        assert response.status_code == 200
        assert "Dates reordered" in response.text
        assert 'value="2026-06-01"' in response.text
        assert 'value="2026-07-31"' in response.text
