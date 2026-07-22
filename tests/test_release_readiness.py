from __future__ import annotations

import sqlite3
from pathlib import Path

from app.release_readiness import evaluate_release_readiness, verify_latest_backup, verify_sqlite_database


def _production_env(storage_root: str = "/data/private-documents") -> dict[str, str]:
    return {
        "CARRIEROS_ENV": "production",
        "CARRIEROS_SECRET": "s" * 40,
        "CARRIEROS_PUBLIC_URL": "https://otwcarrieros.com",
        "CARRIEROS_BILLING_MODE": "stripe",
        "STRIPE_SECRET_KEY": "sk_live_example",
        "STRIPE_WEBHOOK_SECRET": "whsec_example",
        "STRIPE_PRICE_CARRIER_STARTUP": "price_startup",
        "STRIPE_PRICE_OWNER_OPERATOR": "price_owner",
        "STRIPE_PRICE_STARTER_FLEET": "price_starter",
        "STRIPE_PRICE_SMALL_FLEET": "price_small",
        "STRIPE_PRICE_GROWING_FLEET": "price_growing",
        "CARRIEROS_PRIVATE_STORAGE_ROOT": storage_root,
        "CARRIEROS_STORAGE_ENCRYPTED_AT_REST": "true",
        "CARRIEROS_MALWARE_SCANNER": "clamav",
    }


def _database(path: Path, schema: int = 15) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(f"PRAGMA user_version={schema}")
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY)")


def test_release_gate_requires_live_controls_and_verified_backup(tmp_path: Path) -> None:
    database = tmp_path / "carrieros.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    _database(database)
    _database(backup_dir / "carrieros-20260721-010000.db")
    report = evaluate_release_readiness(_production_env(str(tmp_path / "private-documents")), database_path=database, backup_dir=backup_dir)
    assert report["ready"] is True
    assert all(check["status"] == "ok" for check in report["checks"])
    assert verify_sqlite_database(database)["ok"] is True
    assert verify_latest_backup(backup_dir)["ok"] is True


def test_release_gate_never_accepts_test_billing_or_manual_scanning(tmp_path: Path) -> None:
    database = tmp_path / "carrieros.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    _database(database)
    _database(backup_dir / "carrieros-20260721-010000.db")
    env = _production_env(str(tmp_path / "private-documents"))
    env["STRIPE_SECRET_KEY"] = "sk_test_example"
    env["CARRIEROS_MALWARE_SCANNER"] = "manual"
    report = evaluate_release_readiness(env, database_path=database, backup_dir=backup_dir)
    assert report["ready"] is False
    assert any("Stripe live secret" in blocker for blocker in report["blockers"])
    assert any("malware scanner" in blocker for blocker in report["blockers"])


def test_release_gate_reports_missing_backup_without_mutating_database(tmp_path: Path) -> None:
    database = tmp_path / "carrieros.db"
    _database(database)
    report = evaluate_release_readiness(_production_env(str(tmp_path / "private-documents")), database_path=database, backup_dir=tmp_path / "missing")
    assert report["ready"] is False
    assert any("backup restoration evidence" in blocker for blocker in report["blockers"])
    assert not (tmp_path / "missing").exists()
