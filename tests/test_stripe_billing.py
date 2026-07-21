from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import stripe_billing


class FakePrices:
    def __init__(self, price):
        self.price = price

    def retrieve(self, price_id):
        assert price_id == "price_owner"
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
    def __init__(self, price):
        self.sessions = FakeCheckoutSessions()
        self.v1 = SimpleNamespace(
            prices=FakePrices(price),
            checkout=SimpleNamespace(sessions=self.sessions),
        )


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
