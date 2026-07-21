from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.calculations import calculate_load_results, summarize_driver_balances, summarize_owner_pay


def test_driver_balance_is_cumulative_not_latest_load_pay() -> None:
    """The balance carries earlier unpaid earnings forward across included loads."""
    drivers = [
        {
            "id": 1,
            "name": "Chris",
            "role": "Driver",
            "pay_model": "profit_split",
            "vehicle_id": 1,
        }
    ]
    loads = [
        {"id": 101, "driver_id": 1, "revenue": 100.0},
        {"id": 102, "driver_id": 1, "revenue": 225.0},
    ]
    load_results = {
        101: SimpleNamespace(
            included=True,
            total_miles=100.0,
            driver_contractor_earned=31.0002884250467,
            owner_operator_load_pay=0.0,
        ),
        102: SimpleNamespace(
            included=True,
            total_miles=120.0,
            driver_contractor_earned=74.5893102466793,
            owner_operator_load_pay=0.0,
        ),
    }

    [balance] = summarize_driver_balances(
        drivers,
        loads,
        load_results,
        payments=[],
        idle_state={"periods": []},
    )

    latest_load_pay = load_results[102].driver_contractor_earned
    assert latest_load_pay == pytest.approx(74.5893102466793)
    assert balance["load_pay_earned"] == pytest.approx(105.589598671726)
    assert balance["remaining_load_pay"] == 105.59
    assert balance["remaining_load_pay"] != round(latest_load_pay, 2)


def test_driver_balance_subtracts_only_applied_payments_and_idle_reductions() -> None:
    drivers = [{"id": 1, "name": "Driver", "role": "Driver", "pay_model": "profit_split"}]
    loads = [{"id": 1, "driver_id": 1, "revenue": 500.0}]
    load_results = {
        1: SimpleNamespace(
            included=True,
            total_miles=250.0,
            driver_contractor_earned=200.0,
            owner_operator_load_pay=0.0,
        )
    }
    payments = [
        {"driver_id": 1, "amount": 80.0, "counts_against_load_pay": True},
        {"driver_id": 1, "amount": 50.0, "counts_against_load_pay": False},
    ]
    idle_state = {"periods": [{"driver_id": 1, "driver_pay_reduction": 20.0}]}

    [balance] = summarize_driver_balances(drivers, loads, load_results, payments, idle_state)

    assert balance["payments_applied"] == 80.0
    assert balance["idle_fixed_cost_pay_reduction"] == 20.0
    assert balance["remaining_load_pay"] == 100.0


def test_configured_owner_percentage_is_applied_to_positive_company_profit() -> None:
    drivers = [
        {
            "id": 1,
            "name": "Driver",
            "role": "Driver",
            "pay_model": "Profit Split",
            "driver_profit_split_pct": 40,
            "vehicle_id": 1,
            "mpg": 10,
        }
    ]
    loads = [
        {
            "id": 101,
            "driver_id": 1,
            "vehicle_id": 1,
            "pickup_date": "2026-07-20",
            "delivery_date": "2026-07-20",
            "revenue": 1_000,
            "loaded_miles": 100,
            "deadhead_miles": 0,
            "status": "Delivered",
        }
    ]
    settings = {
        "fallback_diesel_price": 0,
        "processing_fee_pct": 0,
        "admin_fee_per_load": 0,
        "payroll_burden_pct": 0,
        "owner_distribution_pct": 30,
        "max_active_days": 31,
    }

    result = calculate_load_results(settings, drivers, weekly_fuel=[], loads=loads)[101]

    assert result.driver_contractor_earned == pytest.approx(400.0)
    assert result.company_profit_before_owner_distribution == pytest.approx(600.0)
    assert result.owner_profit_distribution == pytest.approx(180.0)
    assert result.retained_company_profit == pytest.approx(420.0)


def test_owner_balance_combines_personal_load_pay_and_profit_distribution() -> None:
    drivers = [
        {"id": 1, "name": "David", "role": "Owner", "pay_model": "Owner-Operator"},
        {"id": 2, "name": "Driver", "role": "Driver", "pay_model": "Profit Split"},
    ]
    load_results = {
        101: SimpleNamespace(
            included=True,
            owner_operator_load_pay=100.0,
            company_profit_before_owner_distribution=80.0,
            owner_profit_distribution=40.0,
        )
    }
    payments = [
        {
            "driver_id": 1,
            "amount": 100.0,
            "payment_type": "Regular payout",
            "counts_against_load_pay": True,
            "include_in_reports": False,
        },
        {
            "driver_id": 1,
            "amount": 15.0,
            "payment_type": "Owner profit draw",
            "counts_against_load_pay": True,
            "include_in_reports": False,
        },
        {
            "driver_id": 2,
            "amount": 5.0,
            "payment_type": "Owner profit draw",
            "counts_against_load_pay": True,
            "include_in_reports": True,
        },
    ]

    owner = summarize_owner_pay(drivers, load_results, payments)

    assert owner["owner_operator_load_pay_earned"] == pytest.approx(100.0)
    assert owner["owner_profit_distribution_earned"] == pytest.approx(40.0)
    assert owner["total_owner_earnings"] == pytest.approx(140.0)
    assert owner["owner_operator_payments_applied"] == pytest.approx(100.0)
    assert owner["owner_profit_draws_paid"] == pytest.approx(15.0)
    assert owner["total_owner_payments_draws"] == pytest.approx(115.0)
    assert owner["total_owner_remaining"] == pytest.approx(25.0)
