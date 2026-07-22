from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    DISPATCHER = "dispatcher"
    ACCOUNTING = "accounting"
    COMPLIANCE = "compliance"
    READ_ONLY = "read_only"
    DRIVER = "driver"


PERMISSION_MATRIX: dict[Role, frozenset[str]] = {
    Role.OWNER: frozenset({"*"}),
    Role.ADMINISTRATOR: frozenset({"*"}),
    Role.DISPATCHER: frozenset(
        {
            "dashboard.view",
            "quotes.view",
            "quotes.manage",
            "loads.view",
            "loads.manage",
            "dispatch.approve",
            "documents.view_operational",
        }
    ),
    Role.ACCOUNTING: frozenset(
        {
            "dashboard.view",
            "loads.view",
            "money.view",
            "money.manage",
            "invoices.manage",
            "payments.manage",
            "settlements.manage",
            "documents.view_financial",
        }
    ),
    Role.COMPLIANCE: frozenset(
        {
            "dashboard.view",
            "loads.view",
            "compliance.view",
            "compliance.manage",
            "documents.view_operational",
        }
    ),
    Role.READ_ONLY: frozenset(
        {"dashboard.view", "quotes.view", "loads.view", "money.view", "compliance.view"}
    ),
    Role.DRIVER: frozenset(
        {
            "driver.loads.view_assigned",
            "driver.dispatch.acknowledge",
            "driver.status.update",
            "driver.documents.upload",
            "driver.settlement.view_own",
            "driver.settlement.respond",
        }
    ),
}


def normalize_role(value: str | Role | None, *, legacy_admin: bool = False) -> Role:
    if isinstance(value, Role):
        return value
    text = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "admin": Role.ADMINISTRATOR,
        "administrator": Role.ADMINISTRATOR,
        "readonly": Role.READ_ONLY,
        "read_only": Role.READ_ONLY,
    }
    try:
        return Role(text)
    except ValueError:
        return aliases.get(text, Role.OWNER if legacy_admin else Role.READ_ONLY)


def has_permission(role: str | Role, permission: str) -> bool:
    normalized = normalize_role(role)
    grants = PERMISSION_MATRIX[normalized]
    return "*" in grants or permission in grants
