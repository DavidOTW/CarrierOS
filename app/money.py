from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000001")
PERCENT_QUANTUM = Decimal("0.0001")
ROUNDING_POLICY = ROUND_HALF_UP


class MoneyInputError(ValueError):
    """Raised when a financial value cannot be parsed without guessing."""


def decimal_value(
    value: Any,
    *,
    field: str,
    default: Decimal | str | int | None = None,
    allow_negative: bool = True,
) -> Decimal:
    """Strictly parse a decimal value.

    Missing values may use an explicit default. Invalid text never becomes zero.
    Floats are converted through ``str`` so their binary representation is not
    carried into the Decimal calculation path.
    """

    if value is None or (isinstance(value, str) and not value.strip()):
        if default is None:
            raise MoneyInputError(f"{field} is required")
        value = default
    if isinstance(value, bool):
        raise MoneyInputError(f"{field} must be a number")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError, AttributeError) as exc:
        raise MoneyInputError(f"{field} must be a valid number") from exc
    if not parsed.is_finite():
        raise MoneyInputError(f"{field} must be finite")
    if not allow_negative and parsed < 0:
        raise MoneyInputError(f"{field} cannot be negative")
    return parsed


def money(value: Any, *, field: str = "amount", allow_negative: bool = True) -> Decimal:
    return decimal_value(
        value,
        field=field,
        allow_negative=allow_negative,
    ).quantize(MONEY_QUANTUM, rounding=ROUNDING_POLICY)


def optional_money(
    value: Any,
    *,
    field: str = "amount",
    allow_negative: bool = True,
) -> Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return money(value, field=field, allow_negative=allow_negative)


def rate(value: Any, *, field: str = "rate", allow_negative: bool = False) -> Decimal:
    return decimal_value(
        value,
        field=field,
        allow_negative=allow_negative,
    ).quantize(RATE_QUANTUM, rounding=ROUNDING_POLICY)


def percentage(
    value: Any,
    *,
    field: str = "percentage",
    allow_negative: bool = False,
) -> Decimal:
    return decimal_value(
        value,
        field=field,
        allow_negative=allow_negative,
    ).quantize(PERCENT_QUANTUM, rounding=ROUNDING_POLICY)


def money_to_cents(value: Any, *, field: str = "amount", allow_negative: bool = True) -> int:
    parsed = money(value, field=field, allow_negative=allow_negative)
    return int(parsed * 100)


def optional_money_to_cents(
    value: Any,
    *,
    field: str = "amount",
    allow_negative: bool = True,
) -> int | None:
    parsed = optional_money(value, field=field, allow_negative=allow_negative)
    return None if parsed is None else int(parsed * 100)


def cents_to_money(value: int) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MoneyInputError("cents must be an integer")
    return (Decimal(value) / 100).quantize(MONEY_QUANTUM, rounding=ROUNDING_POLICY)


def percentage_to_basis_points(value: Any, *, field: str = "percentage") -> int:
    parsed = percentage(value, field=field)
    return int((parsed * 100).quantize(Decimal("1"), rounding=ROUNDING_POLICY))


def basis_points_to_percentage(value: int) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MoneyInputError("basis points must be an integer")
    return (Decimal(value) / 100).quantize(PERCENT_QUANTUM, rounding=ROUNDING_POLICY)


def rate_to_micros(value: Any, *, field: str = "rate") -> int:
    parsed = rate(value, field=field)
    return int((parsed * 1_000_000).quantize(Decimal("1"), rounding=ROUNDING_POLICY))


def micros_to_rate(value: int) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MoneyInputError("rate micros must be an integer")
    return (Decimal(value) / 1_000_000).quantize(RATE_QUANTUM, rounding=ROUNDING_POLICY)
