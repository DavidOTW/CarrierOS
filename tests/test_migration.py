from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re

from fastapi.testclient import TestClient

from app.db import db_session, query_one
from app.main import app


def _signup(client: TestClient, email: str) -> None:
    response = client.post(
        "/signup",
        data={
            "full_name": "Migration Owner",
            "company_name": "Migration Fleet",
            "email": email,
            "password": "StrongPassword!42",
            "plan": "owner_operator",
            "accepted_terms": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    organization = query_one("SELECT organization_id FROM users WHERE email=?", (email,))
    with db_session() as conn:
        conn.execute(
            "UPDATE organizations SET subscription_status='active' WHERE id=?",
            (organization["organization_id"],),
        )


def test_csv_migration_previews_then_imports_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "migration.db"))
    with TestClient(app) as client:
        _signup(client, "migration@example.com")
        assert client.post(
            "/vehicles",
            data={"name": "Truck 1", "equipment_type": "Box Truck", "active": "on"},
            follow_redirects=False,
        ).status_code == 303
        vehicle = query_one("SELECT id FROM vehicles WHERE name='Truck 1'")
        assert client.post(
            "/drivers",
            data={
                "name": "Alex Driver",
                "role": "Driver",
                "pay_model": "Flat Rate per Load",
                "vehicle_id": str(vehicle["id"]),
                "flat_rate_per_load": "300",
                "mpg": "9.5",
                "maintenance_per_mile": "0.22",
                "active": "on",
            },
            follow_redirects=False,
        ).status_code == 303

        csv_text = "\n".join(
            [
                "Load number,Pickup date,Delivery date,Status,Driver,Unit,Broker,Origin,Destination,Revenue,Loaded miles,Deadhead miles,Notes",
                f"MIG-001,{date.today().isoformat()},{(date.today() + timedelta(days=2)).isoformat()},Delivered,Alex Driver,Truck 1,Test Broker,Nashville TN,Atlanta GA,2200,250,20,Imported history",
            ]
        )
        preview = client.post(
            "/migration/preview",
            files={"document": ("history.csv", csv_text.encode(), "text/csv")},
        )
        assert preview.status_code == 200
        assert "Ready to import" in preview.text
        assert "MIG-001" in preview.text
        assert query_one("SELECT COUNT(*) AS total FROM loads")["total"] == 0
        token = re.search(r'name="preview_token" value="([^"]+)"', preview.text)
        assert token

        confirmed = client.post(
            "/migration/confirm",
            data={"preview_token": token.group(1), "confirm_import": "1"},
            follow_redirects=False,
        )
        assert confirmed.status_code == 303
        assert confirmed.headers["location"] == "/loads"
        load = query_one("SELECT * FROM loads WHERE load_number='MIG-001'")
        assert load["status_code"] == "DELIVERED_DOCUMENTS_PENDING"
        assert load["source_row"] == 2
        assert query_one("SELECT COUNT(*) AS total FROM load_revenue_items")["total"] == 1
        assert query_one("SELECT COUNT(*) AS total FROM load_status_history")["total"] == 1
        assert query_one("SELECT source_filename FROM organizations")["source_filename"] == "CSV migration"


def test_csv_migration_rejects_duplicate_and_unknown_driver(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "migration-errors.db"))
    with TestClient(app) as client:
        _signup(client, "migration-errors@example.com")
        csv_text = "\n".join(
            [
                "Load number,Pickup date,Delivery date,Driver,Revenue",
                f"BAD-001,{date.today().isoformat()},{date.today().isoformat()},Missing Driver,1200",
            ]
        )
        response = client.post(
            "/migration/preview",
            files={"document": ("history.csv", csv_text.encode(), "text/csv")},
        )
        assert response.status_code == 422
        assert "Driver must exactly match an active driver profile" in response.text
        assert query_one("SELECT COUNT(*) AS total FROM loads")["total"] == 0
