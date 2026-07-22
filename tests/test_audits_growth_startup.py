from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.audits import AuditFileError, audit_uploaded_document
from app.db import db_session, query_one
from app.growth import equipment_finance_audit, growth_mentor_findings
from app.main import app


def create_account(
    client: TestClient,
    email: str,
    *,
    company: str = "Test Carrier",
    plan: str = "owner_operator",
) -> None:
    response = client.post(
        "/signup",
        data={
            "full_name": "Fleet Owner",
            "company_name": company,
            "email": email,
            "password": "StrongPassword!42",
            "plan": plan,
            "accepted_terms": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    user = query_one("SELECT organization_id FROM users WHERE email=?", (email,))
    with db_session() as conn:
        conn.execute(
            "UPDATE organizations SET subscription_status='active' WHERE id=?",
            (user["organization_id"],),
        )


def test_bank_csv_audit_discards_raw_file_and_is_tenant_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "audits.db"))
    statement = (
        b"Date,Description,Amount\n"
        b"2026-07-01,Customer deposit,1500.00\n"
        b"2026-07-02,Fuel,-400.00\n"
    )
    with TestClient(app) as owner:
        create_account(owner, "audit-owner@example.com", company="Audit Fleet")
        response = owner.post(
            "/audits/upload",
            data={
                "document_type": "bank_statement",
                "period_start": "2026-07-01",
                "period_end": "2026-07-31",
            },
            files={"document": ("july-bank.csv", statement, "text/csv")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        audit = query_one("SELECT * FROM document_audits")
        assert audit["original_filename"] == "july-bank.csv"
        assert audit["sha256"]
        assert audit["size_bytes"] == len(statement)
        assert audit["observed_amount"] == pytest.approx(1500)
        structured = json.loads(audit["extracted_json"])
        assert structured["raw_file_retained"] is False
        assert structured["extracted"]["withdrawals"] == pytest.approx(400)
        assert "Customer deposit" not in audit["extracted_json"]
        detail = owner.get(response.headers["location"])
        assert detail.status_code == 200
        assert "raw source file was discarded" in detail.text
        audit_id = audit["id"]

    with TestClient(app) as other:
        create_account(other, "other-owner@example.com", company="Other Fleet")
        assert other.get(f"/audits/{audit_id}").status_code == 404


def test_audit_file_validation_rejects_mismatched_or_unsupported_uploads() -> None:
    with pytest.raises(AuditFileError, match="not a PDF"):
        audit_uploaded_document(
            document_type="ratecon",
            filename="fake.pdf",
            content_type="application/pdf",
            payload=b"not really a pdf",
            context={"expected_revenue": 1000},
        )
    with pytest.raises(AuditFileError, match="Only text-based PDF and CSV"):
        audit_uploaded_document(
            document_type="bank_statement",
            filename="bank.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            payload=b"spreadsheet",
            context={},
        )


def test_startup_plan_allows_zero_active_units_and_preserves_progress_by_tenant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "startup.db"))
    with TestClient(app) as startup_owner:
        create_account(startup_owner, "startup@example.com", plan="carrier_startup")
        organization = query_one("SELECT * FROM organizations WHERE owner_email='startup@example.com'")
        assert organization["active_unit_limit"] == 0
        blocked = startup_owner.post(
            "/vehicles",
            data={"name": "Too Soon", "equipment_type": "Tractor", "active": "on"},
            follow_redirects=False,
        )
        assert blocked.status_code == 303
        assert query_one(
            "SELECT COUNT(*) AS total FROM vehicles WHERE organization_id=?",
            (organization["id"],),
        )["total"] == 0
        saved = startup_owner.post(
            "/startup/entity_ein/toggle",
            data={"completed": "on", "notes": "Verified with official records."},
            follow_redirects=False,
        )
        assert saved.status_code == 303
        page = startup_owner.get("/startup")
        assert "1 of 14 steps complete" in page.text
        assert "Verified with official records." in page.text

    with TestClient(app) as other_owner:
        create_account(other_owner, "startup-other@example.com", company="Other Startup")
        page = other_owner.get("/startup")
        assert "0 of 14 steps complete" in page.text
        assert "Verified with official records." not in page.text


def test_equipment_finance_audit_calculates_payment_and_flags_weak_case() -> None:
    scenario = equipment_finance_audit(
        {
            "purchase_price": 100000,
            "down_payment": 10000,
            "apr_pct": 12,
            "term_months": 60,
            "monthly_insurance": 2000,
            "other_monthly_costs": 800,
            "monthly_miles": 4000,
            "revenue_per_mile": 2.0,
            "mpg": 7,
            "diesel_price": 4,
            "maintenance_per_mile": 0.30,
            "driver_pay_pct": 30,
            "cash_reserve": 12000,
        },
        {"target_margin_pct": 15},
    )
    assert scenario["financed_amount"] == pytest.approx(90000)
    assert scenario["monthly_payment"] > 1900
    assert scenario["remaining_cash"] == pytest.approx(2000)
    assert scenario["projected_profit"] < 0
    titles = {finding["title"] for finding in scenario["findings"]}
    assert "Projected monthly cash contribution is negative" in titles
    assert "Limited post-purchase fixed-cost runway" in titles


def test_growth_mentor_normalizes_whole_percent_company_target() -> None:
    findings = growth_mentor_findings(
        {
            "included_loads": 3,
            "revenue": 10000,
            "company_profit": 1200,
            "company_margin_pct": 0.12,
        },
        {"target_margin_pct": 10},
        1,
    )
    assert findings[1]["severity"] == "good"
    assert "10.0% target" in findings[1]["detail"]
