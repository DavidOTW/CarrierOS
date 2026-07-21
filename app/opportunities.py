from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from .calculations import QuoteResult, calculate_quote, parse_date
from .routing import Location, RouteProvider


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _round_money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def _iso_date(value: Any) -> date | None:
    raw = str(value or "").strip()[:10]
    return parse_date(raw)


def trip_days_for(opportunity: Mapping[str, Any]) -> int:
    pickup = _iso_date(opportunity.get("pickup_at"))
    delivery = _iso_date(opportunity.get("delivery_at"))
    if not pickup or not delivery:
        return 1
    return max(1, (delivery - pickup).days + 1)


def offered_revenue(opportunity: Mapping[str, Any]) -> float:
    explicit = _num(opportunity.get("original_offered_rate"))
    if explicit > 0:
        return explicit
    return max(
        0.0,
        _num(opportunity.get("linehaul_revenue"))
        + _num(opportunity.get("fuel_surcharge"))
        + _num(opportunity.get("additional_revenue"))
        + _num(opportunity.get("stop_pay_revenue")),
    )


@dataclass(frozen=True)
class OpportunityResult:
    offered_revenue: float
    loaded_miles: float
    deadhead_miles: float
    total_miles: float
    deadhead_pct: float
    revenue_per_loaded_mile: float
    revenue_per_total_mile: float
    trip_days: int
    fuel_gallons: float
    fuel_cost: float
    tolls: float
    maintenance_reserve: float
    driver_contractor_pay: float
    owner_operator_pay: float
    payroll_burden: float
    factoring_quick_pay_fees: float
    fixed_cost: float
    other_direct_costs: float
    total_operating_expense: float
    company_profit: float
    owner_profit_distribution: float
    retained_company_profit: float
    company_margin_pct: float
    company_profit_per_mile: float
    company_profit_per_day: float
    cash_required_before_payment: float
    break_even_rate: float | None
    minimum_acceptable_rate: float | None
    target_rate: float | None
    opening_counteroffer: float | None
    maximum_reasonable_deadhead: float
    expected_invoice_date: str | None
    expected_payment_date: str | None
    recommendation: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    target_feasible: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _meets_thresholds(
    quote: QuoteResult,
    revenue: float,
    total_miles: float,
    trip_days: int,
    settings: Mapping[str, Any],
) -> bool:
    return (
        quote.company_margin_pct >= _num(settings.get("target_margin_pct")) / 100
        and quote.company_profit >= _num(settings.get("min_total_profit"), 200)
        and quote.company_profit / max(1.0, total_miles)
        >= _num(settings.get("min_company_profit_per_mile"), 0.25)
        and quote.company_profit / max(1, trip_days)
        >= _num(settings.get("min_profit_per_day"), 100)
        and revenue / max(1.0, total_miles)
        >= _num(settings.get("min_revenue_per_total_mile"), 1.75)
    )


def _minimum_rate(
    settings: Mapping[str, Any],
    driver: Mapping[str, Any],
    pickup: date,
    loaded: float,
    deadhead: float,
    trip_days: int,
    fuel_price: float,
    tolls: float,
    other_costs_without_revenue_fees: float,
    revenue_fee_pct: float,
) -> float | None:
    def quote_at(revenue: float) -> QuoteResult:
        revenue_fee = revenue * revenue_fee_pct / 100
        return calculate_quote(
            settings=settings,
            driver=driver,
            pickup_date=pickup,
            loaded_miles=loaded,
            deadhead_miles=deadhead,
            trip_days=trip_days,
            fuel_price=fuel_price,
            tolls_misc=tolls,
            other_direct_costs=other_costs_without_revenue_fees + revenue_fee,
            quoted_revenue=revenue,
            target_margin_pct=_num(settings.get("target_margin_pct"), 10),
        )

    total_miles = loaded + deadhead
    upper = max(1000.0, (total_miles or 1) * 5.0)
    for _ in range(24):
        if _meets_thresholds(quote_at(upper), upper, total_miles, trip_days, settings):
            break
        upper *= 2
    else:
        return None
    lower = 0.0
    for _ in range(60):
        midpoint = (lower + upper) / 2
        if _meets_thresholds(quote_at(midpoint), midpoint, total_miles, trip_days, settings):
            upper = midpoint
        else:
            lower = midpoint
    return _round_money(upper)


def calculate_opportunity(
    settings: Mapping[str, Any],
    driver: Mapping[str, Any] | None,
    opportunity: Mapping[str, Any],
    *,
    revenue_override: float | None = None,
    fuel_price: float | None = None,
    warnings: Sequence[str] = (),
) -> OpportunityResult:
    revenue = max(0.0, offered_revenue(opportunity) if revenue_override is None else revenue_override)
    loaded = max(0.0, _num(opportunity.get("loaded_miles")))
    deadhead = max(0.0, _num(opportunity.get("deadhead_miles")))
    total_miles = loaded + deadhead
    pickup = _iso_date(opportunity.get("pickup_at")) or date.today()
    delivery = _iso_date(opportunity.get("delivery_at"))
    trip_days = trip_days_for(opportunity)
    fuel_price = max(0.0, _num(fuel_price, _num(settings.get("fallback_diesel_price"))))
    tolls = max(0.0, _num(opportunity.get("tolls")))
    other_direct = max(0.0, _num(opportunity.get("lumper")) + _num(opportunity.get("misc_expenses")))
    revenue_fee_pct = max(0.0, _num(opportunity.get("factoring_pct")) + _num(opportunity.get("quick_pay_pct")))
    revenue_fees = revenue * revenue_fee_pct / 100
    reasons: list[str] = []
    result_warnings = list(warnings)

    if driver is None:
        result_warnings.append("Select a driver or pay profile before relying on the profit result.")
        driver = {
            "pay_model": "Flat Rate per Load",
            "flat_rate_per_load": 0,
            "mpg": 10,
            "maintenance_per_mile": 0,
            "payroll_burden_applies": 0,
        }
    quote = calculate_quote(
        settings=settings,
        driver=driver,
        pickup_date=pickup,
        loaded_miles=loaded,
        deadhead_miles=deadhead,
        trip_days=trip_days,
        fuel_price=fuel_price,
        tolls_misc=tolls,
        other_direct_costs=other_direct + revenue_fees,
        quoted_revenue=revenue,
        target_margin_pct=_num(settings.get("target_margin_pct"), 10),
    )
    minimum = _minimum_rate(
        settings,
        driver,
        pickup,
        loaded,
        deadhead,
        trip_days,
        fuel_price,
        tolls,
        other_direct,
        revenue_fee_pct,
    ) if loaded > 0 else None
    target = minimum
    counter = None
    if target is not None:
        counter_multiplier = 1 + max(0.0, _num(settings.get("quote_counteroffer_pct"), 5)) / 100
        counter = math.ceil((target * counter_multiplier) / 25) * 25

    threshold_margin = _num(settings.get("target_margin_pct"), 10) / 100
    threshold_profit = _num(settings.get("min_total_profit"), 200)
    threshold_profit_mile = _num(settings.get("min_company_profit_per_mile"), 0.25)
    threshold_profit_day = _num(settings.get("min_profit_per_day"), 100)
    threshold_rpm = _num(settings.get("min_revenue_per_total_mile"), 1.75)
    max_deadhead_pct = max(0.0, min(99.0, _num(settings.get("target_max_deadhead_pct"), 15))) / 100
    deadhead_pct = deadhead / total_miles if total_miles else 0
    maximum_deadhead = loaded * max_deadhead_pct / max(0.0001, 1 - max_deadhead_pct)

    if revenue <= 0:
        result_warnings.append("Enter the broker's offered rate.")
    if loaded <= 0:
        result_warnings.append("Loaded miles are required; use verified truck-routing mileage when available.")
    if not _iso_date(opportunity.get("pickup_at")) or not delivery:
        result_warnings.append("Pickup and delivery dates are required for scheduling and profit-per-day checks.")
    if deadhead_pct > max_deadhead_pct:
        reasons.append(
            f"Deadhead is {deadhead_pct:.1%}; company limit is {max_deadhead_pct:.1%}."
        )
    if quote.company_margin_pct < threshold_margin:
        reasons.append(
            f"Company margin is {quote.company_margin_pct:.1%}; target is {threshold_margin:.1%}."
        )
    if quote.company_profit < threshold_profit:
        reasons.append(
            f"Company profit is ${quote.company_profit:,.2f}; minimum is ${threshold_profit:,.2f}."
        )
    profit_mile = quote.company_profit / total_miles if total_miles else 0
    if profit_mile < threshold_profit_mile:
        reasons.append(
            f"Company profit per total mile is ${profit_mile:,.2f}; minimum is ${threshold_profit_mile:,.2f}."
        )
    profit_day = quote.company_profit / trip_days
    if profit_day < threshold_profit_day:
        reasons.append(
            f"Company profit per trip day is ${profit_day:,.2f}; minimum is ${threshold_profit_day:,.2f}."
        )
    revenue_rpm = revenue / total_miles if total_miles else 0
    if revenue_rpm < threshold_rpm:
        reasons.append(
            f"Revenue per total mile is ${revenue_rpm:,.2f}; minimum is ${threshold_rpm:,.2f}."
        )

    if result_warnings:
        recommendation = "REVIEW REQUIRED"
    elif not reasons:
        recommendation = "BOOK"
    elif quote.company_profit < 0 or minimum is None:
        recommendation = "DECLINE"
    else:
        recommendation = "NEGOTIATE"

    expected_invoice = delivery + timedelta(days=1) if delivery else None
    expected_payment = (
        expected_invoice + timedelta(days=max(0, _integer(settings.get("default_payment_days"), 30)))
        if expected_invoice else None
    )
    mpg = max(0.1, _num(driver.get("mpg"), 10))
    fuel_gallons = 0 if quote.fuel_cost == 0 else total_miles / mpg
    cash_required = quote.fuel_cost + tolls + other_direct + revenue_fees + quote.fixed_cost
    owner_distribution = max(0.0, quote.company_profit) * max(
        0.0, _num(settings.get("owner_distribution_pct"))
    ) / 100
    return OpportunityResult(
        offered_revenue=_round_money(revenue),
        loaded_miles=round(loaded, 1),
        deadhead_miles=round(deadhead, 1),
        total_miles=round(total_miles, 1),
        deadhead_pct=deadhead_pct,
        revenue_per_loaded_mile=revenue / loaded if loaded else 0,
        revenue_per_total_mile=revenue_rpm,
        trip_days=trip_days,
        fuel_gallons=round(fuel_gallons, 2),
        fuel_cost=_round_money(quote.fuel_cost),
        tolls=_round_money(tolls),
        maintenance_reserve=_round_money(quote.maintenance_reserve),
        driver_contractor_pay=_round_money(quote.driver_contractor_pay),
        owner_operator_pay=_round_money(quote.owner_operator_pay),
        payroll_burden=_round_money(quote.payroll_burden),
        factoring_quick_pay_fees=_round_money(revenue_fees),
        fixed_cost=_round_money(quote.fixed_cost),
        other_direct_costs=_round_money(other_direct),
        total_operating_expense=_round_money(quote.total_operating_expense),
        company_profit=_round_money(quote.company_profit),
        owner_profit_distribution=_round_money(owner_distribution),
        retained_company_profit=_round_money(quote.company_profit - owner_distribution),
        company_margin_pct=quote.company_margin_pct,
        company_profit_per_mile=profit_mile,
        company_profit_per_day=profit_day,
        cash_required_before_payment=_round_money(cash_required),
        break_even_rate=_round_money(quote.break_even_revenue) if quote.break_even_revenue is not None else None,
        minimum_acceptable_rate=minimum,
        target_rate=target,
        opening_counteroffer=float(counter) if counter is not None else None,
        maximum_reasonable_deadhead=round(maximum_deadhead, 1),
        expected_invoice_date=expected_invoice.isoformat() if expected_invoice else None,
        expected_payment_date=expected_payment.isoformat() if expected_payment else None,
        recommendation=recommendation,
        reasons=tuple(reasons),
        warnings=tuple(dict.fromkeys(result_warnings)),
        target_feasible=minimum is not None,
    )


def opportunity_input_snapshot(
    opportunity: Mapping[str, Any],
    settings: Mapping[str, Any],
    driver: Mapping[str, Any] | None,
    *,
    revenue: float,
) -> str:
    excluded = {"created_at", "updated_at", "created_by", "updated_by", "booked_load_id"}
    payload = {
        "opportunity": {key: value for key, value in dict(opportunity).items() if key not in excluded},
        "organization_thresholds": {
            key: settings.get(key)
            for key in (
                "fallback_diesel_price",
                "processing_fee_pct",
                "admin_fee_per_load",
                "payroll_burden_pct",
                "target_margin_pct",
                "target_max_deadhead_pct",
                "min_company_profit_per_mile",
                "min_total_profit",
                "min_profit_per_day",
                "min_revenue_per_total_mile",
                "owner_distribution_pct",
            )
        },
        "driver_pay_profile": dict(driver) if driver else None,
        "evaluated_revenue": revenue,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compare_drivers(
    settings: Mapping[str, Any],
    drivers: Sequence[Mapping[str, Any]],
    opportunity: Mapping[str, Any],
    locations: Mapping[int, Mapping[str, Any]],
    route_provider: RouteProvider,
    *,
    fuel_price: float | None = None,
    operational_warnings: Mapping[int, Sequence[str]] | None = None,
) -> list[dict[str, Any]]:
    origin = Location(
        city=str(opportunity.get("origin_city") or ""),
        state=str(opportunity.get("origin_state") or ""),
        postal_code=str(opportunity.get("origin_postal_code") or ""),
    )
    stale_hours = max(1, _integer(settings.get("location_stale_hours"), 24))
    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for driver in drivers:
        driver_id = int(driver["id"])
        location = locations.get(driver_id)
        candidate = dict(opportunity)
        route_warning = ""
        location_warning = "Driver location is unknown; enter or confirm deadhead miles."
        deadhead_source = "manual quote value"
        if location:
            observed_raw = str(location.get("observed_at") or "")
            try:
                observed = datetime.fromisoformat(observed_raw.replace("Z", "+00:00"))
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
                age_hours = max(0.0, (now - observed).total_seconds() / 3600)
                location_warning = (
                    f"Driver location is stale ({age_hours:.0f} hours old)."
                    if age_hours > stale_hours else ""
                )
            except ValueError:
                location_warning = "Driver location timestamp is invalid."
            estimate = route_provider.route_miles(
                Location(
                    city=str(location.get("city") or ""),
                    state=str(location.get("state") or ""),
                    postal_code=str(location.get("postal_code") or ""),
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                ),
                origin,
            )
            if estimate:
                candidate["deadhead_miles"] = estimate.miles
                deadhead_source = estimate.source
                route_warning = estimate.warning
        warnings = [item for item in (location_warning, route_warning) if item]
        warnings.extend((operational_warnings or {}).get(driver_id, ()))
        result = calculate_opportunity(
            settings,
            driver,
            candidate,
            fuel_price=fuel_price,
            warnings=warnings,
        )
        rows.append({
            "driver": dict(driver),
            "location": dict(location) if location else None,
            "deadhead_source": deadhead_source,
            "result": result,
        })
    rows.sort(key=lambda row: (
        row["result"].recommendation != "BOOK",
        -row["result"].company_profit,
        row["result"].deadhead_miles,
        str(row["driver"].get("name") or "").casefold(),
    ))
    return rows
