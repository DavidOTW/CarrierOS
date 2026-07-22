from __future__ import annotations

from enum import StrEnum

from .load_states import LoadState, LoadStateError, normalize_state, validate_transition


class DeliveryDocumentKind(StrEnum):
    BOL = "BOL"
    POD = "POD"
    RECEIPT = "RECEIPT"
    DETENTION_EVIDENCE = "DETENTION_EVIDENCE"


DRIVER_STATUS_TARGETS = frozenset(
    {
        LoadState.AT_PICKUP,
        LoadState.IN_TRANSIT,
        LoadState.AT_DELIVERY,
        LoadState.DELIVERED_DOCUMENTS_PENDING,
    }
)


def parse_driver_status(value: str) -> LoadState:
    try:
        state = LoadState(str(value or "").strip().upper())
    except ValueError as exc:
        raise LoadStateError("Choose a valid delivery status") from exc
    if state not in DRIVER_STATUS_TARGETS:
        raise LoadStateError("Drivers may only update pickup, transit, delivery, and document status")
    return state


def validate_driver_transition(current: str, target: str) -> LoadState:
    target_state = parse_driver_status(target)
    current_state = normalize_state(current)
    return validate_transition(current_state, target_state)


def parse_delivery_document_kind(value: str) -> DeliveryDocumentKind:
    try:
        return DeliveryDocumentKind(str(value or "").strip().upper())
    except ValueError as exc:
        raise ValueError("Choose a BOL, POD, receipt, or detention-evidence document") from exc
