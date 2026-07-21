from __future__ import annotations

from datetime import date

import pytest

from app.calculations import calculate_quote, normalized_pay_model


SETTINGS = {
    "processing_fee_pct": 3,
    "admin_fee_per_load": 5,
    "payroll_burden_pct": 5,
    "target_margin_pct": 10,
}


def driver(pay_model: str, **values):
    base = {
        "pay_model": pay_model,
        "mpg": 10,
        "maintenance_per_mile": 0.20,
        "truck_financing_monthly": 600,
        "auto_insurance_monthly": 300,
        "trailer_financing_monthly": 0,
        "trailer_insurance_monthly": 0,
        "other_fixed_monthly": 0,
        "driver_profit_split_pct": 0,
        "contractor_gross_split_pct": 0,
        "owner_operator_split_pct": 0,
        "flat_rate_per_load": 0,
        "pay_per_loaded_mile": 0,
        "pay_per_total_mile": 0,
        "day_rate": 0,
        "payroll_burden_applies": 0,
    }
    base.update(values)
    return base


def quote(profile):
    return calculate_quote(
        SETTINGS,
        profile,
        date(2026, 7, 21),
        loaded_miles=500,
        deadhead_miles=50,
        trip_days=2,
        fuel_price=4.50,
        quoted_revenue=2_000,
        target_margin_pct=10,
    )


@pytest.mark.parametrize(
    ("model", "field", "rate", "expected"),
    [
        ("Flat Rate per Load", "flat_rate_per_load", 300, 300),
        ("Per Loaded Mile", "pay_per_loaded_mile", 0.60, 300),
        ("Per Total Mile", "pay_per_total_mile", 0.60, 330),
        ("Day Rate", "day_rate", 175, 350),
    ],
)
def test_fixed_and_mileage_pay_structures(model, field, rate, expected) -> None:
    result = quote(driver(model, **{field: rate}))
    assert result.driver_contractor_pay == pytest.approx(expected)
    assert result.recommended_minimum_revenue is not None
    assert result.recommended_minimum_revenue > result.total_operating_expense


def test_percentage_pay_structures_remain_distinct() -> None:
    profit_split = quote(driver("Profit Split", driver_profit_split_pct=40))
    gross_split = quote(driver("Contractor Gross Split", contractor_gross_split_pct=85))
    owner = quote(driver("Owner-Operator", owner_operator_split_pct=75))
    assert 0 < profit_split.driver_contractor_pay < 2_000
    assert gross_split.driver_contractor_pay == pytest.approx(1_700)
    assert owner.owner_operator_pay > 0
    assert normalized_pay_model("Per Loaded Mile") == "per_loaded_mile"


def test_contractor_gross_split_excludes_company_vehicle_costs() -> None:
    result = quote(driver("Contractor Gross Split", contractor_gross_split_pct=85))
    assert result.fuel_cost == 0
    assert result.fixed_cost == 0
    assert result.maintenance_reserve == 0
