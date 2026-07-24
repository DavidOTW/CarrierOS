from __future__ import annotations

from datetime import date
import re
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.db import db_session, export_organization_data, query_one
from app.main import app
from app.referrals import referral_invoice_basis_cents


ADMIN_EMAIL = "david@outsidethewirelogistics.com"
PASSWORD = "StrongPassword!42"


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()
    yield
    main_module.login_attempts.clear()
    main_module.signup_attempts.clear()
    main_module.reset_attempts.clear()


def signup(client: TestClient, email: str, company: str) -> int:
    response = client.post(
        "/signup",
        data={
            "full_name": "Fleet Owner",
            "company_name": company,
            "email": email,
            "password": PASSWORD,
            "plan": "owner_operator",
            "accepted_terms": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    row = query_one(
        """SELECT o.id FROM organizations o
        JOIN users u ON u.organization_id=o.id WHERE u.email=?""",
        (email,),
    )
    assert row
    with db_session() as conn:
        conn.execute(
            "UPDATE organizations SET subscription_status='active' WHERE id=?",
            (row["id"],),
        )
    return int(row["id"])


def post_stripe_event(client: TestClient, events: list[dict], event: dict):
    events.append(event)
    return client.post(
        "/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "test"},
    )


def test_referral_program_attributes_recurring_payments_and_adjusts_reversals(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "referrals.db"))
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_example")
    monkeypatch.setattr(main_module, "REFERRAL_ADMIN_EMAIL", ADMIN_EMAIL)
    events: list[dict] = []
    monkeypatch.setattr(
        main_module,
        "construct_webhook_event",
        lambda payload, signature: events.pop(0),
    )

    with TestClient(app) as admin_client, TestClient(app) as referred_client:
        source_org_id = signup(admin_client, ADMIN_EMAIL, "Outside The Wire Logistics")
        with db_session() as conn:
            driver_id = conn.execute(
                """INSERT INTO drivers (organization_id,name,email,role,pay_model)
                VALUES (?,?,?,?,?)""",
                (
                    source_org_id,
                    "Jordan Driver",
                    "driver@example.com",
                    "Driver",
                    "Profit Split",
                ),
            ).lastrowid

        referral_page = admin_client.get("/referrals")
        assert referral_page.status_code == 200
        assert "Drivers earn 50% while their referrals keep paying." in referral_page.text

        invite = admin_client.post(
            "/referrals/partners",
            data={"driver_id": str(driver_id), "email": "driver@example.com"},
        )
        assert invite.status_code == 200
        private_url_match = re.search(
            r'value="([^"]+/referral-program/portal/[^"]+)"',
            invite.text,
        )
        assert private_url_match
        private_url = private_url_match.group(1)
        portal_path = urlparse(private_url).path
        portal_token = portal_path.rsplit("/", 1)[-1]
        partner = query_one("SELECT * FROM referral_partners")
        assert partner
        assert partner["active"] == 0
        assert partner["portal_token_hash"] != portal_token
        assert len(partner["portal_token_hash"]) == 64

        activation = admin_client.post(
            portal_path,
            data={
                "email": "driver@example.com",
                "accepted_terms": "on",
            },
            follow_redirects=False,
        )
        assert activation.status_code == 303
        partner = query_one("SELECT * FROM referral_partners")
        assert partner["active"] == 1
        assert partner["terms_version"] == main_module.REFERRAL_TERMS_VERSION

        portal = admin_client.get(portal_path)
        assert portal.status_code == 200
        assert portal.headers["referrer-policy"] == "no-referrer"
        assert 'content="noindex, nofollow"' in portal.text
        assert f"/r/{partner['referral_code']}" in portal.text

        referral_redirect = referred_client.get(
            f"/r/{partner['referral_code']}",
            follow_redirects=False,
        )
        assert referral_redirect.status_code == 303
        assert referral_redirect.headers["location"].startswith("/signup?ref=")
        referred_org_id = signup(
            referred_client,
            "referred@example.com",
            "Referred Carrier",
        )
        attribution = query_one(
            "SELECT * FROM referral_attributions WHERE referred_organization_id=?",
            (referred_org_id,),
        )
        assert attribution
        assert attribution["referral_partner_id"] == partner["id"]
        with db_session() as conn:
            conn.execute(
                """UPDATE organizations
                SET billing_customer_reference='cus_referred',
                    billing_subscription_reference='sub_referred',
                    subscription_status='active'
                WHERE id=?""",
                (referred_org_id,),
            )

        invoice_event = {
            "id": "evt_invoice_referral_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "id": "in_referral_1",
                    "charge": "ch_referral_1",
                    "customer": "cus_referred",
                    "subscription": "sub_referred",
                    "amount_paid": 10_700,
                    "total_excluding_tax": 10_000,
                    "status_transitions": {"paid_at": 1_800_000_000},
                }
            },
        }
        paid = post_stripe_event(referred_client, events, invoice_event)
        assert paid.status_code == 200
        commission = query_one("SELECT * FROM referral_commissions")
        assert commission
        assert commission["eligible_basis_cents"] == 10_000
        assert commission["commission_rate_bps"] == 5_000
        assert commission["commission_cents"] == 5_000
        assert commission["stripe_charge_id"] == "ch_referral_1"

        duplicate = post_stripe_event(referred_client, events, invoice_event)
        assert duplicate.json()["duplicate"] is True
        assert query_one("SELECT COUNT(*) AS total FROM referral_commissions")["total"] == 1

        partial_refund = post_stripe_event(
            referred_client,
            events,
            {
                "id": "evt_refund_referral_1",
                "type": "charge.refunded",
                "data": {
                    "object": {
                        "id": "ch_referral_1",
                        "invoice": "in_referral_1",
                        "amount": 10_700,
                        "amount_refunded": 5_350,
                    }
                },
            },
        )
        assert partial_refund.status_code == 200
        commission = query_one("SELECT * FROM referral_commissions")
        assert commission["reversed_cents"] == 2_500
        assert commission["status"] == "adjusted"

        with db_session() as conn:
            conn.execute(
                "UPDATE referral_commissions SET eligible_on=? WHERE id=?",
                (date.today().isoformat(), commission["id"]),
            )
        marked_paid = admin_client.post(
            f"/referrals/commissions/{commission['id']}/paid",
            data={"payout_reference": "ACH-TEST-001"},
            follow_redirects=False,
        )
        assert marked_paid.status_code == 303
        commission = query_one("SELECT * FROM referral_commissions")
        assert commission["paid_cents"] == 2_500
        assert commission["payout_reference"] == "ACH-TEST-001"
        assert commission["status"] == "adjusted_paid"

        disputed = post_stripe_event(
            referred_client,
            events,
            {
                "id": "evt_dispute_referral_1",
                "type": "charge.dispute.created",
                "data": {
                    "object": {
                        "id": "dp_referral_1",
                        "charge": "ch_referral_1",
                    }
                },
            },
        )
        assert disputed.status_code == 200
        commission = query_one("SELECT * FROM referral_commissions")
        assert commission["reversed_cents"] == 5_000
        assert commission["status"] == "reversed"
        assert commission["reversal_event_type"] == "charge.dispute.created"
        assert query_one(
            """SELECT COUNT(*) AS total FROM audit_events
            WHERE event_type IN (
              'referral.commission_earned',
              'referral.commission_adjusted',
              'referral.commission_paid'
            )"""
        )["total"] == 4
        adjusted_portal = admin_client.get(portal_path)
        assert "Refund or dispute adjustment awaiting offset: $25.00" in adjusted_portal.text

        second_paid = post_stripe_event(
            referred_client,
            events,
            {
                "id": "evt_invoice_referral_2",
                "type": "invoice.paid",
                "data": {
                    "object": {
                        "id": "in_referral_2",
                        "charge": "ch_referral_2",
                        "customer": "cus_referred",
                        "subscription": "sub_referred",
                        "amount_paid": 10_000,
                        "total_excluding_tax": 10_000,
                        "status_transitions": {"paid_at": 1_800_100_000},
                    }
                },
            },
        )
        assert second_paid.status_code == 200
        second_commission = query_one(
            "SELECT * FROM referral_commissions WHERE stripe_invoice_id='in_referral_2'"
        )
        assert second_commission["commission_cents"] == 5_000
        with db_session() as conn:
            conn.execute(
                "UPDATE referral_commissions SET eligible_on=? WHERE id=?",
                (date.today().isoformat(), second_commission["id"]),
            )
        settlement_page = admin_client.get("/referrals")
        assert "$25.00 cash" in settlement_page.text
        assert "$25.00 applied to prior adjustment" in settlement_page.text
        second_settlement = admin_client.post(
            f"/referrals/commissions/{second_commission['id']}/paid",
            data={"payout_reference": "ACH-TEST-002-OFFSET"},
            follow_redirects=False,
        )
        assert second_settlement.status_code == 303
        second_commission = query_one(
            "SELECT * FROM referral_commissions WHERE stripe_invoice_id='in_referral_2'"
        )
        assert second_commission["paid_cents"] == 2_500
        assert second_commission["offset_applied_cents"] == 2_500
        assert second_commission["status"] == "paid_with_offset"
        settled_portal = admin_client.get(portal_path)
        assert "Refund or dispute adjustment awaiting offset" not in settled_portal.text
        assert "Total earned</span><strong>$50.00" in settled_portal.text
        assert "Paid</span><strong>$50.00" in settled_portal.text
        assert query_one(
            """SELECT COUNT(*) AS total FROM audit_events
            WHERE event_type IN (
              'referral.commission_earned',
              'referral.commission_adjusted',
              'referral.commission_paid'
            )"""
        )["total"] == 6

        exported = export_organization_data(source_org_id)
        assert len(exported["referral_partners"]) == 1
        assert len(exported["referral_attributions"]) == 1
        assert len(exported["referral_commissions"]) == 2
        assert exported["referral_commissions"][0]["commission_cents"] == 5_000


def test_referral_program_blocks_self_referrals_and_non_admin_management(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "referral-access.db"))
    monkeypatch.setattr(main_module, "REFERRAL_ADMIN_EMAIL", ADMIN_EMAIL)

    with TestClient(app) as admin_client:
        source_org_id = signup(admin_client, ADMIN_EMAIL, "Outside The Wire Logistics")
        with db_session() as conn:
            partner_id = conn.execute(
                """INSERT INTO referral_partners
                (source_organization_id,display_name,email,referral_code,
                 portal_token_hash,active,terms_version,terms_accepted_at)
                VALUES (?,?,?,?,?,1,?,CURRENT_TIMESTAMP)""",
                (
                    source_org_id,
                    "Jordan Driver",
                    "driver@example.com",
                    "COSSELFTEST1",
                    "0" * 64,
                    main_module.REFERRAL_TERMS_VERSION,
                ),
            ).lastrowid
        with TestClient(app) as self_client:
            assert self_client.get(
                "/r/COSSELFTEST1",
                follow_redirects=False,
            ).status_code == 303
            self_org_id = signup(
                self_client,
                "driver@example.com",
                "Driver's Own Carrier",
            )
        assert query_one(
            "SELECT id FROM referral_attributions WHERE referred_organization_id=?",
            (self_org_id,),
        ) is None
        assert query_one(
            "SELECT COUNT(*) AS total FROM referral_attributions WHERE referral_partner_id=?",
            (partner_id,),
        )["total"] == 0

        with TestClient(app) as other_client:
            signup(other_client, "other-owner@example.com", "Other Carrier")
            forbidden = other_client.get("/referrals")
            assert forbidden.status_code == 403
            dashboard = other_client.get("/dashboard")
            assert 'href="/referrals"' not in dashboard.text


def test_referral_terms_and_commission_basis_are_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "referral-terms.db"))
    with TestClient(app) as client:
        terms = client.get("/referral-terms")
        assert terms.status_code == 200
        assert 'content="noindex, follow"' in terms.text
        assert "50% of eligible CarrierOS subscription revenue" in terms.text
        assert "Taxes, refunds, credits, discounts, chargebacks" in terms.text
        robots = client.get("/robots.txt")
        assert "Disallow: /referrals" in robots.text
        assert "Disallow: /referral-program/portal/" in robots.text

    assert referral_invoice_basis_cents(
        {"amount_paid": 10_700, "total_excluding_tax": 10_000}
    ) == 10_000
    assert referral_invoice_basis_cents(
        {"amount_paid": 5_000, "total_excluding_tax": 7_500}
    ) == 5_000
    assert referral_invoice_basis_cents({"amount_paid": 2_500}) == 2_500
    assert referral_invoice_basis_cents({"amount_paid": 0}) == 0
