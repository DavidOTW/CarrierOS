from __future__ import annotations

import sqlite3
from enum import StrEnum
from typing import Any


class LoadStateError(ValueError):
    pass


class LoadState(StrEnum):
    BOOKED_AWAITING_RATECON = "BOOKED_AWAITING_RATECON"
    RATECON_REVIEW = "RATECON_REVIEW"
    NEEDS_ASSIGNMENT = "NEEDS_ASSIGNMENT"
    DISPATCH_AWAITING_APPROVAL = "DISPATCH_AWAITING_APPROVAL"
    DISPATCHED_AWAITING_ACK = "DISPATCHED_AWAITING_ACK"
    DISPATCH_ACKNOWLEDGED = "DISPATCH_ACKNOWLEDGED"
    AT_PICKUP = "AT_PICKUP"
    IN_TRANSIT = "IN_TRANSIT"
    AT_DELIVERY = "AT_DELIVERY"
    DELIVERED_DOCUMENTS_PENDING = "DELIVERED_DOCUMENTS_PENDING"
    READY_TO_INVOICE = "READY_TO_INVOICE"
    INVOICED = "INVOICED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    SETTLEMENT_PENDING = "SETTLEMENT_PENDING"
    SETTLED = "SETTLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset({LoadState.CLOSED, LoadState.CANCELLED})


ALLOWED_TRANSITIONS: dict[LoadState, frozenset[LoadState]] = {
    LoadState.BOOKED_AWAITING_RATECON: frozenset(
        {LoadState.RATECON_REVIEW, LoadState.CANCELLED}
    ),
    LoadState.RATECON_REVIEW: frozenset(
        {LoadState.NEEDS_ASSIGNMENT, LoadState.CANCELLED}
    ),
    LoadState.NEEDS_ASSIGNMENT: frozenset(
        {LoadState.DISPATCH_AWAITING_APPROVAL, LoadState.CANCELLED}
    ),
    LoadState.DISPATCH_AWAITING_APPROVAL: frozenset(
        {LoadState.NEEDS_ASSIGNMENT, LoadState.DISPATCHED_AWAITING_ACK, LoadState.CANCELLED}
    ),
    LoadState.DISPATCHED_AWAITING_ACK: frozenset(
        {LoadState.DISPATCH_AWAITING_APPROVAL, LoadState.DISPATCH_ACKNOWLEDGED, LoadState.CANCELLED}
    ),
    LoadState.DISPATCH_ACKNOWLEDGED: frozenset(
        {LoadState.AT_PICKUP, LoadState.CANCELLED}
    ),
    LoadState.AT_PICKUP: frozenset({LoadState.IN_TRANSIT, LoadState.CANCELLED}),
    LoadState.IN_TRANSIT: frozenset({LoadState.AT_DELIVERY}),
    LoadState.AT_DELIVERY: frozenset({LoadState.DELIVERED_DOCUMENTS_PENDING}),
    LoadState.DELIVERED_DOCUMENTS_PENDING: frozenset({LoadState.READY_TO_INVOICE}),
    LoadState.READY_TO_INVOICE: frozenset({LoadState.INVOICED}),
    LoadState.INVOICED: frozenset({LoadState.PARTIALLY_PAID, LoadState.PAID}),
    LoadState.PARTIALLY_PAID: frozenset({LoadState.PARTIALLY_PAID, LoadState.PAID}),
    LoadState.PAID: frozenset({LoadState.SETTLEMENT_PENDING}),
    LoadState.SETTLEMENT_PENDING: frozenset({LoadState.SETTLED}),
    LoadState.SETTLED: frozenset({LoadState.CLOSED}),
    LoadState.CLOSED: frozenset(),
    LoadState.CANCELLED: frozenset(),
}


LEGACY_STATE_MAP = {
    "booked": LoadState.BOOKED_AWAITING_RATECON,
    "booked — awaiting ratecon": LoadState.BOOKED_AWAITING_RATECON,
    "booked â€” awaiting ratecon": LoadState.BOOKED_AWAITING_RATECON,
    "ratecon review": LoadState.RATECON_REVIEW,
    "planned": LoadState.NEEDS_ASSIGNMENT,
    "dispatched": LoadState.DISPATCHED_AWAITING_ACK,
    "at pickup": LoadState.AT_PICKUP,
    "in transit": LoadState.IN_TRANSIT,
    "at delivery": LoadState.AT_DELIVERY,
    "delivered": LoadState.DELIVERED_DOCUMENTS_PENDING,
    "invoiced": LoadState.INVOICED,
    "partially paid": LoadState.PARTIALLY_PAID,
    "paid": LoadState.PAID,
    "closed": LoadState.CLOSED,
    "cancelled": LoadState.CANCELLED,
    "canceled": LoadState.CANCELLED,
}


def normalize_state(value: Any) -> LoadState:
    """Map a legacy stored status to a canonical state during migration/read compatibility."""

    if isinstance(value, LoadState):
        return value
    text = str(value or "").strip()
    try:
        return LoadState(text.upper().replace(" ", "_").replace("-", "_"))
    except ValueError:
        mapped = LEGACY_STATE_MAP.get(text.casefold())
        if mapped is None:
            return LoadState.BOOKED_AWAITING_RATECON
        return mapped


def strict_state(value: LoadState | str) -> LoadState:
    """Parse a new state value without silently accepting free text."""

    if isinstance(value, LoadState):
        return value
    text = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    try:
        return LoadState(text)
    except ValueError as exc:
        raise LoadStateError(f"Unknown load state: {value!r}") from exc


def validate_transition(current: LoadState | str, target: LoadState | str) -> LoadState:
    current_state = normalize_state(current)
    target_state = strict_state(target)
    if target_state == current_state:
        return target_state
    if target_state not in ALLOWED_TRANSITIONS[current_state]:
        raise LoadStateError(
            f"Cannot move load from {current_state.value} to {target_state.value}"
        )
    return target_state


def transition_load_state(
    conn: sqlite3.Connection,
    *,
    organization_id: int,
    load_id: int,
    target: LoadState | str,
    actor_user_id: int | None,
    idempotency_key: str,
    reason: str | None = None,
) -> sqlite3.Row:
    """Apply one tenant-scoped, auditable and retry-safe transition."""

    key = str(idempotency_key or "").strip()
    if not key:
        raise LoadStateError("An idempotency key is required")
    target_state = strict_state(target)
    existing = conn.execute(
        """SELECT * FROM load_status_history
        WHERE organization_id=? AND idempotency_key=?""",
        (organization_id, key),
    ).fetchone()
    if existing:
        if int(existing["load_id"]) != int(load_id):
            raise LoadStateError("Idempotency key was already used for another load")
        if existing["new_status"] != target_state.value:
            raise LoadStateError("Idempotency key was already used for another target state")
        return existing
    load = conn.execute(
        "SELECT id, status_code FROM loads WHERE id=? AND organization_id=?",
        (load_id, organization_id),
    ).fetchone()
    if not load:
        raise LookupError("Load not found")
    if actor_user_id is not None:
        actor = conn.execute(
            "SELECT id FROM users WHERE id=? AND organization_id=?",
            (actor_user_id, organization_id),
        ).fetchone()
        if not actor:
            raise LoadStateError("Transition actor does not belong to the load organization")
    current = normalize_state(load["status_code"])
    target_state = validate_transition(current, target_state)
    if target_state == current:
        raise LoadStateError("Same-state retries must use the original idempotency key")
    cursor = conn.execute(
        """INSERT INTO load_status_history
        (organization_id, load_id, prior_status, new_status, changed_by,
         idempotency_key, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            organization_id,
            load_id,
            current.value,
            target_state.value,
            actor_user_id,
            key,
            str(reason or "").strip() or None,
        ),
    )
    conn.execute(
        """UPDATE loads SET status_code=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND organization_id=?""",
        (target_state.value, load_id, organization_id),
    )
    return conn.execute(
        "SELECT * FROM load_status_history WHERE id=?",
        (cursor.lastrowid,),
    ).fetchone()
