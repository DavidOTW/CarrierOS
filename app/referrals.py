from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


REFERRAL_COMMISSION_BPS = 5_000
REFERRAL_COMMISSION_RATE = REFERRAL_COMMISSION_BPS / 10_000
REFERRAL_HOLD_DAYS = 30
REFERRAL_TERMS_VERSION = "2026-07-24-recurring-50-v1"
REFERRAL_CODE_PATTERN = re.compile(r"^[A-Z0-9]{10,24}$")


def object_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def normalize_referral_code(value: Any) -> str:
    code = re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()
    return code if REFERRAL_CODE_PATTERN.fullmatch(code) else ""


def new_referral_code() -> str:
    return f"COS{secrets.token_hex(5).upper()}"


def new_referral_portal_token() -> str:
    return secrets.token_urlsafe(32)


def referral_token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def referral_invoice_basis_cents(invoice: Any) -> int:
    """Return collected subscription revenue excluding separately stated tax.

    Stripe's amount_paid is the hard cap: credits, discounts, or an unpaid
    invoice can never create a commission larger than cash actually collected.
    """
    amount_paid = max(0, int(object_value(invoice, "amount_paid") or 0))
    if amount_paid <= 0:
        return 0
    excluding_tax = object_value(invoice, "total_excluding_tax")
    if excluding_tax is None:
        excluding_tax = object_value(invoice, "subtotal_excluding_tax")
    if excluding_tax is None:
        return amount_paid
    return min(amount_paid, max(0, int(excluding_tax or 0)))


def referral_commission_cents(basis_cents: int) -> int:
    return max(0, int(basis_cents)) * REFERRAL_COMMISSION_BPS // 10_000


def _invoice_paid_at(invoice: Any) -> datetime:
    transitions = object_value(invoice, "status_transitions") or {}
    paid_at = object_value(transitions, "paid_at")
    if paid_at:
        try:
            return datetime.fromtimestamp(int(paid_at), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    return datetime.now(timezone.utc)


def _invoice_charge_id(invoice: Any) -> str | None:
    direct_charge = str(object_value(invoice, "charge") or "")
    if direct_charge.startswith("ch_"):
        return direct_charge
    payments = object_value(invoice, "payments") or {}
    payment_rows = object_value(payments, "data") or []
    for row in payment_rows:
        payment = object_value(row, "payment") or {}
        charge = str(object_value(payment, "charge") or "")
        if charge.startswith("ch_"):
            return charge
    return None


def record_referral_commission(conn: Any, organization: Any, invoice: Any) -> int | None:
    invoice_id = str(object_value(invoice, "id") or "")
    if not invoice_id.startswith("in_"):
        return None
    attribution = conn.execute(
        """SELECT a.*, p.source_organization_id, p.display_name, p.email
        FROM referral_attributions a
        JOIN referral_partners p ON p.id=a.referral_partner_id
        WHERE a.referred_organization_id=? AND p.active=1
          AND p.terms_accepted_at IS NOT NULL""",
        (organization["id"],),
    ).fetchone()
    if not attribution:
        return None
    if int(attribution["source_organization_id"] or 0) == int(organization["id"]):
        return None
    basis_cents = referral_invoice_basis_cents(invoice)
    commission_cents = referral_commission_cents(basis_cents)
    if basis_cents <= 0 or commission_cents <= 0:
        return None
    paid_at = _invoice_paid_at(invoice)
    eligible_on = (paid_at.date() + timedelta(days=REFERRAL_HOLD_DAYS)).isoformat()
    cursor = conn.execute(
        """INSERT OR IGNORE INTO referral_commissions
        (referral_partner_id,referred_organization_id,stripe_invoice_id,stripe_charge_id,
         referred_company_snapshot,subscription_payment_cents,
         eligible_basis_cents,commission_rate_bps,commission_cents,
         eligible_on,status,earned_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,'pending',?)""",
        (
            attribution["referral_partner_id"],
            organization["id"],
            invoice_id,
            _invoice_charge_id(invoice),
            str(organization["name"] or attribution["referred_company_snapshot"] or "Referred carrier"),
            max(0, int(object_value(invoice, "amount_paid") or 0)),
            basis_cents,
            REFERRAL_COMMISSION_BPS,
            commission_cents,
            eligible_on,
            paid_at.replace(microsecond=0).isoformat(),
        ),
    )
    if cursor.rowcount != 1:
        return None
    commission_id = int(cursor.lastrowid)
    conn.execute(
        """INSERT INTO audit_events
        (organization_id,event_type,details_json) VALUES (?,?,?)""",
        (
            attribution["source_organization_id"],
            "referral.commission_earned",
            json.dumps(
                {
                    "commission_cents": commission_cents,
                    "commission_id": commission_id,
                    "eligible_basis_cents": basis_cents,
                    "stripe_invoice_id": invoice_id,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        ),
    )
    return commission_id


def reverse_referral_commission(conn: Any, stripe_object: Any, event_type: str) -> bool:
    if event_type == "invoice.voided":
        invoice_id = str(object_value(stripe_object, "id") or "")
    else:
        invoice_id = str(object_value(stripe_object, "invoice") or "")
    charge_id = ""
    if event_type == "charge.refunded":
        charge_id = str(object_value(stripe_object, "id") or "")
    elif event_type == "charge.dispute.created":
        charge_id = str(object_value(stripe_object, "charge") or "")
    commission = None
    if invoice_id.startswith("in_"):
        commission = conn.execute(
            """SELECT c.*,p.source_organization_id
            FROM referral_commissions c
            JOIN referral_partners p ON p.id=c.referral_partner_id
            WHERE c.stripe_invoice_id=?""",
            (invoice_id,),
        ).fetchone()
    if not commission and charge_id.startswith("ch_"):
        commission = conn.execute(
            """SELECT c.*,p.source_organization_id
            FROM referral_commissions c
            JOIN referral_partners p ON p.id=c.referral_partner_id
            WHERE c.stripe_charge_id=?""",
            (charge_id,),
        ).fetchone()
    if not commission:
        return False

    commission_cents = int(commission["commission_cents"] or 0)
    reversed_cents = commission_cents
    if event_type == "charge.refunded":
        charge_cents = max(0, int(object_value(stripe_object, "amount") or 0))
        refunded_cents = max(0, int(object_value(stripe_object, "amount_refunded") or 0))
        if charge_cents > 0:
            reversed_cents = min(
                commission_cents,
                round(commission_cents * refunded_cents / charge_cents),
            )
    previous_reversal = int(commission["reversed_cents"] or 0)
    reversed_cents = max(previous_reversal, reversed_cents)
    if reversed_cents <= previous_reversal:
        return False
    status = "reversed" if reversed_cents >= commission_cents else "adjusted"
    conn.execute(
        """UPDATE referral_commissions
        SET reversed_cents=?,status=?,reversed_at=?,reversal_event_type=?
        WHERE id=?""",
        (
            reversed_cents,
            status,
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            event_type,
            commission["id"],
        ),
    )
    conn.execute(
        """INSERT INTO audit_events
        (organization_id,event_type,details_json) VALUES (?,?,?)""",
        (
            commission["source_organization_id"],
            "referral.commission_adjusted",
            json.dumps(
                {
                    "commission_id": int(commission["id"]),
                    "event_type": event_type,
                    "reversed_cents": reversed_cents,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        ),
    )
    return True


def referral_portal_totals(conn: Any, partner_id: int) -> dict[str, int]:
    rows = conn.execute(
        """SELECT commission_cents,reversed_cents,paid_cents,offset_applied_cents
        FROM referral_commissions WHERE referral_partner_id=?""",
        (partner_id,),
    ).fetchall()
    earned_cents = 0
    unpaid_cents = 0
    paid_cents = 0
    cash_overpayment_cents = 0
    valid_offset_recovery_cents = 0
    for row in rows:
        net_cents = max(
            0,
            int(row["commission_cents"] or 0) - int(row["reversed_cents"] or 0),
        )
        row_paid_cents = max(0, int(row["paid_cents"] or 0))
        row_offset_cents = max(0, int(row["offset_applied_cents"] or 0))
        earned_cents += net_cents
        paid_cents += row_paid_cents
        unpaid_cents += max(0, net_cents - row_paid_cents - row_offset_cents)
        cash_overpayment_cents += max(0, row_paid_cents - net_cents)
        valid_offset_recovery_cents += min(
            row_offset_cents,
            max(0, net_cents - row_paid_cents),
        )
    return {
        "earned_cents": earned_cents,
        "unpaid_cents": unpaid_cents,
        "paid_cents": paid_cents,
        "offset_cents": max(
            0,
            cash_overpayment_cents - valid_offset_recovery_cents,
        ),
    }


def referral_program_example_amounts() -> list[tuple[int, int]]:
    return [
        (1_000, 500),
        (2_500, 1_250),
        (5_000, 2_500),
        (7_500, 3_750),
        (10_000, 5_000),
    ]


def referral_terms_summary() -> tuple[str, ...]:
    return (
        "You earn 50% of eligible CarrierOS subscription revenue actually collected from each attributed referral.",
        "Recurring commissions continue while the referred customer remains paid and active.",
        "Taxes, refunds, credits, discounts, chargebacks, and disputed amounts are not commissionable.",
        f"Commissions become eligible {REFERRAL_HOLD_DAYS} days after the successful payment.",
        "Self-referrals, misleading claims, spam, and undisclosed paid endorsements are prohibited.",
        "Required tax documentation must be completed before a payout when applicable.",
    )
