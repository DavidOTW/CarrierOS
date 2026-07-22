from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.db import connect, db_session, query_one
from app.main import app
from app.opportunities import calculate_opportunity, compare_drivers
from app.routing import MockRouteProvider
from app.services import get_state


SETTINGS = {
    "fallback_diesel_price": 4.0,
    "processing_fee_pct": 3,
    "admin_fee_per_load": 5,
    "payroll_burden_pct": 5,
    "target_margin_pct": 10,
    "target_max_deadhead_pct": 20,
    "min_company_profit_per_mile": 0.25,
    "min_total_profit": 200,
    "min_profit_per_day": 100,
    "min_revenue_per_total_mile": 1.75,
    "quote_counteroffer_pct": 5,
    "default_payment_days": 30,
    "location_stale_hours": 24,
    "owner_distribution_pct": 50,
}


def driver(driver_id: int = 1, name: str = "Alex", flat_rate: float = 300) -> dict:
    return {
        "id": driver_id,
        "name": name,
        "vehicle_id": driver_id,
        "pay_model": "Flat Rate per Load",
        "flat_rate_per_load": flat_rate,
        "mpg": 10,
        "maintenance_per_mile": 0.20,
        "truck_financing_monthly": 600,
        "auto_insurance_monthly": 300,
        "trailer_financing_monthly": 0,
        "trailer_insurance_monthly": 0,
        "other_fixed_monthly": 0,
        "payroll_burden_applies": 0,
    }


def opportunity() -> dict:
    return {
        "original_offered_rate": 2200,
        "origin_city": "Memphis",
        "origin_state": "TN",
        "origin_postal_code": "38103",
        "destination_city": "Atlanta",
        "destination_state": "GA",
        "destination_postal_code": "30303",
        "pickup_at": "2026-07-22T08:00",
        "delivery_at": "2026-07-23T17:00",
        "loaded_miles": 500,
        "deadhead_miles": 50,
        "tolls": 20,
        "lumper": 0,
        "misc_expenses": 0,
        "factoring_pct": 1,
        "quick_pay_pct": 0,
    }


def signup(client: TestClient, email: str, company: str) -> int:
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


def operating_profile(client: TestClient) -> tuple[int, int]:
    assert client.post(
        "/vehicles",
        data={"name": "Truck 1", "equipment_type": "Tractor", "active": "on"},
        follow_redirects=False,
    ).status_code == 303
    vehicle_id = int(query_one("SELECT id FROM vehicles WHERE name='Truck 1'")["id"])
    assert client.post(
        "/drivers",
        data={
            "name": "Alex Driver",
            "role": "Driver",
            "pay_model": "Flat Rate per Load",
            "vehicle_id": str(vehicle_id),
            "flat_rate_per_load": "300",
            "mpg": "10",
            "maintenance_per_mile": "0.20",
            "active": "on",
        },
        follow_redirects=False,
    ).status_code == 303
    driver_id = int(query_one("SELECT id FROM drivers WHERE name='Alex Driver'")["id"])
    return vehicle_id, driver_id


def quote_payload(driver_id: int) -> dict[str, str]:
    return {
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
        "selected_driver_id": str(driver_id),
        "equipment_type": "Dry Van",
        "tolls": "20",
        "factoring_pct": "1",
        "mileage_source": "manual",
    }


def test_profit_check_recommendation_and_owner_distribution() -> None:
    result = calculate_opportunity(SETTINGS, driver(), opportunity(), fuel_price=4.0)
    assert result.recommendation == "BOOK"
    assert result.company_profit > 0
    assert result.minimum_acceptable_rate and result.minimum_acceptable_rate < result.offered_revenue
    assert result.opening_counteroffer and result.opening_counteroffer >= result.minimum_acceptable_rate
    assert result.owner_profit_distribution == pytest.approx(result.company_profit * 0.5, abs=0.01)
    assert result.retained_company_profit == pytest.approx(result.company_profit * 0.5, abs=0.01)


def test_driver_comparison_uses_sourced_deadhead_and_flags_stale_location() -> None:
    drivers = [driver(1, "Close", 300), driver(2, "Far", 300)]
    now = datetime.now(timezone.utc)
    locations = {
        1: {"city": "Nashville", "state": "TN", "postal_code": "37201", "observed_at": now.isoformat()},
        2: {"city": "Dallas", "state": "TX", "postal_code": "75201", "observed_at": (now - timedelta(hours=48)).isoformat()},
    }
    provider = MockRouteProvider({
        (("Nashville, TN 37201"), ("Memphis, TN 38103")): 210,
        (("Dallas, TX 75201"), ("Memphis, TN 38103")): 455,
    })
    rows = compare_drivers(SETTINGS, drivers, opportunity(), locations, provider, fuel_price=4.0)
    by_name = {row["driver"]["name"]: row for row in rows}
    assert by_name["Close"]["result"].deadhead_miles == 210
    assert by_name["Close"]["deadhead_source"] == "mock"
    assert any("stale" in warning.lower() for warning in by_name["Far"]["result"].warnings)
    assert by_name["Far"]["result"].recommendation == "REVIEW REQUIRED"


def test_quote_booking_is_single_conversion_immutable_and_tenant_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "opportunities.db"))
    with TestClient(app) as alpha, TestClient(app) as beta:
        alpha_org = signup(alpha, "alpha-quotes@example.com", "Alpha Fleet")
        _, driver_id = operating_profile(alpha)
        alpha.post(
            f"/drivers/{driver_id}/location",
            data={
                "city": "Memphis",
                "state": "TN",
                "postal_code": "38103",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "return_to": "/drivers",
            },
            follow_redirects=False,
        )
        created = alpha.post("/rate-quotes/new", data=quote_payload(driver_id), follow_redirects=False)
        assert created.status_code == 303
        quote = query_one("SELECT * FROM load_opportunities WHERE organization_id=?", (alpha_org,))
        assert created.headers["location"] == f"/rate-quotes/{quote['id']}"
        detail = alpha.get(created.headers["location"])
        assert detail.status_code == 200
        assert "BOOK" in detail.text
        assert "Owner profit distribution" in detail.text

        beta_org = signup(beta, "beta-quotes@example.com", "Beta Fleet")
        assert beta_org != alpha_org
        assert beta.get(f"/rate-quotes/{quote['id']}").status_code == 404

        booked = alpha.post(
            f"/rate-quotes/{quote['id']}/book",
            data={"final_agreed_rate": "2250"},
            follow_redirects=False,
        )
        assert booked.status_code == 303
        load = query_one("SELECT * FROM loads WHERE opportunity_id=?", (quote["id"],))
        assert load["status"] == "Booked — Awaiting RateCon"
        assert load["original_offered_rate"] == pytest.approx(2200)
        assert load["final_agreed_rate"] == pytest.approx(2250)
        assert load["quote_snapshot_id"]
        assert load["booking_snapshot_id"]
        _, state = get_state(alpha_org)
        assert state["summary"]["owner_profit_distribution"] > 0

        duplicate = alpha.post(
            f"/rate-quotes/{quote['id']}/book",
            data={"final_agreed_rate": "2300"},
            follow_redirects=False,
        )
        assert duplicate.status_code == 409
        assert query_one("SELECT COUNT(*) AS total FROM loads WHERE opportunity_id=?", (quote["id"],))["total"] == 1
        with connect() as conn:
            with pytest.raises(sqlite3.DatabaseError, match="immutable"):
                conn.execute(
                    "UPDATE opportunity_snapshots SET result_json='{}' WHERE opportunity_id=?",
                    (quote["id"],),
                )


def test_new_customer_workspace_starts_without_otw_opportunities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "empty.db"))
    with TestClient(app) as client:
        signup(client, "empty-quotes@example.com", "Empty Fleet")
        assert query_one("SELECT COUNT(*) AS total FROM load_opportunities")["total"] == 0
        page = client.get("/rate-quotes")
        assert page.status_code == 200
        assert "No rate quotes yet" in page.text
