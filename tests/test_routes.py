from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient

from app.db import db_session, query_one
from app import main as main_module
from app.main import app


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()
    yield
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()


def signup(client: TestClient, email: str, company: str = "Acme Carrier", activate: bool = True):
    response = client.post(
        "/signup",
        data={
            "full_name": "Fleet Owner",
            "company_name": company,
            "email": email,
            "password": "StrongPassword!42",
            "plan": "owner_operator",
            "accepted_terms": "on",
        },
        follow_redirects=False,
    )
    if activate and response.status_code == 303:
        row = query_one("SELECT organization_id FROM users WHERE email=?", (email,))
        with db_session() as conn:
            conn.execute(
                "UPDATE organizations SET subscription_status='active' WHERE id=?",
                (row["organization_id"],),
            )
    return response


def configure_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_example")
    monkeypatch.setenv("STRIPE_PRICE_CARRIER_STARTUP", "price_startup")
    monkeypatch.setenv("STRIPE_PRICE_OWNER_OPERATOR", "price_owner")
    monkeypatch.setenv("STRIPE_PRICE_STARTER_FLEET", "price_starter")
    monkeypatch.setenv("STRIPE_PRICE_SMALL_FLEET", "price_small")
    monkeypatch.setenv("STRIPE_PRICE_GROWING_FLEET", "price_growing")


def test_launch_pricing_uses_active_power_units() -> None:
    assert [
        (code, plan["units"], plan["price"])
        for code, plan in main_module.PLAN_LIMITS.items()
    ] == [
        ("carrier_startup", 0, 10),
        ("owner_operator", 2, 25),
        ("starter_fleet", 5, 50),
        ("small_fleet", 10, 75),
        ("growing_fleet", 20, 100),
    ]


def test_public_marketing_home_uses_launch_pricing_and_real_app_links(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "marketing.db"))
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Run the fleet" in response.text
        assert "live demo" in response.text.lower()
        assert "Pre-authority" in response.text
        assert "$10" in response.text
        assert "Carrier startup checklist" in response.text
        assert "Up to 2 active power units" in response.text
        assert "$25" in response.text
        assert "Up to 20 active power units" in response.text
        assert "$100" in response.text
        assert "14-day free trial" in response.text
        assert "no payment method" not in response.text.lower()
        assert "Start free beta" not in response.text
        assert '/signup?plan=starter_fleet' in response.text
        assert '<link rel="canonical" href="https://otwcarrieros.com/">' in response.text
        assert 'type="application/ld+json"' in response.text
        assert 'Small Fleet Trucking Software' in response.text
        assert '/driver-settlement-software' in response.text
        assert "Marine Corps combat veteran" in response.text
        assert "Purple Heart recipient" in response.text
        assert "20 years of experience" in response.text
        assert 'href="https://www.linkedin.com/in/davidbryant89"' in response.text
        assert '<a class="public-signin" href="/login">Log in</a>' in response.text
        assert '"@type": "Person"' in response.text
        assert response.headers["cache-control"].startswith("public")
        stylesheet = client.get("/static/app.css")
        assert ".public-signin{display:inline-flex" in stylesheet.text
        assert ".public-signin{display:none}" not in stylesheet.text


def test_search_pages_sitemap_and_crawl_controls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "seo.db"))
    with TestClient(app) as client:
        expected = {
            "/small-fleet-trucking-software": "Small Fleet Trucking Software",
            "/driver-settlement-software": "Driver Pay Tracking",
            "/load-profitability-calculator": "Truck Load Profitability Calculator",
        }
        for path, phrase in expected.items():
            response = client.get(path)
            assert response.status_code == 200
            assert phrase in response.text
            assert f'<link rel="canonical" href="https://otwcarrieros.com{path}">' in response.text
            assert 'content="index, follow' in response.text
            assert '"@type": "FAQPage"' in response.text

        sitemap = client.get("/sitemap.xml")
        assert sitemap.status_code == 200
        assert sitemap.headers["content-type"].startswith("application/xml")
        for path in ("/", "/demo", *expected):
            assert f"https://otwcarrieros.com{path}" in sitemap.text
        assert "/login" not in sitemap.text

        robots = client.get("/robots.txt")
        assert robots.status_code == 200
        assert "Sitemap: https://otwcarrieros.com/sitemap.xml" in robots.text
        assert "Disallow: /dashboard" in robots.text

        login = client.get("/login")
        assert 'content="noindex, nofollow"' in login.text
        assert login.headers["x-robots-tag"] == "noindex, nofollow"


def test_public_demo_is_sample_only_and_includes_all_pay_models(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "demo.db"))
    with TestClient(app) as client:
        response = client.get("/demo")
        assert response.status_code == 200
        assert "fictional sample data" in response.text.lower()
        assert "changes are not saved" in response.text.lower()
        for model in (
            "Profit split",
            "Contractor gross split",
            "Owner-operator split",
            "Flat per load",
            "Loaded-mile rate",
            "Total-mile rate",
            "Day rate",
        ):
            assert model in response.text
        assert "Hourly" not in response.text
        assert "Salary" not in response.text
        assert "SAMPLE DRIVER-PAY ESTIMATE" in response.text
        assert not re.search(r"<form[^>]+method=[\"']post", response.text, re.IGNORECASE)


def test_signup_requires_verified_billing_before_access(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "pending.db"))
    with TestClient(app) as client:
        response = signup(client, "pending@example.com", activate=False)
        assert response.headers["location"] == "/billing?new=1"
        organization = query_one("SELECT * FROM organizations")
        assert organization["subscription_status"] == "incomplete"
        assert organization["trial_ends_at"] is None
        dashboard = client.get("/dashboard", follow_redirects=False)
        assert dashboard.headers["location"] == "/billing"


def test_founding_beta_signup_grants_trial_and_records_consent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "beta.db"))
    monkeypatch.setattr(main_module, "BILLING_MODE", "beta")
    with TestClient(app) as client:
        response = signup(client, "founder@example.com", activate=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"
        organization = query_one("SELECT * FROM organizations")
        assert organization["subscription_status"] == "trialing"
        assert organization["trial_ends_at"] == (date.today() + timedelta(days=14)).isoformat()
        assert organization["terms_version"] == main_module.TERMS_VERSION
        assert organization["terms_accepted_at"]
        user = query_one("SELECT * FROM users WHERE organization_id=?", (organization["id"],))
        assert user["role"] == "owner"
        assert client.get("/dashboard").status_code == 200
        event = query_one("SELECT * FROM audit_events WHERE event_type='organization.created'")
        assert event["organization_id"] == organization["id"]


def test_signup_requires_terms_and_limits_account_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "terms.db"))
    payload = {
        "full_name": "Fleet Owner",
        "company_name": "Consent Carrier",
        "email": "consent@example.com",
        "password": "StrongPassword!42",
        "plan": "owner_operator",
    }
    with TestClient(app) as client:
        rejected = client.post("/signup", data=payload)
        assert rejected.status_code == 400
        assert "Accept the Terms" in rejected.text
        assert query_one("SELECT COUNT(*) AS total FROM organizations")["total"] == 0

    monkeypatch.setattr(main_module, "SIGNUP_MAX_ATTEMPTS", 1)
    with TestClient(app) as first_client:
        assert signup(first_client, "first@example.com", activate=False).status_code == 303
    with TestClient(app) as second_client:
        limited = signup(second_client, "second@example.com", activate=False)
        assert limited.status_code == 429


def test_signup_empty_workspace_and_authenticated_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "routes.db"))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        readiness = client.get("/health/ready")
        assert readiness.status_code == 503
        assert readiness.json()["ready"] is False
        assert "sk_test" not in readiness.text
        assert signup(client, "owner@example.com").status_code == 303
        for page in (
            "/dashboard", "/loads", "/loads/new", "/vehicles", "/drivers", "/fuel",
            "/payments", "/quotes", "/rate-quotes", "/rate-quotes/new", "/financials", "/idle", "/settings",
            "/compliance", "/onboarding", "/documents", "/receivables", "/links", "/billing",
            "/audits", "/growth", "/startup",
            "/manifest.webmanifest", "/service-worker.js",
        ):
            response = client.get(page)
            assert response.status_code == 200, f"{page}: {response.text[:500]}"
        assert query_one("SELECT COUNT(*) AS total FROM loads")["total"] == 0

    with TestClient(app) as public_client:
        assert public_client.get("/privacy").status_code == 200
        assert public_client.get("/terms").status_code == 200


def test_business_links_are_safe_and_tenant_isolated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "links.db"))
    with TestClient(app) as client_a, TestClient(app) as client_b:
        signup(client_a, "links-alpha@example.com", "Alpha Fleet")
        created = client_a.post(
            "/links",
            data={
                "label": "Preferred Load Board",
                "url": "loads.example.com/search",
                "category": "Load board",
            },
            follow_redirects=False,
        )
        assert created.status_code == 303
        assert created.headers["location"] == "/links"
        link = query_one("SELECT * FROM quick_links")
        assert link["url"] == "https://loads.example.com/search"

        links_page = client_a.get("/links")
        assert "Preferred Load Board" in links_page.text
        assert 'target="_blank"' in links_page.text
        assert 'rel="noopener noreferrer"' in links_page.text
        dashboard = client_a.get("/dashboard")
        assert "Preferred Load Board" in dashboard.text

        invalid = client_a.post(
            "/links",
            data={"label": "Unsafe", "url": "javascript:alert(1)", "category": "Other"},
        )
        assert invalid.status_code == 400
        assert "valid http or https" in invalid.text
        duplicate = client_a.post(
            "/links",
            data={
                "label": "preferred load board",
                "url": "https://another.example.com",
                "category": "Other",
            },
        )
        assert duplicate.status_code == 400

        signup(client_b, "links-beta@example.com", "Beta Fleet")
        assert "loads.example.com" not in client_b.get("/links").text
        forbidden_delete = client_b.post(
            f"/links/{link['id']}/delete", follow_redirects=False
        )
        assert forbidden_delete.status_code == 404
        assert query_one("SELECT COUNT(*) AS total FROM quick_links")["total"] == 1

        deleted = client_a.post(
            f"/links/{link['id']}/delete", follow_redirects=False
        )
        assert deleted.status_code == 303
        assert query_one("SELECT COUNT(*) AS total FROM quick_links")["total"] == 0
        assert query_one(
            "SELECT COUNT(*) AS total FROM audit_events WHERE event_type='quick_link.created'"
        )["total"] == 1


def test_dashboard_driver_availability_and_click_to_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert main_module.callable_phone("+1 (615) 555-0198") == "+16155550198"
    assert main_module.callable_phone("not a phone") is None
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "availability.db"))
    delivery = date.today() + timedelta(days=3)
    with TestClient(app) as client:
        signup(client, "dispatch@example.com", "Dispatch Fleet")
        assert client.post(
            "/vehicles",
            data={"name": "Truck 44", "equipment_type": "Truck", "active": "on"},
            follow_redirects=False,
        ).status_code == 303
        vehicle = query_one("SELECT id FROM vehicles WHERE name='Truck 44'")
        assert client.post(
            "/drivers",
            data={
                "name": "Casey Driver",
                "phone": "(615) 555-0198",
                "role": "Driver",
                "pay_model": "Flat Rate per Load",
                "vehicle_id": str(vehicle["id"]),
                "flat_rate_per_load": "350",
                "mpg": "9.5",
                "maintenance_per_mile": "0.22",
                "active": "on",
            },
            follow_redirects=False,
        ).status_code == 303
        driver = query_one("SELECT id FROM drivers WHERE name='Casey Driver'")
        assert client.post(
            "/loads/new",
            data={
                "load_number": "NEXT-101",
                "status": "Booked",
                "include_in_model": "on",
                "pickup_date": date.today().isoformat(),
                "delivery_date": delivery.isoformat(),
                "driver_id": str(driver["id"]),
                "vehicle_id": str(vehicle["id"]),
                "broker": "Example Broker",
                "revenue": "2500",
                "origin": "Nashville, TN",
                "destination": "Charlotte, NC",
                "loaded_miles": "410",
                "deadhead_miles": "35",
            },
            follow_redirects=False,
        ).status_code == 303

        dashboard = client.get("/dashboard")
        display_date = delivery.strftime("%b %d, %Y").replace(" 0", " ")
        assert "Driver &amp; unit availability" in dashboard.text
        assert "Casey Driver" in dashboard.text
        assert "Truck 44" in dashboard.text
        assert "Charlotte, NC" in dashboard.text
        assert f"Available {display_date}" in dashboard.text
        assert 'href="tel:6155550198"' in dashboard.text
        assert "not live GPS or ELD data" in dashboard.text


def test_unit_limit_and_flat_rate_driver(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "limits.db"))
    with TestClient(app) as client:
        signup(client, "limits@example.com")
        for unit in ("Truck 1", "Truck 2", "Truck 3"):
            assert client.post("/vehicles", data={"name": unit, "equipment_type": "Truck", "active": "on"}).status_code == 200
        assert query_one("SELECT COUNT(*) AS total FROM vehicles WHERE active=1")["total"] == 2
        vehicle_id = query_one("SELECT id FROM vehicles ORDER BY id LIMIT 1")["id"]
        created = client.post(
            "/drivers",
            data={
                "name": "Flat Rate Driver",
                "role": "Driver",
                "pay_model": "Flat Rate per Load",
                "vehicle_id": str(vehicle_id),
                "flat_rate_per_load": "325",
                "mpg": "9.5",
                "maintenance_per_mile": "0.22",
                "active": "on",
            },
            follow_redirects=False,
        )
        assert created.status_code == 303
        row = query_one("SELECT pay_model,flat_rate_per_load FROM drivers")
        assert row["pay_model"] == "Flat Rate per Load"
        assert row["flat_rate_per_load"] == pytest.approx(325)


def test_tenant_isolation_and_expired_trial_redirect(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "tenants.db"))
    with TestClient(app) as client_a:
        signup(client_a, "alpha@example.com", "Alpha Fleet")
        create = client_a.post(
            "/documents/generate",
            data={
                "document_type": "driver_handbook",
                "company": "Alpha Fleet",
                "effective_date": "2026-07-21",
                "state": "Tennessee",
                "contact": "alpha@example.com",
                "notes": "Alpha only",
            },
            follow_redirects=False,
        )
        assert create.status_code == 303
        doc_url = create.headers["location"]

    with TestClient(app) as client_b:
        signup(client_b, "beta@example.com", "Beta Fleet")
        assert client_b.get(doc_url).status_code == 404
        beta = query_one("SELECT organization_id FROM users WHERE email='beta@example.com'")
        with db_session() as conn:
            conn.execute(
                "UPDATE organizations SET subscription_status='past_due',trial_ends_at='2020-01-01' WHERE id=?",
                (beta["organization_id"],),
            )
        expired = client_b.get("/dashboard", follow_redirects=False)
        assert expired.status_code == 303
        assert expired.headers["location"] == "/billing"


def test_security_headers_and_no_default_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "security.db"))
    with TestClient(app) as client:
        page = client.get("/login")
        assert page.status_code == 200
        assert page.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
        assert page.headers["cache-control"] == "no-store"
        assert page.headers["cross-origin-opener-policy"] == "same-origin"
        assert "ChangeMe" not in page.text
        assert "admin@" not in page.text


def test_production_forms_require_valid_csrf_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "csrf.db"))
    monkeypatch.setattr(main_module, "IS_PRODUCTION", True)
    monkeypatch.setattr(main_module, "stripe_live_configured", lambda: True)
    with TestClient(app, base_url="https://testserver") as client:
        page = client.get("/signup")
        token_match = re.search(r'const carrierCsrfToken = "([^"]+)"', page.text)
        assert token_match
        payload = {
            "full_name": "Secure Owner",
            "company_name": "Secure Carrier",
            "email": "secure@example.com",
            "password": "StrongPassword!42",
            "plan": "owner_operator",
            "accepted_terms": "on",
        }
        assert client.post("/signup", data=payload).status_code == 403
        payload["_csrf"] = token_match.group(1)
        accepted = client.post("/signup", data=payload, follow_redirects=False)
        assert accepted.status_code == 303


def test_checkout_uses_server_side_plan_whitelist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "checkout.db"))
    monkeypatch.setenv("CARRIEROS_PUBLIC_URL", "https://app.carrieros.example")
    configure_stripe(monkeypatch)
    captured = {}

    def fake_checkout(**kwargs):
        captured.update(kwargs)
        return {"url": "https://checkout.stripe.test/session"}

    monkeypatch.setattr(main_module, "create_checkout_session", fake_checkout)
    with TestClient(app) as client:
        signup(client, "checkout@example.com", activate=False)
        response = client.post(
            "/billing/checkout",
            data={"plan": "starter_fleet"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "https://checkout.stripe.test/session"
        assert captured["plan_code"] == "starter_fleet"
        assert captured["expected_monthly_price"] == 50
        assert captured["owner_email"] == "checkout@example.com"
        assert captured["success_url"].startswith("https://app.carrieros.example/billing")
        invalid = client.post(
            "/billing/checkout",
            data={"plan": "attacker_controlled_price"},
            follow_redirects=False,
        )
        assert invalid.status_code == 400


def test_webhooks_activate_update_and_deduplicate_subscription(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "webhooks.db"))
    configure_stripe(monkeypatch)
    events = []
    monkeypatch.setattr(main_module, "construct_webhook_event", lambda payload, signature: events.pop(0))

    with TestClient(app) as client:
        signup(client, "webhook@example.com", activate=False)
        organization = query_one("SELECT * FROM organizations")
        checkout_event = {
            "id": "evt_checkout_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "mode": "subscription",
                    "customer": "cus_test_1",
                    "subscription": "sub_test_1",
                    "client_reference_id": str(organization["id"]),
                    "metadata": {
                        "carrieros_org_id": str(organization["id"]),
                        "carrieros_plan_code": "owner_operator",
                    },
                }
            },
        }
        events.append(checkout_event)
        activated = client.post("/stripe/webhook", content=b"{}", headers={"stripe-signature": "test"})
        assert activated.status_code == 200
        row = query_one("SELECT * FROM organizations")
        assert row["subscription_status"] == "trialing"
        assert row["billing_customer_reference"] == "cus_test_1"
        assert row["billing_subscription_reference"] == "sub_test_1"

        events.append(checkout_event)
        duplicate = client.post("/stripe/webhook", content=b"{}", headers={"stripe-signature": "test"})
        assert duplicate.json()["duplicate"] is True
        assert query_one("SELECT COUNT(*) AS total FROM processed_stripe_events")["total"] == 1

        events.append({
            "id": "evt_subscription_1",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_1",
                    "customer": "cus_test_1",
                    "status": "active",
                    "trial_end": None,
                    "current_period_end": 1800000000,
                    "cancel_at_period_end": False,
                    "metadata": {
                        "carrieros_org_id": str(organization["id"]),
                        "carrieros_plan_code": "owner_operator",
                    },
                    "items": {"data": [{"price": {"id": "price_small"}}]},
                }
            },
        })
        updated = client.post("/stripe/webhook", content=b"{}", headers={"stripe-signature": "test"})
        assert updated.status_code == 200
        row = query_one("SELECT * FROM organizations")
        assert row["subscription_status"] == "active"
        assert row["plan_code"] == "small_fleet"
        assert row["active_unit_limit"] == 10
        assert row["billing_price_reference"] == "price_small"

        events.append({
            "id": "evt_unrelated_invoice",
            "type": "invoice.payment_failed",
            "data": {"object": {"id": "in_unrelated", "customer": "cus_test_1"}},
        })
        ignored = client.post("/stripe/webhook", content=b"{}", headers={"stripe-signature": "test"})
        assert ignored.status_code == 200
        assert query_one("SELECT subscription_status FROM organizations")["subscription_status"] == "active"


def test_verified_ratecon_creates_reviewable_driver_trip_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "dispatch.db"))
    with TestClient(app) as client:
        signup(client, "dispatch@example.com")
        assert client.post(
            "/vehicles",
            data={"name": "Truck 27", "equipment_type": "Tractor", "active": "on"},
        ).status_code == 200
        vehicle = query_one("SELECT id FROM vehicles WHERE name='Truck 27'")
        assert client.post(
            "/drivers",
            data={
                "name": "Jordan Driver",
                "phone": "(615) 555-0147",
                "role": "Driver",
                "pay_model": "Flat Rate per Load",
                "vehicle_id": str(vehicle["id"]),
                "flat_rate_per_load": "350",
                "mpg": "9.5",
                "maintenance_per_mile": "0.22",
                "active": "on",
            },
            follow_redirects=False,
        ).status_code == 303
        driver = query_one("SELECT id FROM drivers WHERE name='Jordan Driver'")
        created = client.post(
            "/loads/new",
            data={
                "load_number": "DISPATCH-1048",
                "status": "Booked — Awaiting RateCon",
                "include_in_model": "on",
                "pickup_date": "2026-07-22",
                "delivery_date": "2026-07-23",
                "driver_id": str(driver["id"]),
                "vehicle_id": str(vehicle["id"]),
                "broker": "Acme Brokerage",
                "revenue": "3250",
                "origin": "Nashville, TN",
                "destination": "Charlotte, NC",
                "loaded_miles": "410",
                "deadhead_miles": "35",
                "notes": "INTERNAL ONLY: margin discussion",
                "ratecon_received": "on",
                "ratecon_reference": "RC-1048.pdf",
                "pickup_address": "1200 Freight Way, Nashville, TN 37210",
                "pickup_window_start": "2026-07-22T08:00",
                "pickup_window_end": "2026-07-22T10:00",
                "pickup_timezone": "America/Chicago",
                "pickup_contact_name": "Pat Shipping",
                "pickup_contact_phone": "615-555-0101",
                "pickup_instructions": "Check in at gate 2; reference PO 88.",
                "delivery_address": "850 Distribution Blvd, Charlotte, NC 28208",
                "delivery_window_start": "2026-07-23T13:00",
                "delivery_window_end": "2026-07-23T15:30",
                "delivery_timezone": "America/New_York",
                "delivery_contact_name": "Lee Receiving",
                "delivery_contact_phone": "704-555-0188",
                "delivery_instructions": "Use south receiving entrance.",
            },
            follow_redirects=False,
        )
        assert created.status_code == 303
        load = query_one("SELECT * FROM loads WHERE load_number='DISPATCH-1048'")
        assert load["status"] == "RateCon Received"
        assert load["ratecon_received_at"]
        assert load["pickup_address"].startswith("1200 Freight Way")

        detail = client.get(created.headers["location"])
        assert detail.status_code == 200
        assert "Ready for Jordan Driver" in detail.text
        assert "Text trip &middot; iPhone" in detail.text
        assert "Text trip &middot; Android" in detail.text
        assert 'href="sms:6155550147&amp;body=' in detail.text
        assert 'href="sms:6155550147?body=' in detail.text
        assert "https://maps.apple.com/" in detail.text
        assert "https://www.google.com/maps/dir/" in detail.text
        assert "Pat Shipping" in detail.text
        assert "Check in at gate 2; reference PO 88." in detail.text
        assert "Lee Receiving" in detail.text
        assert "Please confirm receipt" in detail.text
        assert "INTERNAL ONLY: margin discussion" not in detail.text


def test_driver_trip_text_lists_missing_requirements_and_rejects_reversed_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "dispatch-blockers.db"))
    with TestClient(app) as client:
        signup(client, "dispatch-blockers@example.com")
        client.post("/vehicles", data={"name": "Truck 9", "equipment_type": "Tractor", "active": "on"})
        vehicle = query_one("SELECT id FROM vehicles WHERE name='Truck 9'")
        client.post(
            "/drivers",
            data={
                "name": "No Phone Driver", "role": "Driver", "pay_model": "Flat Rate per Load",
                "vehicle_id": str(vehicle["id"]), "flat_rate_per_load": "300", "active": "on",
            },
        )
        driver = query_one("SELECT id FROM drivers WHERE name='No Phone Driver'")
        base = {
            "load_number": "BLOCKED-1", "status": "Booked", "include_in_model": "on",
            "pickup_date": "2026-07-22", "delivery_date": "2026-07-23",
            "driver_id": str(driver["id"]), "vehicle_id": str(vehicle["id"]),
            "revenue": "1200", "loaded_miles": "200", "deadhead_miles": "10",
        }
        created = client.post("/loads/new", data=base, follow_redirects=False)
        detail = client.get(created.headers["location"])
        assert "Mark the RateCon as received and verified" in detail.text
        assert "Add a valid mobile number" in detail.text
        assert "Add the full pickup address" in detail.text
        assert "Add the complete delivery appointment window" in detail.text

        invalid = client.post(
            "/loads/new",
            data={
                **base,
                "load_number": "BAD-WINDOW",
                "pickup_window_start": "2026-07-22T11:00",
                "pickup_window_end": "2026-07-22T08:00",
            },
        )
        assert invalid.status_code == 400
        assert "Pickup window end must be after its start" in invalid.text
