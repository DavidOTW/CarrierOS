from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Mapping, Sequence


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "yes", "true", "on", "included"}


def parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def month_start(value: date) -> date:
    return value.replace(day=1)


def add_months(value: date, months: int) -> date:
    index = value.year * 12 + (value.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def days_in_month(value: date) -> int:
    return calendar.monthrange(value.year, value.month)[1]


def date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def monday_for(value: date) -> date:
    return value - timedelta(days=value.weekday())


def driver_monthly_fixed(driver: Mapping[str, Any]) -> float:
    return sum(
        max(0.0, _num(driver.get(key)))
        for key in (
            "truck_financing_monthly",
            "auto_insurance_monthly",
            "trailer_financing_monthly",
            "trailer_insurance_monthly",
            "other_fixed_monthly",
        )
    )


def normalized_pay_model(value: Any) -> str:
    text = str(value or "Profit Split").strip().lower().replace("_", " ").replace("-", " ")
    if "owner" in text:
        return "owner_operator"
    if "contractor" in text or "gross" in text:
        return "contractor_rate_split"
    if "loaded" in text and "mile" in text:
        return "per_loaded_mile"
    if "total" in text and "mile" in text:
        return "per_total_mile"
    if "flat" in text or text.endswith("per load"):
        return "flat_rate_per_load"
    if "day" in text:
        return "day_rate"
    return "profit_split"


def fixed_driver_compensation(
    driver: Mapping[str, Any], loaded_miles: float, total_miles: float, trip_days: int
) -> float:
    pay_model = normalized_pay_model(driver.get("pay_model"))
    if pay_model == "flat_rate_per_load":
        return max(0.0, _num(driver.get("flat_rate_per_load")))
    if pay_model == "per_loaded_mile":
        return max(0.0, loaded_miles) * max(0.0, _num(driver.get("pay_per_loaded_mile")))
    if pay_model == "per_total_mile":
        return max(0.0, total_miles) * max(0.0, _num(driver.get("pay_per_total_mile")))
    if pay_model == "day_rate":
        return max(1, int(trip_days)) * max(0.0, _num(driver.get("day_rate")))
    return 0.0


def payment_counts(value: Any) -> bool:
    return _bool(value)


@dataclass(frozen=True)
class LoadResult:
    load_id: int
    included: bool
    exclusion_reason: str
    total_miles: float
    trip_days: int
    fuel_price_used: float
    fuel_cost: float
    allocated_fixed_cost: float
    maintenance_reserve: float
    company_fees: float
    tolls_misc: float
    other_direct_costs: float
    total_operating_expense: float
    profit_before_pay: float
    driver_contractor_earned: float
    owner_operator_load_pay: float
    payroll_burden: float
    company_profit_before_owner_distribution: float
    owner_profit_distribution: float
    retained_company_profit: float
    all_in_revenue_per_mile: float
    deadhead_pct: float
    company_profit_per_mile: float
    company_margin_pct: float
    decision: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuoteResult:
    total_miles: float
    fuel_cost: float
    fixed_cost: float
    maintenance_reserve: float
    company_fees: float
    total_operating_expense: float
    profit_before_pay: float
    driver_contractor_pay: float
    owner_operator_pay: float
    payroll_burden: float
    company_profit: float
    company_margin_pct: float
    all_in_rpm: float
    recommended_minimum_revenue: float | None
    recommended_minimum_rpm: float | None
    break_even_revenue: float | None
    target_revenue: float | None
    premium_revenue: float | None
    decision: str
    target_feasible: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fuel_price_for(pickup: date, weekly_fuel: Sequence[Mapping[str, Any]], fallback: float) -> float:
    best_date: date | None = None
    best_price = fallback
    for row in weekly_fuel:
        week = parse_date(row.get("week_start"))
        price = row.get("average_price")
        if week is None or price in (None, "") or week > pickup:
            continue
        if best_date is None or week >= best_date:
            best_date = week
            best_price = _num(price, fallback)
    return best_price


def _candidate_load(
    load: Mapping[str, Any],
    driver: Mapping[str, Any] | None,
    settings: Mapping[str, Any],
) -> tuple[bool, str, date | None, date | None, int]:
    pickup = parse_date(load.get("pickup_date"))
    delivery = parse_date(load.get("delivery_date"))
    if pickup is None or delivery is None:
        return False, "Missing pickup or delivery date", pickup, delivery, 0
    if driver is None:
        return False, "Missing driver", pickup, delivery, 0
    if not _bool(driver.get("active", driver.get("enabled", True)), True):
        return False, "Driver is disabled", pickup, delivery, 0
    if load.get("revenue") in (None, ""):
        return False, "Missing revenue", pickup, delivery, 0
    if not _bool(load.get("include_in_model", True), True):
        return False, "Excluded by user", pickup, delivery, 0
    status = str(load.get("status") or "").strip().lower()
    if status in {"cancelled", "canceled", "quote"}:
        return False, f"Status is {status}", pickup, delivery, 0
    trip_days = (delivery - pickup).days + 1
    if trip_days < 1:
        return False, "Delivery precedes pickup", pickup, delivery, trip_days
    if trip_days > int(_num(settings.get("max_active_days"), 31)):
        return False, "Trip exceeds maximum active days", pickup, delivery, trip_days
    supported_start = parse_date(settings.get("supported_start_date"))
    supported_end = parse_date(settings.get("supported_end_date"))
    if supported_start and pickup < supported_start:
        return False, "Pickup is before supported calendar", pickup, delivery, trip_days
    if supported_end and delivery > supported_end:
        return False, "Delivery is after supported calendar", pickup, delivery, trip_days
    vehicle_id = load.get("vehicle_id") or driver.get("vehicle_id")
    if not vehicle_id:
        return False, "Missing unit / truck", pickup, delivery, trip_days
    return True, "", pickup, delivery, trip_days


def calculate_load_results(
    settings: Mapping[str, Any],
    drivers: Sequence[Mapping[str, Any]],
    weekly_fuel: Sequence[Mapping[str, Any]],
    loads: Sequence[Mapping[str, Any]],
) -> dict[int, LoadResult]:
    drivers_by_id = {int(row["id"]): row for row in drivers}
    prepared: dict[int, dict[str, Any]] = {}
    occupancy: dict[tuple[int, date], list[int]] = defaultdict(list)

    for row in loads:
        load_id = int(row["id"])
        driver = drivers_by_id.get(int(row.get("driver_id") or 0))
        included, reason, pickup, delivery, trip_days = _candidate_load(row, driver, settings)
        vehicle_id = int(row.get("vehicle_id") or (driver or {}).get("vehicle_id") or 0)
        prepared[load_id] = {
            "row": row,
            "driver": driver,
            "included": included,
            "reason": reason,
            "pickup": pickup,
            "delivery": delivery,
            "trip_days": trip_days,
            "vehicle_id": vehicle_id,
        }
        if included and pickup and delivery:
            for day in date_range(pickup, delivery):
                occupancy[(vehicle_id, day)].append(load_id)

    fallback = _num(settings.get("fallback_diesel_price"), 0.0)
    processing_rate = max(0.0, _num(settings.get("processing_fee_pct"))) / 100.0
    admin_fee = max(0.0, _num(settings.get("admin_fee_per_load")))
    burden_rate = max(0.0, _num(settings.get("payroll_burden_pct"))) / 100.0
    owner_distribution_rate = max(0.0, _num(settings.get("owner_distribution_pct"))) / 100.0
    target_margin = _num(settings.get("target_margin_pct")) / 100.0
    max_deadhead = _num(settings.get("target_max_deadhead_pct")) / 100.0
    min_profit_mile = _num(settings.get("min_company_profit_per_mile"))

    results: dict[int, LoadResult] = {}
    for load_id, info in prepared.items():
        row = info["row"]
        driver = info["driver"] or {}
        revenue = max(0.0, _num(row.get("revenue")))
        loaded = max(0.0, _num(row.get("loaded_miles")))
        deadhead = max(0.0, _num(row.get("deadhead_miles")))
        total_miles = loaded + deadhead
        tolls_misc = max(0.0, _num(row.get("tolls_misc", row.get("tolls"))))
        other_direct = max(0.0, _num(row.get("other_direct_costs", row.get("misc"))))

        if not info["included"]:
            results[load_id] = LoadResult(
                load_id=load_id,
                included=False,
                exclusion_reason=info["reason"],
                total_miles=total_miles,
                trip_days=max(0, int(info["trip_days"])),
                fuel_price_used=0.0,
                fuel_cost=0.0,
                allocated_fixed_cost=0.0,
                maintenance_reserve=0.0,
                company_fees=0.0,
                tolls_misc=tolls_misc,
                other_direct_costs=other_direct,
                total_operating_expense=0.0,
                profit_before_pay=0.0,
                driver_contractor_earned=0.0,
                owner_operator_load_pay=0.0,
                payroll_burden=0.0,
                company_profit_before_owner_distribution=0.0,
                owner_profit_distribution=0.0,
                retained_company_profit=0.0,
                all_in_revenue_per_mile=0.0,
                deadhead_pct=(deadhead / total_miles if total_miles else 0.0),
                company_profit_per_mile=0.0,
                company_margin_pct=0.0,
                decision="CHECK INPUTS",
            )
            continue

        pickup: date = info["pickup"]
        delivery: date = info["delivery"]
        override = row.get("fuel_override")
        fuel_price = _num(override) if override not in (None, "") else fuel_price_for(pickup, weekly_fuel, fallback)
        pay_model = normalized_pay_model(driver.get("pay_model"))
        mpg = max(0.1, _num(driver.get("mpg"), 0.1))
        maintenance_rate = max(0.0, _num(driver.get("maintenance_per_mile")))

        if pay_model == "contractor_rate_split":
            fuel_cost = 0.0
            maintenance = 0.0
        else:
            fuel_cost = total_miles / mpg * fuel_price
            maintenance = total_miles * maintenance_rate

        monthly_fixed = driver_monthly_fixed(driver)
        allocated_fixed = 0.0
        for day in date_range(pickup, delivery):
            concurrent = max(1, len(occupancy[(info["vehicle_id"], day)]))
            allocated_fixed += monthly_fixed / days_in_month(day) / concurrent

        fees = revenue * processing_rate + admin_fee
        operating = fuel_cost + allocated_fixed + maintenance + fees + tolls_misc + other_direct
        profit_before_pay = revenue - operating

        driver_pay = 0.0
        owner_operator_pay = 0.0
        if pay_model == "profit_split":
            driver_pay = max(0.0, profit_before_pay * _num(driver.get("driver_profit_split_pct")) / 100.0)
        elif pay_model == "contractor_rate_split":
            driver_pay = max(0.0, revenue * _num(driver.get("contractor_gross_split_pct")) / 100.0)
        elif pay_model == "owner_operator":
            owner_operator_pay = max(0.0, profit_before_pay * _num(driver.get("owner_operator_split_pct")) / 100.0)
        else:
            driver_pay = fixed_driver_compensation(driver, loaded, total_miles, info["trip_days"])

        payroll_burden = driver_pay * burden_rate if _bool(driver.get("payroll_burden_applies")) else 0.0
        company_profit = revenue - operating - driver_pay - owner_operator_pay - payroll_burden
        owner_distribution = max(0.0, company_profit) * owner_distribution_rate
        retained = company_profit - owner_distribution
        rpm = revenue / total_miles if total_miles else 0.0
        dh_pct = deadhead / total_miles if total_miles else 0.0
        profit_mile = company_profit / total_miles if total_miles else 0.0
        margin = company_profit / revenue if revenue else 0.0

        if company_profit < 0:
            decision = "LOSS"
        elif revenue and margin < target_margin:
            decision = "BELOW TARGET"
        elif dh_pct > max_deadhead:
            decision = "HIGH DEADHEAD"
        elif profit_mile < min_profit_mile:
            decision = "LOW COMPANY PROFIT"
        else:
            decision = "OK"

        results[load_id] = LoadResult(
            load_id=load_id,
            included=True,
            exclusion_reason="",
            total_miles=total_miles,
            trip_days=int(info["trip_days"]),
            fuel_price_used=fuel_price,
            fuel_cost=fuel_cost,
            allocated_fixed_cost=allocated_fixed,
            maintenance_reserve=maintenance,
            company_fees=fees,
            tolls_misc=tolls_misc,
            other_direct_costs=other_direct,
            total_operating_expense=operating,
            profit_before_pay=profit_before_pay,
            driver_contractor_earned=driver_pay,
            owner_operator_load_pay=owner_operator_pay,
            payroll_burden=payroll_burden,
            company_profit_before_owner_distribution=company_profit,
            owner_profit_distribution=owner_distribution,
            retained_company_profit=retained,
            all_in_revenue_per_mile=rpm,
            deadhead_pct=dh_pct,
            company_profit_per_mile=profit_mile,
            company_margin_pct=margin,
            decision=decision,
        )
    return results


def _valid_idle_periods(
    drivers_by_id: Mapping[int, Mapping[str, Any]],
    idle_periods: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for row in idle_periods:
        start = parse_date(row.get("start_date"))
        end = parse_date(row.get("end_date"))
        driver = drivers_by_id.get(int(row.get("driver_id") or 0))
        vehicle_id = int(row.get("vehicle_id") or (driver or {}).get("vehicle_id") or 0)
        situation = str(row.get("situation") or "")
        include = _bool(row.get("include_in_model", row.get("include", True)), True)
        status = "OK"
        if not include:
            status = "EXCLUDED"
        elif start is None or end is None or driver is None or not situation:
            status = "CHECK INPUTS"
        elif end < start:
            status = "END BEFORE START"
        elif start.year != end.year or start.month != end.month:
            status = "SPLIT AT MONTH END"
        elif (end - start).days + 1 > 31:
            status = "SPLIT >31 DAYS"
        elif "driver keeps truck" in situation.lower() and normalized_pay_model(driver.get("pay_model")) != "profit_split":
            status = "CHOOSE COMPANY - NOT PROFIT SPLIT"
        prepared.append({
            "row": row,
            "start": start,
            "end": end,
            "driver": driver,
            "vehicle_id": vehicle_id,
            "situation": situation,
            "include": include,
            "status": status,
            "overlap_status": "OK",
        })

    for index, current in enumerate(prepared):
        if current["status"] != "OK":
            continue
        for other_index, other in enumerate(prepared):
            if index == other_index or other["status"] != "OK":
                continue
            if current["vehicle_id"] != other["vehicle_id"]:
                continue
            if current["start"] <= other["end"] and current["end"] >= other["start"]:
                current["overlap_status"] = "OVERLAP - FIX"
                break
    return prepared


def calculate_idle_state(
    drivers: Sequence[Mapping[str, Any]],
    vehicles: Sequence[Mapping[str, Any]],
    loads: Sequence[Mapping[str, Any]],
    load_results: Mapping[int, LoadResult],
    idle_periods: Sequence[Mapping[str, Any]],
    months: Sequence[date],
) -> dict[str, Any]:
    drivers_by_id = {int(row["id"]): row for row in drivers}
    vehicles_by_id = {int(row["id"]): row for row in vehicles}
    valid_load_days: dict[int, set[date]] = defaultdict(set)
    for load in loads:
        result = load_results.get(int(load["id"]))
        if not result or not result.included:
            continue
        pickup = parse_date(load.get("pickup_date"))
        delivery = parse_date(load.get("delivery_date"))
        driver = drivers_by_id.get(int(load.get("driver_id") or 0))
        vehicle_id = int(load.get("vehicle_id") or (driver or {}).get("vehicle_id") or 0)
        if pickup and delivery:
            valid_load_days[vehicle_id].update(date_range(pickup, delivery))

    prepared_periods = _valid_idle_periods(drivers_by_id, idle_periods)
    period_results: list[dict[str, Any]] = []
    for item in prepared_periods:
        row = item["row"]
        start = item["start"]
        end = item["end"]
        driver = item["driver"] or {}
        calendar_days = ((end - start).days + 1) if start and end else 0
        covered_days = 0
        if start and end:
            covered_days = sum(1 for day in date_range(start, end) if day in valid_load_days[item["vehicle_id"]])
        idle_days = max(0, calendar_days - covered_days)
        monthly_fixed = driver_monthly_fixed(driver)
        idle_fixed = 0.0
        if start and item["status"] == "OK" and item["overlap_status"] == "OK":
            idle_fixed = idle_days * monthly_fixed / days_in_month(start)
        kept = "driver keeps truck" in item["situation"].lower()
        reduction = idle_fixed * _num(driver.get("driver_profit_split_pct")) / 100.0 if kept else 0.0
        company_cost = max(0.0, idle_fixed - reduction)
        result_text = item["status"] if item["status"] != "OK" else item["overlap_status"]
        if result_text == "OK":
            if idle_fixed == 0:
                responsibility = "COVERED BY LOAD"
            elif kept:
                responsibility = f"DRIVER PAY REDUCTION {_num(driver.get('driver_profit_split_pct')):.0f}% - {driver.get('name','')}"
            else:
                responsibility = "COMPANY"
        else:
            responsibility = result_text
        period_results.append({
            **dict(row),
            "start": start,
            "end": end,
            "vehicle_id": item["vehicle_id"],
            "driver_name": driver.get("name", ""),
            "calendar_days": calendar_days,
            "load_covered_days": covered_days,
            "idle_days": idle_days,
            "monthly_fixed_cost": monthly_fixed,
            "idle_fixed_cost": idle_fixed,
            "driver_pay_reduction": reduction,
            "company_idle_cost": company_cost,
            "period_status": item["status"],
            "overlap_status": item["overlap_status"],
            "responsibility_result": responsibility,
        })

    # A unit can appear on more than one driver profile. The workbook uses one
    # source profile per unit; choose the profile with the highest current fixed cost,
    # then the later record, which mirrors the current F350/Kenny setup.
    source_driver_by_vehicle: dict[int, Mapping[str, Any]] = {}
    for driver in drivers:
        vehicle_id = int(driver.get("vehicle_id") or 0)
        if not vehicle_id or not _bool(driver.get("active", True), True):
            continue
        existing = source_driver_by_vehicle.get(vehicle_id)
        candidate_key = (driver_monthly_fixed(driver), int(driver.get("id") or 0))
        existing_key = (driver_monthly_fixed(existing), int(existing.get("id") or 0)) if existing else (-1.0, -1)
        if candidate_key >= existing_key:
            source_driver_by_vehicle[vehicle_id] = driver

    bridges: list[dict[str, Any]] = []
    by_month_vehicle: dict[tuple[date, int], dict[str, Any]] = {}
    for month in months:
        month = month_start(month)
        dim = days_in_month(month)
        month_days = set(date_range(month, month.replace(day=dim)))
        for vehicle_id, source_driver in source_driver_by_vehicle.items():
            vehicle = vehicles_by_id.get(vehicle_id, {})
            monthly_fixed = driver_monthly_fixed(source_driver)
            load_days = len(month_days.intersection(valid_load_days.get(vehicle_id, set())))
            load_allocated = monthly_fixed / dim * load_days if dim else 0.0
            period_subset = [
                p for p in period_results
                if p["vehicle_id"] == vehicle_id
                and p["start"] is not None
                and month_start(p["start"]) == month
                and p["period_status"] == "OK"
                and p["overlap_status"] == "OK"
                and _bool(p.get("include_in_model", p.get("include", True)), True)
            ]
            logged_idle_days = sum(int(p["idle_days"]) for p in period_subset)
            driver_reduction = sum(_num(p["driver_pay_reduction"]) for p in period_subset)
            logged_company = sum(_num(p["company_idle_cost"]) for p in period_subset)
            unlogged_days = max(0, dim - load_days - logged_idle_days)
            unlogged_company = monthly_fixed / dim * unlogged_days if dim else 0.0
            total_company = logged_company + unlogged_company
            total_idle_fixed = max(0.0, monthly_fixed - load_allocated)
            accounted = load_allocated + driver_reduction + total_company
            status = "OK" if abs(accounted - monthly_fixed) <= 0.02 else "REVIEW"
            bridge = {
                "month": month,
                "vehicle_id": vehicle_id,
                "vehicle_name": vehicle.get("name", ""),
                "source_driver_name": source_driver.get("name", ""),
                "monthly_fixed_cost": monthly_fixed,
                "calendar_days": dim,
                "load_covered_days": load_days,
                "load_allocated_fixed_cost": load_allocated,
                "logged_idle_days": logged_idle_days,
                "driver_pay_reduction": driver_reduction,
                "logged_company_idle_cost": logged_company,
                "unlogged_idle_days": unlogged_days,
                "unlogged_company_cost": unlogged_company,
                "total_idle_fixed_cost": total_idle_fixed,
                "total_company_idle_cost": total_company,
                "total_fixed_cost_accounted": accounted,
                "status": status,
            }
            bridges.append(bridge)
            by_month_vehicle[(month, vehicle_id)] = bridge

    return {
        "periods": period_results,
        "bridges": bridges,
        "by_month_vehicle": by_month_vehicle,
    }


def summarize_driver_balances(
    drivers: Sequence[Mapping[str, Any]],
    loads: Sequence[Mapping[str, Any]],
    load_results: Mapping[int, LoadResult],
    payments: Sequence[Mapping[str, Any]],
    idle_state: Mapping[str, Any],
) -> list[dict[str, Any]]:
    load_rows_by_driver: dict[int, list[tuple[Mapping[str, Any], LoadResult]]] = defaultdict(list)
    for load in loads:
        result = load_results.get(int(load["id"]))
        if result and result.included:
            load_rows_by_driver[int(load.get("driver_id") or 0)].append((load, result))
    payments_by_driver: dict[int, float] = defaultdict(float)
    for payment in payments:
        driver_id = int(payment.get("driver_id") or 0)
        if driver_id and payment_counts(payment.get("counts_against_load_pay")):
            payments_by_driver[driver_id] += max(0.0, _num(payment.get("amount")))
    reductions_by_driver: dict[int, float] = defaultdict(float)
    for period in idle_state.get("periods", []):
        driver_id = int(period.get("driver_id") or 0)
        reductions_by_driver[driver_id] += _num(period.get("driver_pay_reduction"))

    balances: list[dict[str, Any]] = []
    for driver in drivers:
        driver_id = int(driver["id"])
        pairs = load_rows_by_driver.get(driver_id, [])
        revenue = sum(_num(load.get("revenue")) for load, _ in pairs)
        miles = sum(result.total_miles for _, result in pairs)
        earned = sum(result.driver_contractor_earned + result.owner_operator_load_pay for _, result in pairs)
        paid = payments_by_driver.get(driver_id, 0.0)
        reduction = reductions_by_driver.get(driver_id, 0.0)
        remaining = max(0.0, round(earned - paid - reduction, 2))
        credit = max(0.0, round(paid + reduction - earned, 2))
        if remaining > 0:
            status = "AMOUNT STILL OWED"
        elif credit > 0:
            status = "COMPANY CREDIT / DRIVER OWES"
        else:
            status = "PAID IN FULL"
        balances.append({
            "driver_id": driver_id,
            "driver_name": driver.get("name", ""),
            "role": driver.get("role", ""),
            "pay_model": driver.get("pay_model", ""),
            "vehicle_id": driver.get("vehicle_id"),
            "included_loads": len(pairs),
            "gross_revenue": revenue,
            "total_miles": miles,
            "load_pay_earned": earned,
            "payments_applied": paid,
            "idle_fixed_cost_pay_reduction": reduction,
            "remaining_load_pay": remaining,
            "company_credit_driver_owes": credit,
            "status": status,
        })
    return balances


def summarize_owner_pay(
    drivers: Sequence[Mapping[str, Any]],
    load_results: Mapping[int, LoadResult],
    payments: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    owner_ids = {int(d["id"]) for d in drivers if str(d.get("role", "")).strip().lower() == "owner" or normalized_pay_model(d.get("pay_model")) == "owner_operator"}
    owner_operator_earned = sum(r.owner_operator_load_pay for r in load_results.values() if r.included)
    company_profit = sum(r.company_profit_before_owner_distribution for r in load_results.values() if r.included)
    distribution_earned = sum(r.owner_profit_distribution for r in load_results.values() if r.included)
    owner_operator_payments = sum(
        max(0.0, _num(p.get("amount")))
        for p in payments
        if int(p.get("driver_id") or 0) in owner_ids
        and payment_counts(p.get("counts_against_load_pay"))
        and str(p.get("payment_type") or "").strip().lower() != "owner profit draw"
    )
    distribution_draws = sum(
        max(0.0, _num(p.get("amount")))
        for p in payments
        if int(p.get("driver_id") or 0) in owner_ids
        and str(p.get("payment_type") or "").strip().lower() == "owner profit draw"
    )
    owner_operator_remaining = max(0.0, owner_operator_earned - owner_operator_payments)
    distribution_remaining = max(0.0, distribution_earned - distribution_draws)
    return {
        "company_profit_before_distribution": company_profit,
        "owner_profit_distribution_earned": distribution_earned,
        "owner_profit_draws_paid": distribution_draws,
        "owner_profit_distribution_remaining": distribution_remaining,
        "owner_operator_load_pay_earned": owner_operator_earned,
        "owner_operator_payments_applied": owner_operator_payments,
        "owner_operator_pay_remaining": owner_operator_remaining,
        "total_owner_earnings": distribution_earned + owner_operator_earned,
        "total_owner_payments_draws": distribution_draws + owner_operator_payments,
        "total_owner_remaining": distribution_remaining + owner_operator_remaining,
    }


def summarize_driver_period(
    drivers: Sequence[Mapping[str, Any]],
    loads: Sequence[Mapping[str, Any]],
    load_results: Mapping[int, LoadResult],
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    result_rows: list[dict[str, Any]] = []
    for driver in drivers:
        driver_id = int(driver["id"])
        pairs: list[tuple[Mapping[str, Any], LoadResult]] = []
        for load in loads:
            if int(load.get("driver_id") or 0) != driver_id:
                continue
            result = load_results.get(int(load["id"]))
            delivery = parse_date(load.get("delivery_date"))
            if result and result.included and delivery and start <= delivery <= end:
                pairs.append((load, result))
        revenue = sum(_num(load.get("revenue")) for load, _ in pairs)
        total_miles = sum(r.total_miles for _, r in pairs)
        driver_pay = sum(r.driver_contractor_earned for _, r in pairs)
        owner_pay = sum(r.owner_operator_load_pay for _, r in pairs)
        company_profit = sum(r.company_profit_before_owner_distribution for _, r in pairs)
        result_rows.append({
            "driver_id": driver_id,
            "driver_name": driver.get("name", ""),
            "pay_model": driver.get("pay_model", ""),
            "loads": len(pairs),
            "revenue": revenue,
            "total_miles": total_miles,
            "driver_contractor_pay": driver_pay,
            "owner_pay": owner_pay,
            "total_pay": driver_pay + owner_pay,
            "company_profit": company_profit,
            "avg_revenue_per_mile": revenue / total_miles if total_miles else 0.0,
        })
    return result_rows


def calculate_monthly_financials(
    settings: Mapping[str, Any],
    overhead_items: Sequence[Mapping[str, Any]],
    loads: Sequence[Mapping[str, Any]],
    load_results: Mapping[int, LoadResult],
    idle_state: Mapping[str, Any],
    months: Sequence[date],
) -> list[dict[str, Any]]:
    monthly_overhead = sum(max(0.0, _num(item.get("monthly_cost"))) for item in overhead_items)
    tax_rate = max(0.0, _num(settings.get("tax_reserve_pct"))) / 100.0
    growth_rate = max(0.0, _num(settings.get("growth_reserve_pct"))) / 100.0
    bridge_rows = idle_state.get("bridges", [])
    rows: list[dict[str, Any]] = []
    for raw_month in months:
        month = month_start(raw_month)
        next_month = add_months(month, 1)
        pairs: list[tuple[Mapping[str, Any], LoadResult]] = []
        for load in loads:
            result = load_results.get(int(load["id"]))
            delivery = parse_date(load.get("delivery_date"))
            if result and result.included and delivery and month <= delivery < next_month:
                pairs.append((load, result))
        revenue = sum(_num(load.get("revenue")) for load, _ in pairs)
        loaded_miles = sum(_num(load.get("loaded_miles")) for load, _ in pairs)
        deadhead_miles = sum(_num(load.get("deadhead_miles")) for load, _ in pairs)
        operating = sum(r.total_operating_expense for _, r in pairs)
        payroll = sum(r.payroll_burden for _, r in pairs)
        driver_pay = sum(r.driver_contractor_earned for _, r in pairs)
        owner_pay = sum(r.owner_operator_load_pay for _, r in pairs)
        company_profit = sum(r.company_profit_before_owner_distribution for _, r in pairs)
        month_bridges = [b for b in bridge_rows if b["month"] == month]
        total_idle_fixed = sum(_num(b.get("total_idle_fixed_cost")) for b in month_bridges)
        driver_idle_reduction = sum(_num(b.get("driver_pay_reduction")) for b in month_bridges)
        company_idle = sum(_num(b.get("total_company_idle_cost")) for b in month_bridges)
        overhead = monthly_overhead if pairs else 0.0
        true_net = company_profit - overhead - company_idle
        margin = true_net / revenue if revenue else 0.0
        tax_reserve = max(0.0, true_net) * tax_rate
        growth_reserve = max(0.0, true_net - tax_reserve) * growth_rate
        cash_after = true_net - tax_reserve - growth_reserve
        rows.append({
            "month": month,
            "revenue": revenue,
            "loads": len(pairs),
            "loaded_miles": loaded_miles,
            "deadhead_miles": deadhead_miles,
            "total_miles": loaded_miles + deadhead_miles,
            "operating_expense": operating,
            "payroll_burden": payroll,
            "driver_contractor_pay": driver_pay,
            "owner_operator_pay": owner_pay,
            "load_company_profit": company_profit,
            "company_overhead": overhead,
            "true_net_after_overhead": true_net,
            "true_net_margin": margin,
            "tax_reserve": tax_reserve,
            "growth_reserve": growth_reserve,
            "cash_after_reserves": cash_after,
            "total_idle_fixed_cost": total_idle_fixed,
            "driver_idle_pay_reduction": driver_idle_reduction,
            "company_idle_fixed_cost": company_idle,
        })
    return rows


def calculate_state(
    settings: Mapping[str, Any],
    overhead_items: Sequence[Mapping[str, Any]],
    drivers: Sequence[Mapping[str, Any]],
    vehicles: Sequence[Mapping[str, Any]],
    weekly_fuel: Sequence[Mapping[str, Any]],
    loads: Sequence[Mapping[str, Any]],
    payments: Sequence[Mapping[str, Any]],
    idle_periods: Sequence[Mapping[str, Any]],
    report_month: date | None = None,
    reporting_months: int = 24,
) -> dict[str, Any]:
    start_month = parse_date(settings.get("reporting_start_month")) or month_start(date.today())
    months = [add_months(month_start(start_month), i) for i in range(reporting_months)]
    report_month = month_start(report_month or parse_date(settings.get("default_report_month")) or date.today())
    if report_month not in months:
        months_for_idle = sorted(set(months + [report_month]))
    else:
        months_for_idle = months

    load_results = calculate_load_results(settings, drivers, weekly_fuel, loads)
    idle_state = calculate_idle_state(drivers, vehicles, loads, load_results, idle_periods, months_for_idle)
    balances = summarize_driver_balances(drivers, loads, load_results, payments, idle_state)
    owner_pay = summarize_owner_pay(drivers, load_results, payments)
    monthly = calculate_monthly_financials(settings, overhead_items, loads, load_results, idle_state, months)

    included = [r for r in load_results.values() if r.included]
    payments_applied = sum(max(0.0, _num(p.get("amount"))) for p in payments if payment_counts(p.get("counts_against_load_pay")))
    monthly_overhead = sum(max(0.0, _num(item.get("monthly_cost"))) for item in overhead_items)
    current_fuel = fuel_price_for(date.today(), weekly_fuel, _num(settings.get("fallback_diesel_price")))
    summary = {
        "total_revenue": sum(_num(load.get("revenue")) for load in loads if load_results.get(int(load["id"])) and load_results[int(load["id"])].included),
        "operating_expense": sum(r.total_operating_expense for r in included),
        "driver_contractor_earned": sum(r.driver_contractor_earned for r in included),
        "owner_operator_pay": sum(r.owner_operator_load_pay for r in included),
        "load_company_profit_before_owner_distribution": sum(r.company_profit_before_owner_distribution for r in included),
        "owner_profit_distribution": sum(r.owner_profit_distribution for r in included),
        "retained_company_profit": sum(r.retained_company_profit for r in included),
        "total_load_pay_remaining": sum(_num(b.get("remaining_load_pay")) for b in balances),
        "current_average_diesel": current_fuel,
        "payments_applied_to_load_pay": payments_applied,
        "monthly_company_overhead": monthly_overhead,
        "included_loads": len(included),
    }
    warnings = {
        "loss_making": sum(1 for r in included if r.decision == "LOSS"),
        "below_target": sum(1 for r in included if r.decision == "BELOW TARGET"),
        "high_deadhead": sum(1 for r in included if r.decision == "HIGH DEADHEAD"),
        "low_company_profit": sum(1 for r in included if r.decision == "LOW COMPANY PROFIT"),
        "idle_input_errors": sum(1 for p in idle_state["periods"] if p["period_status"] not in {"OK", "EXCLUDED"} or p["overlap_status"] != "OK"),
        "fixed_cost_reviews": sum(1 for b in idle_state["bridges"] if b["status"] != "OK"),
    }
    selected_month_bridges = [b for b in idle_state["bridges"] if b["month"] == report_month]
    selected_month_financial = next((row for row in monthly if row["month"] == report_month), None)
    return {
        "load_results": load_results,
        "idle_state": idle_state,
        "driver_balances": balances,
        "owner_pay": owner_pay,
        "monthly_financials": monthly,
        "summary": summary,
        "warnings": warnings,
        "report_month": report_month,
        "selected_month_bridges": selected_month_bridges,
        "selected_month_financial": selected_month_financial,
    }


def _quote_minimum_revenue(
    settings: Mapping[str, Any],
    driver: Mapping[str, Any],
    base_cost_before_revenue_fees: float,
    target_margin_pct: float,
) -> float | None:
    processing = max(0.0, _num(settings.get("processing_fee_pct"))) / 100.0
    burden = max(0.0, _num(settings.get("payroll_burden_pct"))) / 100.0
    pay_model = normalized_pay_model(driver.get("pay_model"))
    if pay_model == "profit_split":
        split = _num(driver.get("driver_profit_split_pct")) / 100.0
        retained_factor = 1.0 - split - (split * burden if _bool(driver.get("payroll_burden_applies")) else 0.0)
        revenue_pay_rate = 0.0
    elif pay_model == "owner_operator":
        retained_factor = 1.0 - _num(driver.get("owner_operator_split_pct")) / 100.0
        revenue_pay_rate = 0.0
    elif pay_model == "contractor_rate_split":
        retained_factor = 1.0
        split = _num(driver.get("contractor_gross_split_pct")) / 100.0
        revenue_pay_rate = split * (1.0 + burden if _bool(driver.get("payroll_burden_applies")) else 1.0)
    else:
        retained_factor = 1.0
        revenue_pay_rate = 0.0
    target = target_margin_pct / 100.0
    denominator = retained_factor * (1.0 - processing) - revenue_pay_rate - target
    if denominator <= 0:
        return None
    admin_fee = max(0.0, _num(settings.get("admin_fee_per_load")))
    return (base_cost_before_revenue_fees + admin_fee) * retained_factor / denominator


def calculate_quote(
    settings: Mapping[str, Any],
    driver: Mapping[str, Any],
    pickup_date: date,
    loaded_miles: float,
    deadhead_miles: float,
    trip_days: int,
    fuel_price: float,
    tolls_misc: float = 0.0,
    other_direct_costs: float = 0.0,
    quoted_revenue: float | None = None,
    target_margin_pct: float | None = None,
) -> QuoteResult:
    loaded = max(0.0, loaded_miles)
    deadhead = max(0.0, deadhead_miles)
    total_miles = loaded + deadhead
    trip_days = max(1, int(trip_days))
    pay_model = normalized_pay_model(driver.get("pay_model"))
    if pay_model == "contractor_rate_split":
        fuel_cost = 0.0
        fixed_cost = 0.0
        maintenance = 0.0
    else:
        mpg = max(0.1, _num(driver.get("mpg"), 0.1))
        fuel_cost = total_miles / mpg * max(0.0, fuel_price)
        fixed_cost = driver_monthly_fixed(driver) / days_in_month(pickup_date) * trip_days
        maintenance = total_miles * max(0.0, _num(driver.get("maintenance_per_mile")))
    tolls_misc = max(0.0, tolls_misc)
    other_direct_costs = max(0.0, other_direct_costs)
    base_cost = fuel_cost + fixed_cost + maintenance + tolls_misc + other_direct_costs
    fixed_compensation = fixed_driver_compensation(driver, loaded, total_miles, trip_days)
    fixed_payroll = fixed_compensation * max(0.0, _num(settings.get("payroll_burden_pct"))) / 100.0 if _bool(driver.get("payroll_burden_applies")) else 0.0
    minimum_base_cost = base_cost + fixed_compensation + fixed_payroll
    target_margin_pct = _num(target_margin_pct, _num(settings.get("target_margin_pct")))
    recommended = _quote_minimum_revenue(settings, driver, minimum_base_cost, target_margin_pct)
    break_even = _quote_minimum_revenue(settings, driver, minimum_base_cost, 0.0)
    premium = recommended * 1.10 if recommended is not None else None
    revenue = max(0.0, _num(quoted_revenue)) if quoted_revenue not in (None, "") else 0.0
    fees = revenue * max(0.0, _num(settings.get("processing_fee_pct"))) / 100.0 + max(0.0, _num(settings.get("admin_fee_per_load"))) if quoted_revenue not in (None, "") else 0.0
    operating = base_cost + fees if quoted_revenue not in (None, "") else base_cost
    profit_before_pay = revenue - operating if quoted_revenue not in (None, "") else 0.0
    driver_pay = 0.0
    owner_pay = 0.0
    if quoted_revenue not in (None, ""):
        if pay_model == "profit_split":
            driver_pay = max(0.0, profit_before_pay * _num(driver.get("driver_profit_split_pct")) / 100.0)
        elif pay_model == "contractor_rate_split":
            driver_pay = max(0.0, revenue * _num(driver.get("contractor_gross_split_pct")) / 100.0)
        elif pay_model == "owner_operator":
            owner_pay = max(0.0, profit_before_pay * _num(driver.get("owner_operator_split_pct")) / 100.0)
        else:
            driver_pay = fixed_compensation
    payroll = driver_pay * max(0.0, _num(settings.get("payroll_burden_pct"))) / 100.0 if _bool(driver.get("payroll_burden_applies")) else 0.0
    company_profit = revenue - operating - driver_pay - owner_pay - payroll if quoted_revenue not in (None, "") else 0.0
    margin = company_profit / revenue if revenue else 0.0
    if quoted_revenue in (None, ""):
        decision = "ENTER QUOTE"
    elif company_profit < 0:
        decision = "DECLINE / REPRICE"
    elif margin < target_margin_pct / 100.0:
        decision = "REPRICE"
    else:
        decision = "MEETS TARGET"
    return QuoteResult(
        total_miles=total_miles,
        fuel_cost=fuel_cost,
        fixed_cost=fixed_cost,
        maintenance_reserve=maintenance,
        company_fees=fees,
        total_operating_expense=operating,
        profit_before_pay=profit_before_pay,
        driver_contractor_pay=driver_pay,
        owner_operator_pay=owner_pay,
        payroll_burden=payroll,
        company_profit=company_profit,
        company_margin_pct=margin,
        all_in_rpm=revenue / total_miles if total_miles and revenue else 0.0,
        recommended_minimum_revenue=recommended,
        recommended_minimum_rpm=recommended / total_miles if recommended is not None and total_miles else None,
        break_even_revenue=break_even,
        target_revenue=recommended,
        premium_revenue=premium,
        decision=decision,
        target_feasible=recommended is not None,
    )
