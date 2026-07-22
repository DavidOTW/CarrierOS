from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .opportunities import OpportunityResult, compare_drivers
from .routing import RouteProvider


HOS_DISCLAIMER = "Schedule estimate only — driver HOS must be independently verified."


@dataclass(frozen=True)
class AssignmentCandidate:
    driver: dict[str, Any]
    power_unit: dict[str, Any] | None
    trailer: dict[str, Any] | None
    location: dict[str, Any] | None
    result: OpportunityResult
    deadhead_source: str
    eligible: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    recommendation: str


def _equipment_compatible(requirement: str, trailer: Mapping[str, Any] | None) -> bool:
    required = requirement.casefold().strip()
    if not required or required in {"truck", "tractor", "power only", "any"}:
        return True
    if trailer is None:
        return False
    actual = str(trailer.get("trailer_type") or "").casefold()
    aliases = {
        "dry van": ("dry", "van"),
        "reefer": ("reefer", "refrigerated"),
        "flatbed": ("flatbed", "flat bed"),
        "step deck": ("step", "drop deck"),
        "box truck": ("box", "straight"),
    }
    terms = aliases.get(required, (required,))
    return any(term in actual for term in terms)


def rank_assignments(
    settings: Mapping[str, Any],
    load: Mapping[str, Any],
    drivers: Sequence[Mapping[str, Any]],
    power_units_by_driver: Mapping[int, Mapping[str, Any] | None],
    trailers: Sequence[Mapping[str, Any]],
    locations: Mapping[int, Mapping[str, Any]],
    route_provider: RouteProvider,
    *,
    schedule_blockers: Mapping[int, Sequence[str]] | None = None,
    compliance_blockers: Mapping[int, Sequence[str]] | None = None,
    fuel_price: float | None = None,
) -> list[AssignmentCandidate]:
    opportunity = {
        "original_offered_rate": load.get("final_agreed_rate") or load.get("revenue") or 0,
        "origin_city": load.get("origin_city") or "",
        "origin_state": load.get("origin_state") or "",
        "origin_postal_code": load.get("origin_postal_code") or "",
        "destination_city": load.get("destination_city") or "",
        "destination_state": load.get("destination_state") or "",
        "destination_postal_code": load.get("destination_postal_code") or "",
        "pickup_at": load.get("pickup_at") or load.get("pickup_date") or "",
        "delivery_at": load.get("delivery_at") or load.get("delivery_date") or "",
        "loaded_miles": load.get("loaded_miles") or 0,
        "deadhead_miles": load.get("deadhead_miles") or 0,
        "tolls": load.get("tolls_misc") or 0,
        "misc_expenses": load.get("other_direct_costs") or 0,
    }
    rows = compare_drivers(
        settings,
        drivers,
        opportunity,
        locations,
        route_provider,
        fuel_price=fuel_price,
    )
    candidates: list[AssignmentCandidate] = []
    for row in rows:
        driver = dict(row["driver"])
        driver_id = int(driver["id"])
        power_unit = power_units_by_driver.get(driver_id)
        trailer = next(
            (
                dict(item)
                for item in trailers
                if bool(item.get("active", 1))
                and _equipment_compatible(str(load.get("equipment_requirement") or ""), item)
            ),
            None,
        )
        blockers = list((schedule_blockers or {}).get(driver_id, ()))
        blockers.extend((compliance_blockers or {}).get(driver_id, ()))
        if not bool(driver.get("active", 1)):
            blockers.append("Driver is inactive")
        if not power_unit or not bool(power_unit.get("active", 1)):
            blockers.append("No active power unit is assigned")
        requirement = str(load.get("equipment_requirement") or "")
        if requirement and not _equipment_compatible(requirement, trailer):
            blockers.append(f"No active trailer matches {requirement}")
        warnings = list(row["result"].warnings)
        warnings.append(HOS_DISCLAIMER)
        eligible = not blockers
        recommendation = (
            "RECOMMENDED"
            if eligible and row["result"].recommendation == "BOOK"
            else "REVIEW"
            if eligible
            else "INELIGIBLE"
        )
        candidates.append(
            AssignmentCandidate(
                driver,
                dict(power_unit) if power_unit else None,
                trailer,
                dict(row["location"]) if row["location"] else None,
                row["result"],
                str(row["deadhead_source"]),
                eligible,
                tuple(blockers),
                tuple(dict.fromkeys(warnings)),
                recommendation,
            )
        )
    candidates.sort(
        key=lambda item: (
            not item.eligible,
            item.recommendation != "RECOMMENDED",
            -item.result.company_profit,
            item.result.deadhead_miles,
            str(item.driver.get("name") or "").casefold(),
        )
    )
    return candidates
