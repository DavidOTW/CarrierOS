from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.calculations import calculate_quote
from app.decimal_calculations import calculate_quote_decimal
from app.money import (
    MoneyInputError,
    basis_points_to_percentage,
    cents_to_money,
    money,
    money_to_cents,
    percentage_to_basis_points,
    rate_to_micros,
)


SETTINGS = {
    "processing_fee_pct": 3,
    "admin_fee_per_load": 5,
    "payroll_burden_pct": 5,
    "target_margin_pct": 10,
}

BASE_DRIVER = {
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

MODELS = {
    "Profit Split": {"driver_profit_split_pct": 40},
    "Contractor Gross Split": {"contractor_gross_split_pct": 85},
    "Owner-Operator": {"owner_operator_split_pct": 75},
    "Flat Rate per Load": {"flat_rate_per_load": 300},
    "Per Loaded Mile": {"pay_per_loaded_mile": 0.60},
    "Per Total Mile": {"pay_per_total_mile": 0.60},
    "Day Rate": {"day_rate": 175},
}

CURRENCY_FIELDS = {
    "fuel_cost",
    "fixed_cost",
    "maintenance_reserve",
    "company_fees",
    "total_operating_expense",
    "driver_contractor_pay",
    "owner_operator_pay",
    "company_profit",
    "recommended_minimum_revenue",
}


def _driver(model: str) -> dict:
    return {**BASE_DRIVER, "pay_model": model, **MODELS[model]}


def test_strict_money_parser_and_half_up_rounding() -> None:
    assert money("10.005") == Decimal("10.01")
    assert money("-10.005") == Decimal("-10.01")
    assert money_to_cents("0.29") == 29
    assert cents_to_money(29) == Decimal("0.29")
    assert percentage_to_basis_points("40.125") == 4013
    assert basis_points_to_percentage(4013) == Decimal("40.1300")
    assert rate_to_micros("0.605001") == 605001


@pytest.mark.parametrize("bad", ["not money", "1,000.00", "NaN", "Infinity", True])
def test_invalid_financial_input_never_becomes_zero(bad: object) -> None:
    with pytest.raises(MoneyInputError):
        money(bad, field="offered rate")


@pytest.mark.parametrize("model", list(MODELS))
def test_decimal_quote_path_matches_protected_legacy_golden_fixture(model: str) -> None:
    golden = json.loads(
        (Path(__file__).parent / "fixtures" / "v016_quote_golden.json").read_text(encoding="utf-8")
    )[model]
    driver = _driver(model)
    legacy = calculate_quote(
        SETTINGS,
        driver,
        date(2026, 7, 21),
        loaded_miles=500,
        deadhead_miles=50,
        trip_days=2,
        fuel_price=4.5,
        tolls_misc=20,
        other_direct_costs=30,
        quoted_revenue=2000,
        target_margin_pct=10,
    )
    decimal_result = calculate_quote_decimal(
        SETTINGS,
        driver,
        date(2026, 7, 21),
        loaded_miles="500",
        deadhead_miles="50",
        trip_days=2,
        fuel_price="4.5",
        tolls_misc="20",
        other_direct_costs="30",
        quoted_revenue="2000",
        target_margin_pct="10",
    )
    for field in CURRENCY_FIELDS:
        expected = Decimal(golden[field])
        assert getattr(decimal_result, field) == expected
        assert Decimal(str(getattr(legacy, field))).quantize(Decimal("0.01")) == expected
    assert decimal_result.decision == golden["decision"] == legacy.decision


def test_decimal_path_rejects_bad_values_that_legacy_path_would_default() -> None:
    with pytest.raises(MoneyInputError, match="fuel_price"):
        calculate_quote_decimal(
            SETTINGS,
            _driver("Flat Rate per Load"),
            date(2026, 7, 21),
            loaded_miles="500",
            deadhead_miles="50",
            trip_days=2,
            fuel_price="unknown",
            quoted_revenue="2000",
        )
