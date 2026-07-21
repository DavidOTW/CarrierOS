from __future__ import annotations

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
        "payments": row_dicts(query_all("SELECT * FROM payments WHERE organization_id=? ORDER BY paid_at,id", (org_id,))),
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


def selected_month(value: str | None, default: str | None = None) -> date:
    parsed = parse_date(value) or parse_date(default) or date.today().replace(day=1)
    return parsed.replace(day=1)
