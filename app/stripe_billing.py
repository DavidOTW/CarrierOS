from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Mapping

import stripe


PLAN_PRICE_ENV = {
    "carrier_startup": "STRIPE_PRICE_CARRIER_STARTUP",
    "owner_operator": "STRIPE_PRICE_OWNER_OPERATOR",
    "starter_fleet": "STRIPE_PRICE_STARTER_FLEET",
    "small_fleet": "STRIPE_PRICE_SMALL_FLEET",
    "growing_fleet": "STRIPE_PRICE_GROWING_FLEET",
}


class BillingConfigurationError(RuntimeError):
    """Raised when the server-side Stripe configuration is incomplete."""


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise BillingConfigurationError(f"{name} is not configured.")
    return value


def _stripe_client() -> stripe.StripeClient:
    # Stripe's SDK defaults to an 80-second network timeout. That is too long
    # for a single-worker web request: a transient Stripe/network issue would
    # make the plan selection page look frozen. Fail promptly so the route can
    # return a useful retry message while the app remains responsive.
    try:
        timeout_seconds = float(os.getenv("CARRIEROS_STRIPE_TIMEOUT_SECONDS", "20"))
    except ValueError:
        timeout_seconds = 20.0
    timeout_seconds = min(30.0, max(5.0, timeout_seconds))
    return stripe.StripeClient(
        _required_env("STRIPE_SECRET_KEY"),
        # Checkout and price validation are intentionally synchronous calls.
        # Stripe's HTTPX client defaults to async-only in recent SDK versions;
        # explicitly enable sync methods so a checkout request cannot become a
        # raw 500 before Stripe receives it.
        http_client=stripe.HTTPXClient(
            timeout=timeout_seconds,
            allow_sync_methods=True,
        ),
    )


@lru_cache(maxsize=16)
def _validated_price_id(plan_code: str, price_id: str, expected_unit_amount: int) -> str:
    """Fail closed if a configured Stripe Price does not match CarrierOS pricing."""
    price = _stripe_client().v1.prices.retrieve(price_id)
    recurring = _value(price, "recurring") or {}
    checks = {
        "active": bool(_value(price, "active")),
        "currency": str(_value(price, "currency") or "").lower() == "usd",
        "amount": int(_value(price, "unit_amount") or -1) == expected_unit_amount,
        "type": str(_value(price, "type") or "") == "recurring",
        "interval": str(_value(recurring, "interval") or "") == "month",
        "interval_count": int(_value(recurring, "interval_count") or 0) == 1,
        "usage_type": str(_value(recurring, "usage_type") or "") == "licensed",
    }
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise BillingConfigurationError(
            f"Stripe Price for {plan_code} does not match CarrierOS billing ({failed})."
        )
    return price_id


def stripe_configured() -> bool:
    return bool(
        os.getenv("STRIPE_SECRET_KEY", "").strip()
        and os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
        and all(os.getenv(name, "").strip() for name in PLAN_PRICE_ENV.values())
    )


def stripe_live_configured() -> bool:
    """Return true only when production billing points at a live Stripe account."""
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    return bool(stripe_configured() and secret_key.startswith("sk_live_"))


def price_id_for_plan(plan_code: str) -> str:
    env_name = PLAN_PRICE_ENV.get(plan_code)
    if not env_name:
        raise BillingConfigurationError("Unknown CarrierOS plan.")
    return _required_env(env_name)


def plan_code_for_price(price_id: str | None) -> str | None:
    if not price_id:
        return None
    for plan_code, env_name in PLAN_PRICE_ENV.items():
        if os.getenv(env_name, "").strip() == price_id:
            return plan_code
    return None


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def object_value(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from Stripe objects or dictionaries."""
    return _value(obj, key, default)


def unix_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None


def create_checkout_session(
    *,
    organization_id: int,
    owner_email: str,
    plan_code: str,
    expected_monthly_price: int,
    success_url: str,
    cancel_url: str,
    existing_customer_id: str | None = None,
) -> Any:
    price_id = price_id_for_plan(plan_code)
    price_id = _validated_price_id(plan_code, price_id, expected_monthly_price * 100)
    metadata = {
        "carrieros_org_id": str(organization_id),
        "carrieros_plan_code": plan_code,
    }
    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "client_reference_id": str(organization_id),
        "metadata": metadata,
        "subscription_data": {
            "trial_period_days": 14,
            "metadata": metadata,
        },
        "success_url": success_url,
        "cancel_url": cancel_url,
        "allow_promotion_codes": True,
        "billing_address_collection": "auto",
        "payment_method_collection": "always",
    }
    params["subscription_data"]["trial_settings"] = {
        "end_behavior": {"missing_payment_method": "cancel"}
    }
    if existing_customer_id:
        params["customer"] = existing_customer_id
    else:
        params["customer_email"] = owner_email
    if os.getenv("STRIPE_TAX_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}:
        params["automatic_tax"] = {"enabled": True}
        params["tax_id_collection"] = {"enabled": True}

    return _stripe_client().v1.checkout.sessions.create(
        params=params,
        options={
            "idempotency_key": (
                f"carrieros-checkout-{organization_id}-{plan_code}-"
                f"{secrets.token_urlsafe(12)}"
            )
        },
    )


def create_portal_session(*, customer_id: str, return_url: str) -> Any:
    params: dict[str, Any] = {"customer": customer_id, "return_url": return_url}
    configuration_id = os.getenv("STRIPE_PORTAL_CONFIGURATION_ID", "").strip()
    if configuration_id:
        params["configuration"] = configuration_id
    return _stripe_client().v1.billing_portal.sessions.create(params=params)


def construct_webhook_event(payload: bytes, signature: str | None) -> Any:
    if not signature:
        raise ValueError("Missing Stripe-Signature header.")
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=_required_env("STRIPE_WEBHOOK_SECRET"),
    )


def first_subscription_price_id(subscription: Any) -> str | None:
    items = _value(subscription, "items") or {}
    data = _value(items, "data") or []
    if not data:
        return None
    price = _value(data[0], "price") or {}
    return _value(price, "id")
