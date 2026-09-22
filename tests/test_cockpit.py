from __future__ import annotations

from datetime import date, timedelta
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
    yield
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()


def signup(client: TestClient) -> int:
    response = client.post(
        "/signup",
        data={
            "full_name": "Fleet Owner",
            "company_name": "Cockpit Carrier",
            "email": "cockpit@example.com",
            "password": "StrongPassword!42",
            "plan": "free_operator",
            "accepted_terms": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    user = query_one("SELECT organization_id FROM users WHERE email='cockpit@example.com'")
    with db_session() as conn:
        conn.execute(
            "UPDATE organizations SET subscription_status='active' WHERE id=?",
            (user["organization_id"],),
        )
    return int(user["organization_id"])


def test_ceo_cockpit_turns_load_file_controls_into_live_decisions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "cockpit.db"))
    today = date.today()
    old_delivery = today - timedelta(days=50)
    recent_delivery = today - timedelta(days=3)

    with TestClient(app) as client:
        organization_id = signup(client)
        with db_session() as conn:
            conn.execute(
                """UPDATE organizations
                SET fallback_diesel_price=0,cash_balance_today=5000,cash_floor=10000,
                    ar_collection_rate_pct=80,planned_fixed_cost_change_date=?,
                    planned_fixed_cost_change_monthly=750
                WHERE id=?""",
                ((today + timedelta(days=30)).isoformat(), organization_id),
            )
            vehicle_id = conn.execute(
                "INSERT INTO vehicles (organization_id,name,equipment_type,active) VALUES (?,?,?,1)",
                (organization_id, "Unit 12", "Box Truck"),
            ).lastrowid
            driver_id = conn.execute(
                """INSERT INTO drivers
                (organization_id,vehicle_id,name,role,pay_model,flat_rate_per_load,
                 truck_financing_monthly,auto_insurance_monthly,mpg,maintenance_per_mile,active)
                VALUES (?,?,?,?,?,?,?,?,?,?,1)""",
                (organization_id, vehicle_id, "Casey Driver", "Driver", "Flat Rate per Load", 300, 900, 400, 10, 0.10),
            ).lastrowid
            invoiced_load_id = conn.execute(
                """INSERT INTO loads
                (organization_id,load_number,pickup_date,delivery_date,driver_id,vehicle_id,
                 broker,origin,destination,status,status_code,revenue,loaded_miles,deadhead_miles)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    organization_id, "FRT-2101", (old_delivery - timedelta(days=1)).isoformat(),
                    old_delivery.isoformat(), driver_id, vehicle_id, "Total Quality Logistics",
                    "Nashville, TN", "Atlanta, GA", "Invoiced", "INVOICED", 2200, 250, 20,
                ),
            ).lastrowid
            conn.execute(
                """INSERT INTO loads
                (organization_id,load_number,pickup_date,delivery_date,driver_id,vehicle_id,
                 broker,origin,destination,status,status_code,revenue,loaded_miles,deadhead_miles)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    organization_id, "FRT-2102", (recent_delivery - timedelta(days=1)).isoformat(),
                    recent_delivery.isoformat(), driver_id, vehicle_id, "TQL",
                    "Memphis, TN", "Dallas, TX", "Delivered", "READY_TO_INVOICE", 1800, 400, 35,
                ),
            )
            conn.execute(
                """INSERT INTO invoices
                (organization_id,invoice_number,customer,load_id,amount,invoice_date,due_date,status)
                VALUES (?,?,?,?,?,?,?,'Unpaid')""",
                (
                    organization_id, "INV-2101", "Total Quality Logistics", invoiced_load_id,
                    2200, old_delivery.isoformat(), (old_delivery + timedelta(days=30)).isoformat(),
                ),
            )

        response = client.get(f"/cockpit?as_of={today.isoformat()}")
        assert response.status_code == 200
        assert "CEO cockpit" in response.text
        assert "Weekly break-even" in response.text
        assert "Cash outlook" in response.text
        assert "Invoice delivered loads" in response.text
        assert "Collect aging receivables" in response.text
        assert "Broker scorecard" in response.text
        assert "Driver scorecard" in response.text
        assert "Unit profitability" in response.text
        assert "Total Quality Logistics" in response.text
        assert "Possible broker naming duplicates" in response.text
        assert "$2,200.00" in response.text
        assert "$1,800.00" in response.text
        assert "Planned fixed-cost scenario" in response.text
        assert 'href="/cockpit"' in response.text


def test_cockpit_cash_settings_are_saved_without_changing_load_math(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "cockpit-settings.db"))
    with TestClient(app) as client:
        organization_id = signup(client)
        settings = query_one("SELECT * FROM organizations WHERE id=?", (organization_id,))
        response = client.post(
            "/settings",
            data={
                **dict(settings),
                "cash_balance_today": "12500.50",
                "cash_floor": "9000",
                "ar_collection_rate_pct": "75",
                "planned_fixed_cost_change_date": "2027-01-01",
                "planned_fixed_cost_change_monthly": "625",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        saved = query_one("SELECT * FROM organizations WHERE id=?", (organization_id,))
        assert saved["cash_balance_today"] == pytest.approx(12500.50)
        assert saved["cash_floor"] == pytest.approx(9000)
        assert saved["ar_collection_rate_pct"] == pytest.approx(75)
        assert saved["planned_fixed_cost_change_date"] == "2027-01-01"
        assert saved["planned_fixed_cost_change_monthly"] == pytest.approx(625)
