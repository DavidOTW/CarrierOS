from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import stripe_billing


class FakePrices:
    def __init__(self, price, price_id="price_owner"):
        self.price = price
        self.price_id = price_id

    def retrieve(self, price_id):
        assert price_id == self.price_id
        return self.price


class FakeCheckoutSessions:
    def __init__(self):
        self.params = None
        self.options = None

    def create(self, *, params, options):
        self.params = params
        self.options = options
        return {"id": "cs_test_carrieros", "url": "https://checkout.stripe.test/session"}


class FakeStripeClient:
    def __init__(self, price, price_id="price_owner"):
        self.sessions = FakeCheckoutSessions()
        self.v1 = SimpleNamespace(
            prices=FakePrices(price, price_id),
            checkout=SimpleNamespace(sessions=self.sessions),
        )


def test_stripe_client_uses_bounded_network_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("CARRIEROS_STRIPE_TIMEOUT_SECONDS", "90")
    captured: dict[str, object] = {}

    def fake_http_client(*, timeout, allow_sync_methods):
        captured["timeout"] = timeout
        captured["allow_sync_methods"] = allow_sync_methods
        return "http-client"

    def fake_stripe_client(api_key, *, http_client):
        captured["api_key"] = api_key
        captured["http_client"] = http_client
        return "stripe-client"

    monkeypatch.setattr(stripe_billing.stripe, "HTTPXClient", fake_http_client)
    monkeypatch.setattr(stripe_billing.stripe, "StripeClient", fake_stripe_client)

    assert stripe_billing._stripe_client() == "stripe-client"
    assert captured == {
        "timeout": 30.0,
        "allow_sync_methods": True,
        "api_key": "sk_test_example",
        "http_client": "http-client",
    }


def valid_monthly_price(**overrides):
    values = {
        "active": True,
        "currency": "usd",
        "unit_amount": 2500,
        "type": "recurring",
        "recurring": {
            "interval": "month",
            "interval_count": 1,
            "usage_type": "licensed",
        },
    }
    values.update(overrides)
    return values


def test_checkout_collects_payment_method_and_starts_card_on_file_trial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("STRIPE_PRICE_OWNER_OPERATOR", "price_owner")
    fake = FakeStripeClient(valid_monthly_price())
    monkeypatch.setattr(stripe_billing, "_stripe_client", lambda: fake)
    stripe_billing._validated_price_id.cache_clear()

    session = stripe_billing.create_checkout_session(
        organization_id=42,
        owner_email="owner@example.com",
        plan_code="owner_operator",
        expected_monthly_price=25,
        success_url="https://otwcarrieros.com/billing?checkout=success",
        cancel_url="https://otwcarrieros.com/billing?checkout=cancelled",
    )

    assert session["id"] == "cs_test_carrieros"
    assert fake.sessions.params["mode"] == "subscription"
    assert fake.sessions.params["line_items"] == [{"price": "price_owner", "quantity": 1}]
    assert fake.sessions.params["payment_method_collection"] == "always"
    assert fake.sessions.params["subscription_data"]["trial_period_days"] == 14
    assert fake.sessions.params["subscription_data"]["trial_settings"] == {
        "end_behavior": {"missing_payment_method": "cancel"}
    }
    assert fake.sessions.params["customer_email"] == "owner@example.com"


def test_startup_plan_validates_zero_unit_monthly_price(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("STRIPE_PRICE_CARRIER_STARTUP", "price_startup")
    fake = FakeStripeClient(valid_monthly_price(unit_amount=1000), "price_startup")
    monkeypatch.setattr(stripe_billing, "_stripe_client", lambda: fake)
    stripe_billing._validated_price_id.cache_clear()

    stripe_billing.create_checkout_session(
        organization_id=43,
        owner_email="startup@example.com",
        plan_code="carrier_startup",
        expected_monthly_price=10,
        success_url="https://otwcarrieros.com/billing?checkout=success",
        cancel_url="https://otwcarrieros.com/billing?checkout=cancelled",
    )

    assert fake.sessions.params["line_items"] == [{"price": "price_startup", "quantity": 1}]


@pytest.mark.parametrize(
    ("override", "failed_check"),
    [
        ({"active": False}, "active"),
        ({"currency": "eur"}, "currency"),
        ({"unit_amount": 1900}, "amount"),
        ({"type": "one_time", "recurring": None}, "type"),
        ({"recurring": {"interval": "year", "interval_count": 1, "usage_type": "licensed"}}, "interval"),
    ],
)
def test_checkout_refuses_mispriced_or_nonmonthly_stripe_price(
    monkeypatch: pytest.MonkeyPatch, override: dict, failed_check: str
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("STRIPE_PRICE_OWNER_OPERATOR", "price_owner")
    fake = FakeStripeClient(valid_monthly_price(**override))
    monkeypatch.setattr(stripe_billing, "_stripe_client", lambda: fake)
    stripe_billing._validated_price_id.cache_clear()

    with pytest.raises(stripe_billing.BillingConfigurationError, match=failed_check):
        stripe_billing.create_checkout_session(
            organization_id=42,
            owner_email="owner@example.com",
            plan_code="owner_operator",
            expected_monthly_price=25,
            success_url="https://otwcarrieros.com/billing?checkout=success",
            cancel_url="https://otwcarrieros.com/billing?checkout=cancelled",
        )
