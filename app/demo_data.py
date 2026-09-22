from __future__ import annotations

from datetime import date, timedelta
from typing import Any


FREE_TIER_COPY = (
    "1 active power unit free forever — no card required. "
    "Pay only when you add a second unit."
)


_SAMPLE_LOADS: tuple[dict[str, Any], ...] = (
    {
        "number": "FRT-1048",
        "broker": "Acme Brokerage",
        "origin": "Nashville, TN",
        "destination": "Charlotte, NC",
        "origin_short": "Nashville",
        "destination_short": "Charlotte",
        "driver": "Marcus Hill",
        "unit": "Unit 03",
        "status": "In transit",
        "status_class": "blue",
        "pickup_offset": -3,
        "delivery_offset": -2,
        "miles": 522,
        "deadhead": 84,
        "revenue": "$3,250",
        "operating_expense": "$1,038",
        "load_pay": "$1,300",
        "profit": "$912",
        "decision": "OK",
        "decision_class": "green",
    },
    {
        "number": "FRT-1047",
        "broker": "Prime Freight",
        "origin": "Louisville, KY",
        "destination": "Atlanta, GA",
        "origin_short": "Louisville",
        "destination_short": "Atlanta",
        "driver": "Sarah Reed",
        "unit": "Unit 02",
        "status": "Delivered",
        "status_class": "green",
        "pickup_offset": -4,
        "delivery_offset": -3,
        "miles": 421,
        "dispatch_miles": 487,
        "deadhead": 66,
        "revenue": "$2,890",
        "operating_expense": "$1,019",
        "load_pay": "$1,087",
        "profit": "$784",
        "decision": "OK",
        "decision_class": "green",
    },
    {
        "number": "FRT-1046",
        "broker": "Blue Line Logistics",
        "origin": "Memphis, TN",
        "destination": "Dallas, TX",
        "origin_short": "Memphis",
        "destination_short": "Dallas",
        "driver": "Devon Carter",
        "unit": "Unit 05",
        "status": "At pickup",
        "status_class": "orange",
        "pickup_offset": -3,
        "delivery_offset": -1,
        "miles": 913,
        "deadhead": 90,
        "revenue": "$4,680",
        "operating_expense": "$1,720",
        "load_pay": "$1,184",
        "profit": "$1,246",
        "decision": "OK",
        "decision_class": "green",
    },
    {
        "number": "FRT-1045",
        "broker": "Riverbend Transport",
        "origin": "Knoxville, TN",
        "destination": "Raleigh, NC",
        "origin_short": "Knoxville",
        "destination_short": "Raleigh",
        "driver": "Marcus Hill",
        "unit": "Unit 03",
        "status": "Planned",
        "status_class": "gray",
        "pickup_offset": -1,
        "delivery_offset": 0,
        "miles": 412,
        "deadhead": 51,
        "revenue": "$2,640",
        "operating_expense": "$972",
        "load_pay": "$1,000",
        "profit": "$668",
        "decision": "OK",
        "decision_class": "green",
    },
    {
        "number": "FRT-1044",
        "broker": "Summit Logistics",
        "origin": "Chattanooga, TN",
        "destination": "Birmingham, AL",
        "origin_short": "Chattanooga",
        "destination_short": "Birmingham",
        "driver": "Sarah Reed",
        "unit": "Unit 02",
        "status": "Delivered",
        "status_class": "green",
        "pickup_offset": -5,
        "delivery_offset": -5,
        "miles": 166,
        "deadhead": 28,
        "revenue": "$1,480",
        "operating_expense": "$590",
        "load_pay": "$464",
        "profit": "$426",
        "decision": "OK",
        "decision_class": "green",
    },
    {
        "number": "FRT-1043",
        "broker": "Sample Freight Co.",
        "origin": "Bowling Green, KY",
        "destination": "Columbus, OH",
        "origin_short": "Bowling Green",
        "destination_short": "Columbus",
        "driver": "Devon Carter",
        "unit": "Unit 05",
        "status": "Delivered",
        "status_class": "green",
        "pickup_offset": -7,
        "delivery_offset": -6,
        "miles": 397,
        "deadhead": 101,
        "revenue": "$1,980",
        "operating_expense": "$913",
        "load_pay": "$650",
        "profit": "$417",
        "decision": "Review",
        "decision_class": "orange",
    },
)


def _short_date(value: date) -> str:
    return f"{value.strftime('%b')} {value.day}"


def build_public_sample_data(as_of: date | None = None) -> dict[str, Any]:
    """Build fictional marketing/demo dates from one request-time anchor."""
    anchor = as_of or date.today()
    loads: list[dict[str, Any]] = []
    for source in _SAMPLE_LOADS:
        pickup_date = anchor + timedelta(days=source["pickup_offset"])
        delivery_date = anchor + timedelta(days=source["delivery_offset"])
        load = dict(source)
        load.update(
            {
                "pickup_date": pickup_date.isoformat(),
                "delivery_date": delivery_date.isoformat(),
                "pickup_label": _short_date(pickup_date),
                "delivery_label": _short_date(delivery_date),
                "lane": f"{source['origin_short']} → {source['destination_short']}",
                "dispatch_miles": source.get("dispatch_miles", source["miles"]),
            }
        )
        loads.append(load)

    by_number = {load["number"]: load for load in loads}
    week_start = anchor - timedelta(days=anchor.weekday())
    relative_dates = {
        "payment_primary": _short_date(anchor - timedelta(days=6)),
        "payment_owner": _short_date(anchor - timedelta(days=5)),
        "document_generated": _short_date(anchor - timedelta(days=3)),
        "invoice_recent": _short_date(anchor - timedelta(days=2)),
        "invoice_older": _short_date(anchor - timedelta(days=31)),
        "detention_sent": _short_date(anchor - timedelta(days=6)),
        "fuel_week_start": _short_date(week_start),
        "insurance_renewal": _short_date(anchor + timedelta(days=19)),
        "annual_inspection": _short_date(anchor + timedelta(days=40)),
        "medical_certificate": _short_date(anchor + timedelta(days=117)),
        "trailer_registration": _short_date(anchor + timedelta(days=33)),
    }
    return {
        "as_of": anchor.isoformat(),
        "week_label": f"Week {anchor.isocalendar().week}",
        "month_label": anchor.strftime("%B"),
        "previous_month_label": (anchor.replace(day=1) - timedelta(days=1)).strftime("%B"),
        "month_to_date_label": f"{anchor.strftime('%B')} month to date",
        "loads": loads,
        "loads_by_number": by_number,
        "marketing_loads": loads[:3],
        "active_loads": loads[:4],
        "dispatch_loads": loads[:5],
        "report_loads": [by_number[number] for number in ("FRT-1048", "FRT-1047", "FRT-1043")],
        "dates": relative_dates,
    }
