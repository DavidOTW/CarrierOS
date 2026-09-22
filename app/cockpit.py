from __future__ import annotations

from collections import defaultdict
from datetime import date
import re
from typing import Any, Mapping, Sequence

from .calculations import driver_monthly_fixed, normalized_pay_model, parse_date
from .load_states import LoadState, normalize_state


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _activity_date(load: Mapping[str, Any]) -> date | None:
    return parse_date(load.get("pickup_date")) or parse_date(load.get("delivery_date"))


def _name_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _name_acronym(value: Any) -> str:
    words = _name_key(value).split()
    if len(words) == 1:
        return words[0].replace(" ", "")
    return "".join(word[0] for word in words if word not in {"and", "the", "of"})


def _pay_setup_missing(driver: Mapping[str, Any]) -> bool:
    model = normalized_pay_model(driver.get("pay_model"))
    field = {
        "profit_split": "driver_profit_split_pct",
        "contractor_rate_split": "contractor_gross_split_pct",
        "owner_operator": "owner_operator_split_pct",
        "flat_rate": "flat_rate_per_load",
        "loaded_mile": "pay_per_loaded_mile",
        "total_mile": "pay_per_total_mile",
        "day_rate": "day_rate",
    }.get(model)
    return bool(field and _number(driver.get(field)) <= 0)


def build_ceo_cockpit(
    bundle: Mapping[str, Any],
    state: Mapping[str, Any],
    invoices: Sequence[Mapping[str, Any]],
    *,
    as_of: date,
) -> dict[str, Any]:
    """Build a read-only owner view from the same records as the operating model.

    The cockpit intentionally does not change load-pay or pricing calculations. It
    rearranges existing results into cash, break-even, concentration, and data-
    quality decisions inspired by the owner's load workbook.
    """

    settings = bundle["settings"]
    loads = list(bundle["loads"])
    drivers = list(bundle["drivers"])
    vehicles = list(bundle["vehicles"])
    results = state["load_results"]
    year_start = as_of.replace(month=1, day=1)

    period_loads: list[dict[str, Any]] = []
    excluded_loads: list[dict[str, Any]] = []
    for raw in loads:
        load = dict(raw)
        activity = _activity_date(load)
        if not activity or activity < year_start or activity > as_of:
            continue
        result = results.get(int(load["id"]))
        load["result"] = result
        load["activity_date"] = activity
        if result and result.included:
            period_loads.append(load)
        else:
            excluded_loads.append(load)

    revenue = sum(_number(load.get("revenue")) for load in period_loads)
    allocated_fixed = sum(_number(load["result"].allocated_fixed_cost) for load in period_loads)
    modeled_profit = sum(
        _number(load["result"].company_profit_before_owner_distribution)
        for load in period_loads
    )
    contribution = modeled_profit + allocated_fixed
    contribution_margin = contribution / revenue if revenue else 0.0
    average_revenue_per_load = revenue / len(period_loads) if period_loads else 0.0

    active_drivers = [driver for driver in drivers if int(driver.get("active") or 0)]
    monthly_equipment_fixed = sum(driver_monthly_fixed(driver) for driver in active_drivers)
    monthly_overhead = sum(_number(item.get("monthly_cost")) for item in bundle["overhead_items"])
    monthly_fixed = monthly_equipment_fixed + monthly_overhead
    weekly_fixed = monthly_fixed * 12 / 52
    break_even_monthly = monthly_fixed / contribution_margin if contribution_margin > 0 else 0.0
    break_even_weekly = break_even_monthly * 12 / 52
    loads_needed_weekly = (
        break_even_weekly / average_revenue_per_load if average_revenue_per_load > 0 else 0.0
    )

    active_units = sum(
        1
        for vehicle in vehicles
        if int(vehicle.get("active") or 0)
        and "trailer" not in str(vehicle.get("equipment_type") or "").casefold()
    )
    first_activity = min((load["activity_date"] for load in period_loads), default=None)
    last_activity = max((load["activity_date"] for load in period_loads), default=None)
    elapsed_days = max(1, (last_activity - first_activity).days + 1) if first_activity and last_activity else 1
    actual_revenue_weekly = revenue / elapsed_days * 7 if period_loads else 0.0
    actual_loads_weekly = len(period_loads) / elapsed_days * 7 if period_loads else 0.0

    period_months = [
        row
        for row in state["monthly_financials"]
        if row["month"].year == as_of.year and row["month"] <= as_of.replace(day=1)
    ]
    modeled_surplus = sum(_number(row.get("true_net_after_overhead")) for row in period_months)
    surplus_margin = modeled_surplus / revenue if revenue else 0.0

    open_invoices: list[dict[str, Any]] = []
    buckets = {
        "0–15 days": {"amount": 0.0, "count": 0},
        "16–30 days": {"amount": 0.0, "count": 0},
        "31–45 days": {"amount": 0.0, "count": 0},
        "46–60 days": {"amount": 0.0, "count": 0},
        "Over 60 days": {"amount": 0.0, "count": 0},
    }
    for raw in invoices:
        invoice = dict(raw)
        amount_due = _number(invoice.get("amount_due"))
        if amount_due <= 0:
            continue
        opened = parse_date(invoice.get("delivery_date")) or parse_date(invoice.get("invoice_date"))
        if opened and opened > as_of:
            continue
        days_open = max(0, (as_of - opened).days) if opened else 0
        if days_open <= 15:
            bucket = "0–15 days"
        elif days_open <= 30:
            bucket = "16–30 days"
        elif days_open <= 45:
            bucket = "31–45 days"
        elif days_open <= 60:
            bucket = "46–60 days"
        else:
            bucket = "Over 60 days"
        invoice.update(days_open=days_open, age_bucket=bucket)
        open_invoices.append(invoice)
        buckets[bucket]["amount"] += amount_due
        buckets[bucket]["count"] += 1
    open_invoices.sort(key=lambda row: (row["days_open"], row.get("amount_due", 0)), reverse=True)
    open_ar = sum(_number(row.get("amount_due")) for row in open_invoices)
    ar_over_45 = sum(
        _number(row.get("amount_due")) for row in open_invoices if row["days_open"] > 45
    )

    invoiced_load_ids = {int(row.get("load_id") or 0) for row in invoices if row.get("load_id")}
    delivered_states = {LoadState.DELIVERED_DOCUMENTS_PENDING, LoadState.READY_TO_INVOICE}
    unearned_states = {
        LoadState.BOOKED_AWAITING_RATECON,
        LoadState.RATECON_REVIEW,
        LoadState.NEEDS_ASSIGNMENT,
        LoadState.DISPATCH_AWAITING_APPROVAL,
        LoadState.DISPATCHED_AWAITING_ACK,
        LoadState.DISPATCH_ACKNOWLEDGED,
        LoadState.AT_PICKUP,
        LoadState.IN_TRANSIT,
        LoadState.AT_DELIVERY,
    }
    delivered_not_invoiced = [
        load for load in loads
        if int(load["id"]) not in invoiced_load_ids
        and normalize_state(load.get("status_code") or load.get("status")) in delivered_states
    ]
    proof_blocked = [
        load for load in delivered_not_invoiced
        if normalize_state(load.get("status_code") or load.get("status"))
        == LoadState.DELIVERED_DOCUMENTS_PENDING
    ]
    unearned_loads = [
        load for load in loads
        if normalize_state(load.get("status_code") or load.get("status")) in unearned_states
    ]

    collection_rate = max(0.0, min(100.0, _number(settings.get("ar_collection_rate_pct")))) / 100
    cash_balance = _number(settings.get("cash_balance_today"))
    cash_floor = max(0.0, _number(settings.get("cash_floor")))
    driver_pay_due = sum(max(0.0, _number(row.get("remaining_load_pay"))) for row in state["driver_balances"])
    expected_collections = open_ar * collection_rate
    projected_cash = cash_balance + expected_collections - monthly_fixed - driver_pay_due

    broker_groups: dict[str, dict[str, Any]] = {}
    for load in period_loads:
        broker = str(load.get("broker") or "Unassigned").strip() or "Unassigned"
        key = _name_key(broker) or "unassigned"
        group = broker_groups.setdefault(key, {
            "name": broker,
            "loads": 0,
            "revenue": 0.0,
            "contribution": 0.0,
            "open_ar": 0.0,
            "oldest_open": 0,
        })
        group["loads"] += 1
        group["revenue"] += _number(load.get("revenue"))
        group["contribution"] += (
            _number(load["result"].company_profit_before_owner_distribution)
            + _number(load["result"].allocated_fixed_cost)
        )
    for invoice in open_invoices:
        key = _name_key(invoice.get("customer")) or "unassigned"
        if key not in broker_groups:
            broker_groups[key] = {
                "name": str(invoice.get("customer") or "Unassigned"),
                "loads": 0,
                "revenue": 0.0,
                "contribution": 0.0,
                "open_ar": 0.0,
                "oldest_open": 0,
            }
        broker_groups[key]["open_ar"] += _number(invoice.get("amount_due"))
        broker_groups[key]["oldest_open"] = max(
            int(broker_groups[key]["oldest_open"]), int(invoice["days_open"])
        )
    target_margin = _number(settings.get("target_margin_pct")) / 100
    broker_scorecard = []
    for group in broker_groups.values():
        group["share"] = group["revenue"] / revenue if revenue else 0.0
        group["margin"] = group["contribution"] / group["revenue"] if group["revenue"] else 0.0
        if group["share"] >= 0.30:
            group["verdict"] = "CONCENTRATION RISK"
            group["tone"] = "bad"
        elif group["contribution"] < 0:
            group["verdict"] = "LOSING MONEY"
            group["tone"] = "bad"
        elif group["revenue"] and group["margin"] < target_margin:
            group["verdict"] = "LOW MARGIN"
            group["tone"] = "warn"
        else:
            group["verdict"] = "GOOD"
            group["tone"] = "good"
        broker_scorecard.append(group)
    broker_scorecard.sort(key=lambda row: row["revenue"], reverse=True)
    largest_broker = broker_scorecard[0] if broker_scorecard else None

    ledger_by_driver = {
        int(row.get("driver_id") or 0): _number(row.get("remaining_load_pay"))
        for row in state["driver_balances"]
    }
    loads_by_driver: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for load in period_loads:
        loads_by_driver[int(load.get("driver_id") or 0)].append(load)
    company_contribution_per_load = contribution / len(period_loads) if period_loads else 0.0
    driver_scorecard = []
    for driver in drivers:
        driver_loads = loads_by_driver.get(int(driver["id"]), [])
        driver_revenue = sum(_number(load.get("revenue")) for load in driver_loads)
        driver_contribution = sum(
            _number(load["result"].company_profit_before_owner_distribution)
            + _number(load["result"].allocated_fixed_cost)
            for load in driver_loads
        )
        driver_pay = sum(
            _number(load["result"].driver_contractor_earned)
            + _number(load["result"].owner_operator_load_pay)
            for load in driver_loads
        )
        contribution_per_load = driver_contribution / len(driver_loads) if driver_loads else 0.0
        margin = driver_contribution / driver_revenue if driver_revenue else 0.0
        if not driver_loads:
            verdict, tone = "NO ACTIVITY", "info"
        elif driver_contribution < 0:
            verdict, tone = "LOSING MONEY", "bad"
        elif margin < target_margin:
            verdict, tone = "BELOW TARGET", "warn"
        elif company_contribution_per_load and contribution_per_load >= company_contribution_per_load * 1.25:
            verdict, tone = "TOP PERFORMER", "good"
        else:
            verdict, tone = "ON TARGET", "good"
        driver_scorecard.append({
            "driver_id": int(driver["id"]),
            "name": driver.get("name") or "Unassigned",
            "active": bool(driver.get("active")),
            "pay_model": driver.get("pay_model") or "",
            "loads": len(driver_loads),
            "revenue": driver_revenue,
            "contribution": driver_contribution,
            "margin": margin,
            "contribution_per_load": contribution_per_load,
            "pay": driver_pay,
            "pay_share": driver_pay / driver_revenue if driver_revenue else 0.0,
            "ledger_due": ledger_by_driver.get(int(driver["id"]), 0.0),
            "verdict": verdict,
            "tone": tone,
        })
    driver_scorecard.sort(key=lambda row: (not row["active"], -row["contribution"], row["name"]))

    vehicle_names = {int(vehicle["id"]): vehicle.get("name") or "Unassigned" for vehicle in vehicles}
    loads_by_vehicle: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for load in period_loads:
        loads_by_vehicle[int(load.get("vehicle_id") or 0)].append(load)
    unit_scorecard = []
    for vehicle_id, vehicle_loads in loads_by_vehicle.items():
        unit_revenue = sum(_number(load.get("revenue")) for load in vehicle_loads)
        unit_profit = sum(
            _number(load["result"].company_profit_before_owner_distribution)
            for load in vehicle_loads
        )
        margin = unit_profit / unit_revenue if unit_revenue else 0.0
        verdict = "PROFITABLE" if margin >= target_margin else ("LOW MARGIN" if unit_profit >= 0 else "LOSS")
        tone = "good" if verdict == "PROFITABLE" else ("warn" if verdict == "LOW MARGIN" else "bad")
        unit_scorecard.append({
            "vehicle_id": vehicle_id,
            "name": vehicle_names.get(vehicle_id, "Unassigned"),
            "loads": len(vehicle_loads),
            "revenue": unit_revenue,
            "profit": unit_profit,
            "margin": margin,
            "verdict": verdict,
            "tone": tone,
        })
    unit_scorecard.sort(key=lambda row: row["profit"], reverse=True)

    duplicate_load_ids = len(loads) - len({str(load.get("load_number") or "").casefold() for load in loads})
    missing_unit = sum(
        1 for driver in active_drivers
        if normalized_pay_model(driver.get("pay_model")) != "owner_operator" and not driver.get("vehicle_id")
    )
    missing_pay = sum(1 for driver in active_drivers if _pay_setup_missing(driver))
    names_by_acronym: dict[str, set[str]] = defaultdict(set)
    for load in loads:
        name = str(load.get("broker") or "").strip()
        if name:
            names_by_acronym[_name_acronym(name)].add(name)
    broker_alias_groups = [sorted(names) for names in names_by_acronym.values() if len(names) > 1]
    invoice_mismatches = sum(
        1
        for invoice in invoices
        if invoice.get("load_id")
        and _number(invoice.get("load_revenue")) > 0
        and abs(_number(invoice.get("amount")) - _number(invoice.get("load_revenue"))) > 0.01
    )
    checks = [
        {"label": "Loads excluded from profit", "actual": len(excluded_loads), "status": "REVIEW" if excluded_loads else "PASS", "href": "/loads"},
        {"label": "Active drivers missing a unit", "actual": missing_unit, "status": "REVIEW" if missing_unit else "PASS", "href": "/drivers"},
        {"label": "Active drivers missing pay setup", "actual": missing_pay, "status": "REVIEW" if missing_pay else "PASS", "href": "/drivers"},
        {"label": "Duplicate load IDs", "actual": duplicate_load_ids, "status": "REVIEW" if duplicate_load_ids else "PASS", "href": "/loads"},
        {"label": "Possible broker naming duplicates", "actual": len(broker_alias_groups), "status": "REVIEW" if broker_alias_groups else "PASS", "href": "/loads"},
        {"label": "Invoice / load amount differences", "actual": invoice_mismatches, "status": "REVIEW" if invoice_mismatches else "PASS", "href": "/receivables"},
    ]

    days_stale = (as_of - last_activity).days if last_activity else None
    decisions = []
    if delivered_not_invoiced:
        decisions.append({"tone": "bad", "title": "Invoice delivered loads", "detail": f"{len(delivered_not_invoiced)} load(s) worth ${sum(_number(load.get('revenue')) for load in delivered_not_invoiced):,.2f} are delivered without an invoice.", "href": "/receivables"})
    if ar_over_45 > 0:
        decisions.append({"tone": "bad", "title": "Collect aging receivables", "detail": f"${ar_over_45:,.2f} has been open more than 45 days.", "href": "/receivables"})
    cash_planning_active = bool(period_loads or open_ar or monthly_fixed or driver_pay_due or cash_balance)
    if cash_planning_active and projected_cash < cash_floor:
        decisions.append({"tone": "bad", "title": "Protect the cash floor", "detail": f"The 30-day projection is ${cash_floor - projected_cash:,.2f} below your floor.", "href": "/settings"})
    if largest_broker and largest_broker["share"] >= 0.30:
        decisions.append({"tone": "warn", "title": "Reduce customer concentration", "detail": f"{largest_broker['name']} represents {largest_broker['share']:.1%} of year-to-date revenue.", "href": "#broker-scorecard"})
    if revenue and contribution_margin < target_margin:
        decisions.append({"tone": "warn", "title": "Raise contribution margin", "detail": f"Contribution margin is {contribution_margin:.1%} against a {target_margin:.1%} target.", "href": "/financials"})
    if excluded_loads:
        decisions.append({"tone": "warn", "title": "Complete load inputs", "detail": f"{len(excluded_loads)} load(s) are excluded from modeled profit.", "href": "/loads"})
    if days_stale is None or days_stale > 14:
        freshness = "No dated loads are available." if days_stale is None else f"The newest dated load is {days_stale} days old."
        decisions.append({"tone": "info", "title": "Refresh operating data", "detail": freshness, "href": "/loads/new"})

    planned_change = _number(settings.get("planned_fixed_cost_change_monthly"))
    planned_date = parse_date(settings.get("planned_fixed_cost_change_date"))
    future_fixed = max(0.0, monthly_fixed + planned_change)
    future_break_even = future_fixed / contribution_margin if contribution_margin > 0 else 0.0

    return {
        "as_of": as_of,
        "year_start": year_start,
        "revenue": revenue,
        "contribution": contribution,
        "contribution_margin": contribution_margin,
        "modeled_surplus": modeled_surplus,
        "surplus_margin": surplus_margin,
        "target_margin": target_margin,
        "included_loads": len(period_loads),
        "excluded_loads": len(excluded_loads),
        "open_ar": open_ar,
        "oldest_open": max((row["days_open"] for row in open_invoices), default=0),
        "ar_over_45": ar_over_45,
        "ar_buckets": [{"label": label, **value, "share": value["amount"] / open_ar if open_ar else 0.0} for label, value in buckets.items()],
        "open_invoices": open_invoices,
        "delivered_not_invoiced": delivered_not_invoiced,
        "delivered_not_invoiced_amount": sum(_number(load.get("revenue")) for load in delivered_not_invoiced),
        "proof_blocked": proof_blocked,
        "proof_blocked_amount": sum(_number(load.get("revenue")) for load in proof_blocked),
        "unearned_loads": unearned_loads,
        "unearned_amount": sum(_number(load.get("revenue")) for load in unearned_loads),
        "cash_balance": cash_balance,
        "cash_floor": cash_floor,
        "collection_rate": collection_rate,
        "expected_collections": expected_collections,
        "driver_pay_due": driver_pay_due,
        "projected_cash": projected_cash,
        "cash_headroom": projected_cash - cash_floor,
        "monthly_equipment_fixed": monthly_equipment_fixed,
        "monthly_overhead": monthly_overhead,
        "monthly_fixed": monthly_fixed,
        "weekly_fixed": weekly_fixed,
        "break_even_monthly": break_even_monthly,
        "break_even_weekly": break_even_weekly,
        "average_revenue_per_load": average_revenue_per_load,
        "loads_needed_weekly": loads_needed_weekly,
        "loads_needed_per_unit": loads_needed_weekly / active_units if active_units else 0.0,
        "actual_revenue_weekly": actual_revenue_weekly,
        "actual_loads_weekly": actual_loads_weekly,
        "actual_loads_per_unit": actual_loads_weekly / active_units if active_units else 0.0,
        "active_units": active_units,
        "first_activity": first_activity,
        "last_activity": last_activity,
        "days_stale": days_stale,
        "planned_change_date": planned_date,
        "planned_fixed_change": planned_change,
        "future_fixed": future_fixed,
        "future_break_even": future_break_even,
        "future_break_even_weekly": future_break_even * 12 / 52,
        "decisions": decisions,
        "checks": checks,
        "review_checks": sum(1 for check in checks if check["status"] == "REVIEW"),
        "broker_alias_groups": broker_alias_groups,
        "broker_scorecard": broker_scorecard,
        "driver_scorecard": driver_scorecard,
        "company_contribution_per_load": company_contribution_per_load,
        "unit_scorecard": unit_scorecard,
    }
