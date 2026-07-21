from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app import stripe_billing
from app.db import (
    create_database_backup,
    create_password_reset_token,
    db_session,
    hash_password,
    password_needs_rehash,
    query_one,
    token_digest,
    verify_password,
)
from app.main import app


def create_active_account(client: TestClient, email: str = "owner@example.com") -> None:
    response = client.post(
        "/signup",
        data={
            "full_name": "Fleet Owner",
            "company_name": "Ready Carrier",
            "email": email,
            "password": "StrongPassword!42",
            "plan": "owner_operator",
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


def configure_stripe(monkeypatch: pytest.MonkeyPatch, secret_key: str) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", secret_key)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_example")
    monkeypatch.setenv("STRIPE_PRICE_OWNER_OPERATOR", "price_owner")
    monkeypatch.setenv("STRIPE_PRICE_STARTER_FLEET", "price_starter")
    monkeypatch.setenv("STRIPE_PRICE_SMALL_FLEET", "price_small")
    monkeypatch.setenv("STRIPE_PRICE_GROWING_FLEET", "price_growing")


def test_production_never_opens_signup_with_test_stripe_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "prelaunch.db"))
    configure_stripe(monkeypatch, "sk_test_example")
    monkeypatch.setattr(main_module, "IS_PRODUCTION", True)
    monkeypatch.setattr(main_module, "BILLING_MODE", "stripe")
    assert stripe_billing.stripe_live_configured() is False
    with TestClient(app) as client:
        response = client.get("/signup")
        assert response.status_code == 200
        assert "Customer billing is almost ready" in response.text
        assert "test checkout" in response.text


def test_password_hashes_upgrade_and_reset_tokens_are_single_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "recovery.db"))
    main_module.reset_attempts.clear()
    legacy_salt = "a" * 32
    import hashlib

    legacy_digest = hashlib.pbkdf2_hmac(
        "sha256", b"LegacyPassword!42", legacy_salt.encode(), 180_000
    ).hex()
    legacy_hash = f"{legacy_salt}${legacy_digest}"
    assert verify_password("LegacyPassword!42", legacy_hash)
    assert password_needs_rehash(legacy_hash)
    assert not password_needs_rehash(hash_password("CurrentPassword!42"))

    with TestClient(app) as client:
        create_active_account(client)
        user = query_one("SELECT * FROM users WHERE email='owner@example.com'")
        token = create_password_reset_token(int(user["id"]))
        client.get("/logout")
        response = client.post(
            "/reset-password",
            data={
                "token": token,
                "password": "ReplacementPassword!43",
                "confirm_password": "ReplacementPassword!43",
            },
        )
        assert response.status_code == 200
        assert "Your password has been changed" in response.text
        updated = query_one("SELECT password_hash FROM users WHERE id=?", (user["id"],))
        assert verify_password("ReplacementPassword!43", updated["password_hash"])

        replay = client.post(
            "/reset-password",
            data={
                "token": token,
                "password": "AnotherPassword!44",
                "confirm_password": "AnotherPassword!44",
            },
        )
        assert replay.status_code == 400
        assert "invalid or has expired" in replay.text


def test_onboarding_links_are_hashed_expiring_and_single_submission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "onboarding.db"))
    with TestClient(app) as client:
        create_active_account(client)
        invite = client.post(
            "/onboarding/invite",
            data={"full_name": "Driver One", "email": "driver@example.com"},
        )
        assert invite.status_code == 200
        marker = "/onboard/"
        start = invite.text.index(marker) + len(marker)
        token = invite.text[start:].split("<", 1)[0]
        row = query_one("SELECT * FROM onboarding_applications")
        assert row["token"] == token_digest(token)
        assert row["token"] != token
        assert row["expires_at"]
        assert client.get(f"/onboard/{token}").status_code == 200
        submitted = client.post(
            f"/onboard/{token}",
            data={"full_name": "Driver One", "license_state": "TN"},
        )
        assert submitted.status_code == 200
        assert "has been submitted" in submitted.text
        replay = client.post(
            f"/onboard/{token}",
            data={"full_name": "Changed Name", "license_state": "KY"},
        )
        assert replay.status_code == 200
        unchanged = query_one("SELECT full_name, license_state FROM onboarding_applications")
        assert unchanged["full_name"] == "Driver One"
        assert unchanged["license_state"] == "TN"


def test_consistent_backup_and_authenticated_company_export(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = tmp_path / "export.db"
    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("CARRIEROS_DB", str(database))
    monkeypatch.setenv("CARRIEROS_BACKUP_DIR", str(backup_dir))
    with TestClient(app) as client:
        create_active_account(client)
        backup = create_database_backup()
        assert backup and backup.exists()
        with sqlite3.connect(backup) as conn:
            assert conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 1

        response = client.post("/settings/export")
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        payload = json.loads(response.text)
        assert payload["organization"]["name"] == "Ready Carrier"
        assert payload["users"][0]["email"] == "owner@example.com"
        assert "password_hash" not in payload["users"][0]


@pytest.mark.parametrize(
    ("path", "redacted"),
    [
        ("/reset-password?token=secret", "/reset-password?[redacted]"),
        ("/onboard/secret", "/onboard/[redacted]"),
    ],
)
def test_bearer_tokens_are_redacted_from_access_logs(path: str, redacted: str) -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1", "GET", path, "1.1", 200),
        None,
    )
    assert main_module.SensitiveAccessLogFilter().filter(record)
    assert record.args[2] == redacted
