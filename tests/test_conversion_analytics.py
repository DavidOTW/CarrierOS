from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.db import db_session, query_one
from app.main import app


@pytest.fixture(autouse=True)
def clear_signup_rate_limit_state():
    main_module.signup_attempts.clear()
    yield
    main_module.signup_attempts.clear()


def _create_account(client: TestClient, **extra: str):
    payload = {
        "full_name": "Fleet Owner",
        "company_name": "Attribution Carrier",
        "email": "attribution@example.com",
        "password": "StrongPassword!42",
        "plan": "starter_fleet",
        "accepted_terms": "on",
    }
    payload.update(extra)
    return client.post("/signup", data=payload, follow_redirects=False)


def test_safe_campaign_parameters_and_internal_traffic_are_configured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "analytics.db"))
    with TestClient(app) as client:
        response = client.get(
            "/?utm_source=founder_email&utm_medium=email&utm_campaign=carrier_intro"
        )
        assert response.status_code == 200
        assert "carrierSafeCampaignKeys" in response.text
        assert "carrierSafeLocation.href" in response.text
        assert "carrieros_internal_traffic" in response.text
        assert "traffic_type: carrierInternalTraffic ? 'internal' : 'external'" in response.text
        assert "page_location: window.location.origin + window.location.pathname" not in response.text
        assert "captureCarrierAttribution" in response.text
        assert "acquisition_campaign" in response.text


def test_signup_page_has_trust_copy_and_tracks_real_funnel_steps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "signup-funnel.db"))
    with TestClient(app) as client:
        response = client.get("/signup?plan=starter_fleet")
        assert response.status_code == 200
        assert "No charge today" in response.text
        assert "Purple Heart Marine Corps combat veteran" in response.text
        assert "Book a 15-minute walkthrough" in response.text
        assert "Start your 14-day trial" in response.text
        assert 'data-analytics-event="view_signup"' in response.text
        assert "beginSignup" in response.text
        assert "signup_submit" in response.text
        assert "plan_selected" in response.text


def test_signup_persists_first_touch_attribution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "attribution.db"))
    with TestClient(app) as client:
        response = _create_account(
            client,
            acquisition_source="founder_email",
            acquisition_medium="email",
            acquisition_campaign="purple_heart_founder_intro",
            acquisition_term="small carrier software",
            acquisition_content="personal_story_cta",
            acquisition_landing_page="/small-fleet-trucking-software",
            acquisition_referrer_host="mail.example.com",
            acquisition_click_id="gclid-example-123",
        )
        assert response.status_code == 303
        organization = query_one("SELECT * FROM organizations")
        assert organization["acquisition_source"] == "founder_email"
        assert organization["acquisition_medium"] == "email"
        assert organization["acquisition_campaign"] == "purple_heart_founder_intro"
        assert organization["acquisition_landing_page"] == "/small-fleet-trucking-software"
        assert organization["acquisition_click_id"] == "gclid-example-123"


def test_billing_conversions_require_verified_subscription_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "verified-conversions.db"))
    with TestClient(app) as client:
        created = _create_account(client)
        assert created.headers["location"] == "/billing?new=1"

        new_account = client.get("/billing?new=1&checkout=success")
        assert 'data-analytics-event="sign_up"' in new_account.text
        assert 'data-analytics-persistent="true"' in new_account.text
        assert 'data-analytics-event="trial_started"' not in new_account.text
        assert "data-checkout-confirmation" in new_account.text

        organization = query_one("SELECT * FROM organizations")
        with db_session() as conn:
            conn.execute(
                """UPDATE organizations
                SET subscription_status='trialing', trial_ends_at='2026-08-07'
                WHERE id=?""",
                (organization["id"],),
            )
        trial = client.get("/billing")
        assert 'data-analytics-event="trial_started"' in trial.text
        assert 'data-analytics-trial-end="2026-08-07"' in trial.text

        with db_session() as conn:
            conn.execute(
                """UPDATE organizations
                SET subscription_status='active',
                    subscription_current_period_end='2026-09-07'
                WHERE id=?""",
                (organization["id"],),
            )
        paid = client.get("/billing")
        assert 'data-analytics-event="subscription_started"' in paid.text
        assert 'data-analytics-period-end="2026-09-07"' in paid.text

        status = client.get("/billing/status")
        assert status.status_code == 200
        assert status.json()["subscription_status"] == "active"
        assert status.json()["plan"] == "starter_fleet"
