from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class Location:
    city: str = ""
    state: str = ""
    postal_code: str = ""
    latitude: float | None = None
    longitude: float | None = None

    @property
    def label(self) -> str:
        locality = ", ".join(part for part in (self.city.strip(), self.state.strip()) if part)
        return " ".join(part for part in (locality, self.postal_code.strip()) if part).strip()


@dataclass(frozen=True)
class RouteEstimate:
    miles: float
    source: str
    confidence: str
    warning: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RouteProvider(Protocol):
    name: str

    def route_miles(self, origin: Location, destination: Location) -> RouteEstimate | None: ...


class ManualRouteProvider:
    """Production-safe default: never invent commercial routing mileage."""

    name = "manual"

    def route_miles(self, origin: Location, destination: Location) -> RouteEstimate | None:
        return None


class EstimatedRouteProvider:
    """Clearly labeled non-commercial estimate for demos and development only."""

    name = "estimated"

    def route_miles(self, origin: Location, destination: Location) -> RouteEstimate | None:
        if None in (origin.latitude, origin.longitude, destination.latitude, destination.longitude):
            return None
        radius = 3958.7613
        lat1, lon1, lat2, lon2 = map(
            math.radians,
            (origin.latitude, origin.longitude, destination.latitude, destination.longitude),
        )
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        straight_line = radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))
        return RouteEstimate(
            miles=round(straight_line * 1.18, 1),
            source=self.name,
            confidence="estimate",
            warning="Non-commercial estimate. Verify practical truck routing before booking.",
        )


class MockRouteProvider:
    """Deterministic routing fixture used by automated tests."""

    name = "mock"

    def __init__(self, routes: Mapping[tuple[str, str], float] | None = None):
        self.routes = {
            (a.casefold(), b.casefold()): float(miles)
            for (a, b), miles in (routes or {}).items()
        }

    def route_miles(self, origin: Location, destination: Location) -> RouteEstimate | None:
        miles = self.routes.get((origin.label.casefold(), destination.label.casefold()))
        if miles is None:
            return None
        return RouteEstimate(miles=miles, source=self.name, confidence="fixture", warning="")


def configured_route_provider() -> RouteProvider:
    provider = os.getenv("CARRIEROS_ROUTE_PROVIDER", "manual").strip().lower()
    if provider == "estimated":
        return EstimatedRouteProvider()
    return ManualRouteProvider()

