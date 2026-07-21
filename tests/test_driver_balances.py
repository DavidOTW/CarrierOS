from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.calculations import summarize_driver_balances


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
