from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from .calculations import days_in_month, normalized_pay_model
from .money import MONEY_QUANTUM, ROUNDING_POLICY, decimal_value, rate


ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def _value(
    source: Mapping[str, Any],
    key: str,
    default: str = "0",
    *,
    allow_negative: bool = False,
) -> Decimal:
    return decimal_value(
        source.get(key),
        field=key,
        default=default,
        allow_negative=allow_negative,
    )


def _enabled(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "yes", "true", "on", "included"}


def _currency(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUNDING_POLICY)


@dataclass(frozen=True)
class DecimalQuoteResult:
    total_miles: Decimal
    fuel_cost: Decimal
    fixed_cost: Decimal
    maintenance_reserve: Decimal
    company_fees: Decimal
    total_operating_expense: Decimal
    profit_before_pay: Decimal
    driver_contractor_pay: Decimal
    owner_operator_pay: Decimal
    payroll_burden: Decimal
    company_profit: Decimal
    company_margin_pct: Decimal
    all_in_rpm: Decimal
    recommended_minimum_revenue: Decimal | None
    recommended_minimum_rpm: Decimal | None
    break_even_revenue: Decimal | None
    target_revenue: Decimal | None
    premium_revenue: Decimal | None
    decision: str
    target_feasible: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_storage_dict(self) -> dict[str, str | bool | None]:
        return {
            key: (format(value, "f") if isinstance(value, Decimal) else value)
            for key, value in self.to_dict().items()
        }


def _monthly_fixed(driver: Mapping[str, Any]) -> Decimal:
    return sum(
        (
            max(ZERO, _value(driver, key))
            for key in (
                "truck_financing_monthly",
                "auto_insurance_monthly",
                "trailer_financing_monthly",
                "trailer_insurance_monthly",
                "other_fixed_monthly",
            )
        ),
        ZERO,
    )


def _fixed_compensation(
    driver: Mapping[str, Any],
    loaded_miles: Decimal,
    total_miles: Decimal,
    trip_days: int,
) -> Decimal:
    pay_model = normalized_pay_model(driver.get("pay_model"))
    if pay_model == "flat_rate_per_load":
        return max(ZERO, _value(driver, "flat_rate_per_load"))
    if pay_model == "per_loaded_mile":
        return max(ZERO, loaded_miles) * max(ZERO, _value(driver, "pay_per_loaded_mile"))
    if pay_model == "per_total_mile":
        return max(ZERO, total_miles) * max(ZERO, _value(driver, "pay_per_total_mile"))
    if pay_model == "day_rate":
        return Decimal(max(1, int(trip_days))) * max(ZERO, _value(driver, "day_rate"))
    return ZERO


def _minimum_revenue(
    settings: Mapping[str, Any],
    driver: Mapping[str, Any],
    base_cost_before_revenue_fees: Decimal,
    target_margin_pct: Decimal,
) -> Decimal | None:
    processing = max(ZERO, _value(settings, "processing_fee_pct")) / HUNDRED
    burden = max(ZERO, _value(settings, "payroll_burden_pct")) / HUNDRED
    pay_model = normalized_pay_model(driver.get("pay_model"))
    if pay_model == "profit_split":
        split = _value(driver, "driver_profit_split_pct") / HUNDRED
        retained_factor = ONE - split - (split * burden if _enabled(driver.get("payroll_burden_applies")) else ZERO)
        revenue_pay_rate = ZERO
    elif pay_model == "owner_operator":
        retained_factor = ONE - _value(driver, "owner_operator_split_pct") / HUNDRED
        revenue_pay_rate = ZERO
    elif pay_model == "contractor_rate_split":
        retained_factor = ONE
        split = _value(driver, "contractor_gross_split_pct") / HUNDRED
        revenue_pay_rate = split * (ONE + burden if _enabled(driver.get("payroll_burden_applies")) else ONE)
    else:
        retained_factor = ONE
        revenue_pay_rate = ZERO
    target = target_margin_pct / HUNDRED
    denominator = retained_factor * (ONE - processing) - revenue_pay_rate - target
    if denominator <= ZERO:
        return None
    admin_fee = max(ZERO, _value(settings, "admin_fee_per_load"))
    return (base_cost_before_revenue_fees + admin_fee) * retained_factor / denominator


def calculate_quote_decimal(
    settings: Mapping[str, Any],
    driver: Mapping[str, Any],
    pickup_date: date,
    loaded_miles: Any,
    deadhead_miles: Any,
    trip_days: int,
    fuel_price: Any,
    tolls_misc: Any = "0",
    other_direct_costs: Any = "0",
    quoted_revenue: Any | None = None,
    target_margin_pct: Any | None = None,
) -> DecimalQuoteResult:
    """Decimal implementation run beside the protected legacy calculator.

    PR 1 does not switch historical or customer-facing calculations to this path.
    Golden parity tests must approve any difference before later phases adopt it.
    """

    loaded = max(ZERO, rate(loaded_miles, field="loaded_miles"))
    deadhead = max(ZERO, rate(deadhead_miles, field="deadhead_miles"))
    total_miles = loaded + deadhead
    trip_days = max(1, int(trip_days))
    pay_model = normalized_pay_model(driver.get("pay_model"))
    fuel_price_value = max(ZERO, rate(fuel_price, field="fuel_price"))
    if pay_model == "contractor_rate_split":
        fuel_cost = fixed_cost = maintenance = ZERO
    else:
        mpg = max(Decimal("0.1"), _value(driver, "mpg", "0.1"))
        fuel_cost = total_miles / mpg * fuel_price_value
        fixed_cost = _monthly_fixed(driver) / Decimal(days_in_month(pickup_date)) * Decimal(trip_days)
        maintenance = total_miles * max(ZERO, _value(driver, "maintenance_per_mile"))
    tolls_value = max(ZERO, decimal_value(tolls_misc, field="tolls_misc", default="0", allow_negative=False))
    other_costs_value = max(
        ZERO,
        decimal_value(other_direct_costs, field="other_direct_costs", default="0", allow_negative=False),
    )
    base_cost = fuel_cost + fixed_cost + maintenance + tolls_value + other_costs_value
    fixed_compensation = _fixed_compensation(driver, loaded, total_miles, trip_days)
    burden_rate = max(ZERO, _value(settings, "payroll_burden_pct")) / HUNDRED
    fixed_payroll = (
        fixed_compensation * burden_rate
        if _enabled(driver.get("payroll_burden_applies"))
        else ZERO
    )
    minimum_base_cost = base_cost + fixed_compensation + fixed_payroll
    target_margin = decimal_value(
        target_margin_pct,
        field="target_margin_pct",
        default=_value(settings, "target_margin_pct"),
        allow_negative=False,
    )
    recommended = _minimum_revenue(settings, driver, minimum_base_cost, target_margin)
    break_even = _minimum_revenue(settings, driver, minimum_base_cost, ZERO)
    premium = recommended * Decimal("1.10") if recommended is not None else None
    has_revenue = quoted_revenue is not None and not (
        isinstance(quoted_revenue, str) and not quoted_revenue.strip()
    )
    revenue = (
        max(ZERO, decimal_value(quoted_revenue, field="quoted_revenue", allow_negative=False))
        if has_revenue
        else ZERO
    )
    fees = (
        revenue * max(ZERO, _value(settings, "processing_fee_pct")) / HUNDRED
        + max(ZERO, _value(settings, "admin_fee_per_load"))
        if has_revenue
        else ZERO
    )
    operating = base_cost + fees if has_revenue else base_cost
    profit_before_pay = revenue - operating if has_revenue else ZERO
    driver_pay = owner_pay = ZERO
    if has_revenue:
        if pay_model == "profit_split":
            driver_pay = max(ZERO, profit_before_pay * _value(driver, "driver_profit_split_pct") / HUNDRED)
        elif pay_model == "contractor_rate_split":
            driver_pay = max(ZERO, revenue * _value(driver, "contractor_gross_split_pct") / HUNDRED)
        elif pay_model == "owner_operator":
            owner_pay = max(ZERO, profit_before_pay * _value(driver, "owner_operator_split_pct") / HUNDRED)
        else:
            driver_pay = fixed_compensation
    payroll = driver_pay * burden_rate if _enabled(driver.get("payroll_burden_applies")) else ZERO
    company_profit = revenue - operating - driver_pay - owner_pay - payroll if has_revenue else ZERO
    margin = company_profit / revenue if revenue else ZERO
    if not has_revenue:
        decision = "ENTER QUOTE"
    elif company_profit < ZERO:
        decision = "DECLINE / REPRICE"
    elif margin < target_margin / HUNDRED:
        decision = "REPRICE"
    else:
        decision = "MEETS TARGET"
    return DecimalQuoteResult(
        total_miles=rate(total_miles, field="total_miles"),
        fuel_cost=_currency(fuel_cost),
        fixed_cost=_currency(fixed_cost),
        maintenance_reserve=_currency(maintenance),
        company_fees=_currency(fees),
        total_operating_expense=_currency(operating),
        profit_before_pay=_currency(profit_before_pay),
        driver_contractor_pay=_currency(driver_pay),
        owner_operator_pay=_currency(owner_pay),
        payroll_burden=_currency(payroll),
        company_profit=_currency(company_profit),
        company_margin_pct=margin.quantize(Decimal("0.000001"), rounding=ROUNDING_POLICY),
        all_in_rpm=(revenue / total_miles if total_miles and revenue else ZERO).quantize(
            Decimal("0.000001"), rounding=ROUNDING_POLICY
        ),
        recommended_minimum_revenue=_currency(recommended) if recommended is not None else None,
        recommended_minimum_rpm=(
            (recommended / total_miles).quantize(Decimal("0.000001"), rounding=ROUNDING_POLICY)
            if recommended is not None and total_miles
            else None
        ),
        break_even_revenue=_currency(break_even) if break_even is not None else None,
        target_revenue=_currency(recommended) if recommended is not None else None,
        premium_revenue=_currency(premium) if premium is not None else None,
        decision=decision,
        target_feasible=recommended is not None,
    )
