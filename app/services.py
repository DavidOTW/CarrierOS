from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from .calculations import calculate_state, parse_date
from .db import as_dict, query_all, query_one


def row_dicts(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def get_organization(org_id: int) -> dict[str, Any]:
    row = query_one("SELECT * FROM organizations WHERE id=?", (org_id,))
    if not row:
        raise LookupError("Organization not found")
    return dict(row)


def get_bundle(org_id: int) -> dict[str, Any]:
    return {
        "settings": get_organization(org_id),
        "overhead_items": row_dicts(query_all("SELECT * FROM overhead_items WHERE organization_id=? ORDER BY sort_order,id", (org_id,))),
        "vehicles": row_dicts(query_all("SELECT * FROM vehicles WHERE organization_id=? ORDER BY active DESC,name", (org_id,))),
        "drivers": row_dicts(query_all("SELECT * FROM drivers WHERE organization_id=? ORDER BY source_row IS NULL,source_row,name", (org_id,))),
        "weekly_fuel": row_dicts(query_all("SELECT * FROM weekly_fuel WHERE organization_id=? ORDER BY week_start", (org_id,))),
        "loads": row_dicts(query_all("SELECT * FROM loads WHERE organization_id=? ORDER BY pickup_date,id", (org_id,))),
        "payments": row_dicts(query_all("SELECT * FROM payments WHERE organization_id=? AND voided_at IS NULL ORDER BY paid_at,id", (org_id,))),
        "idle_periods": row_dicts(query_all("SELECT * FROM idle_periods WHERE organization_id=? ORDER BY start_date,id", (org_id,))),
    }


def get_state(org_id: int, report_month: date | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = get_bundle(org_id)
    state = calculate_state(
        settings=bundle["settings"],
        overhead_items=bundle["overhead_items"],
        drivers=bundle["drivers"],
        vehicles=bundle["vehicles"],
        weekly_fuel=bundle["weekly_fuel"],
        loads=bundle["loads"],
        payments=bundle["payments"],
        idle_periods=bundle["idle_periods"],
        report_month=report_month,
    )
    return bundle, state


def loads_with_results(bundle: dict[str, Any], state: dict[str, Any], newest_first: bool = True) -> list[dict[str, Any]]:
    drivers = {int(d["id"]): d for d in bundle["drivers"]}
    vehicles = {int(v["id"]): v for v in bundle["vehicles"]}
    rows: list[dict[str, Any]] = []
    for load in bundle["loads"]:
        item = dict(load)
        item["driver"] = drivers.get(int(load.get("driver_id") or 0))
        item["vehicle"] = vehicles.get(int(load.get("vehicle_id") or 0))
        item["result"] = state["load_results"].get(int(load["id"]))
        rows.append(item)
    rows.sort(key=lambda r: (r.get("pickup_date") or "", int(r.get("id") or 0)), reverse=newest_first)
    return rows


LOAD_SORT_OPTIONS = (
    ("delivery_desc", "Delivery: newest first"),
    ("delivery_asc", "Delivery: oldest first"),
    ("pickup_desc", "Pickup: newest first"),
    ("pickup_asc", "Pickup: oldest first"),
    ("driver_asc", "Driver: A to Z"),
    ("load_asc", "Load number: A to Z"),
    ("revenue_desc", "Revenue: highest first"),
    ("profit_desc", "Company profit: highest first"),
)


def filter_and_sort_loads(
    rows: list[dict[str, Any]],
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    date_field: str = "delivery_date",
    driver_ids: set[int] | None = None,
    load_ids: set[int] | None = None,
    status: str = "",
    sort: str = "delivery_desc",
) -> list[dict[str, Any]]:
    """Apply Excel-style AND filters to organization-scoped load rows."""
    field = date_field if date_field in {"pickup_date", "delivery_date"} else "delivery_date"
    selected_drivers = driver_ids or set()
    selected_loads = load_ids or set()
    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_date = parse_date(row.get(field))
        if date_from and (row_date is None or row_date < date_from):
            continue
        if date_to and (row_date is None or row_date > date_to):
            continue
        if selected_drivers and int(row.get("driver_id") or 0) not in selected_drivers:
            continue
        if selected_loads and int(row.get("id") or 0) not in selected_loads:
            continue
        if status and str(row.get("status") or "") != status:
            continue
        filtered.append(row)

    allowed_sorts = {value for value, _ in LOAD_SORT_OPTIONS}
    sort = sort if sort in allowed_sorts else "delivery_desc"
    if sort in {"delivery_desc", "delivery_asc", "pickup_desc", "pickup_asc"}:
        sort_field = "delivery_date" if sort.startswith("delivery") else "pickup_date"
        descending = sort.endswith("desc")
        dated = [row for row in filtered if parse_date(row.get(sort_field))]
        undated = [row for row in filtered if not parse_date(row.get(sort_field))]
        dated.sort(
            key=lambda row: (parse_date(row.get(sort_field)), int(row.get("id") or 0)),
            reverse=descending,
        )
        return dated + undated
    if sort == "driver_asc":
        filtered.sort(key=lambda row: (
            str((row.get("driver") or {}).get("name") or "Unassigned").casefold(),
            str(row.get("load_number") or "").casefold(),
        ))
    elif sort == "load_asc":
        filtered.sort(key=lambda row: str(row.get("load_number") or "").casefold())
    elif sort == "revenue_desc":
        filtered.sort(key=lambda row: (float(row.get("revenue") or 0), int(row.get("id") or 0)), reverse=True)
    elif sort == "profit_desc":
        filtered.sort(
            key=lambda row: (
                float(getattr(row.get("result"), "company_profit_before_owner_distribution", 0) or 0),
                int(row.get("id") or 0),
            ),
            reverse=True,
        )
    return filtered


def summarize_load_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    included = [row for row in rows if row.get("result") and row["result"].included]
    revenue = sum(float(row.get("revenue") or 0) for row in included)
    total_miles = sum(float(row["result"].total_miles or 0) for row in included)
    operating = sum(float(row["result"].total_operating_expense or 0) for row in included)
    driver_pay = sum(float(row["result"].driver_contractor_earned or 0) for row in included)
    owner_operator_pay = sum(float(row["result"].owner_operator_load_pay or 0) for row in included)
    company_profit = sum(float(row["result"].company_profit_before_owner_distribution or 0) for row in included)
    owner_distribution = sum(float(row["result"].owner_profit_distribution or 0) for row in included)
    retained = sum(float(row["result"].retained_company_profit or 0) for row in included)
    return {
        "selected_rows": len(rows),
        "included_loads": len(included),
        "excluded_loads": len(rows) - len(included),
        "revenue": revenue,
        "total_miles": total_miles,
        "operating_expense": operating,
        "driver_contractor_pay": driver_pay,
        "owner_operator_pay": owner_operator_pay,
        "total_load_pay": driver_pay + owner_operator_pay,
        "company_profit": company_profit,
        "owner_profit_distribution": owner_distribution,
        "retained_company_profit": retained,
        "avg_revenue_per_mile": revenue / total_miles if total_miles else 0.0,
        "company_margin_pct": company_profit / revenue if revenue else 0.0,
    }


def summarize_load_rows_by_driver(
    rows: list[dict[str, Any]], drivers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    drivers_by_id = {int(driver["id"]): driver for driver in drivers}
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("result") and row["result"].included:
            grouped[int(row.get("driver_id") or 0)].append(row)
    results: list[dict[str, Any]] = []
    for driver_id, driver_rows in grouped.items():
        summary = summarize_load_rows(driver_rows)
        driver = drivers_by_id.get(driver_id, {})
        results.append({
            "driver_id": driver_id,
            "driver_name": driver.get("name") or "Unassigned",
            "pay_model": driver.get("pay_model") or "",
            **summary,
        })
    results.sort(key=lambda row: str(row["driver_name"]).casefold())
    return results


def summarize_load_rows_by_month(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        delivery = parse_date(row.get("delivery_date"))
        if delivery and row.get("result") and row["result"].included:
            grouped[delivery.replace(day=1)].append(row)
    results = [{"month": month, **summarize_load_rows(month_rows)} for month, month_rows in grouped.items()]
    results.sort(key=lambda row: row["month"], reverse=True)
    return results


def selected_month(value: str | None, default: str | None = None) -> date:
    parsed = parse_date(value) or parse_date(default) or date.today().replace(day=1)
    return parsed.replace(day=1)
