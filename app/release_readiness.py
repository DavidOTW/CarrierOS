"""Production release-readiness checks for the v0.16 beta gate.

The checks are deliberately side-effect free: they do not create directories,
modify databases, or print secret values. They report whether a release has the
controls required before a human approves a production promotion.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

EXPECTED_SCHEMA_VERSION = 15
STRIPE_PRICE_KEYS = (
    "STRIPE_PRICE_CARRIER_STARTUP",
    "STRIPE_PRICE_OWNER_OPERATOR",
    "STRIPE_PRICE_STARTER_FLEET",
    "STRIPE_PRICE_SMALL_FLEET",
    "STRIPE_PRICE_GROWING_FLEET",
)
PRODUCTION_SCANNERS = {"clamav", "managed", "s3-antivirus", "virustotal"}
PLACEHOLDER_VALUES = {
    "",
    "replace_me",
    "sk_test_replace_me",
    "whsec_replace_me",
    "price_replace_me",
    "generate-a-random-value-with-at-least-32-characters",
}


def _configured(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return bool(normalized) and normalized not in PLACEHOLDER_VALUES


def _absolute_path(value: str) -> bool:
    """Accept POSIX production paths even when the gate runs on Windows."""

    return Path(value).is_absolute() or value.startswith(("/", "\\"))


def _check(checks: list[dict[str, str]], blockers: list[str], name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "status": "ok" if ok else "blocked", "detail": detail})
    if not ok:
        blockers.append(f"{name}: {detail}")


def verify_sqlite_database(path: Path, *, expected_schema: int = EXPECTED_SCHEMA_VERSION) -> dict[str, object]:
    """Return a non-mutating integrity and schema report for one SQLite file."""

    if not path.exists():
        return {"ok": False, "detail": "database file is missing", "schema_version": None}
    try:
        with sqlite3.connect(path, timeout=5) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
        return {"ok": False, "detail": f"database could not be checked ({type(exc).__name__})", "schema_version": None}
    if not integrity or integrity[0] != "ok":
        return {"ok": False, "detail": "PRAGMA quick_check did not return ok", "schema_version": schema_version}
    if schema_version < expected_schema:
        return {
            "ok": False,
            "detail": f"schema version {schema_version} is older than required {expected_schema}",
            "schema_version": schema_version,
        }
    return {"ok": True, "detail": f"SQLite integrity ok; schema version {schema_version}", "schema_version": schema_version}


def verify_latest_backup(path: Path, *, expected_schema: int = EXPECTED_SCHEMA_VERSION) -> dict[str, object]:
    """Verify the newest retained CarrierOS backup without changing it."""

    if not path.exists() or not path.is_dir():
        return {"ok": False, "detail": "backup directory is missing", "path": None}
    backups = sorted(path.glob("carrieros-*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not backups:
        return {"ok": False, "detail": "no retained carrieros-*.db backup was found", "path": None}
    latest = backups[0]
    report = verify_sqlite_database(latest, expected_schema=expected_schema)
    return {
        "ok": bool(report["ok"]),
        "detail": f"{report['detail']} ({latest.name})",
        "path": str(latest),
        "backup_count": len(backups),
    }


def evaluate_release_readiness(
    environ: Mapping[str, str] | None = None,
    *,
    database_path: Path | str | None = None,
    backup_dir: Path | str | None = None,
) -> dict[str, object]:
    """Evaluate production beta prerequisites and return safe, structured evidence."""

    env = dict(os.environ if environ is None else environ)
    checks: list[dict[str, str]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    environment = env.get("CARRIEROS_ENV", "development").strip().lower()
    _check(checks, blockers, "production environment", environment == "production", "CARRIEROS_ENV must be production")

    secret = env.get("CARRIEROS_SECRET", "").strip()
    _check(checks, blockers, "session secret", len(secret) >= 32 and _configured(secret), "CARRIEROS_SECRET must be a non-placeholder value with at least 32 characters")

    public_url = env.get("CARRIEROS_PUBLIC_URL", "").strip()
    parsed_url = urlsplit(public_url)
    _check(checks, blockers, "canonical public URL", parsed_url.scheme == "https" and bool(parsed_url.netloc), "CARRIEROS_PUBLIC_URL must be an https URL")

    billing_mode = env.get("CARRIEROS_BILLING_MODE", "stripe").strip().lower()
    _check(checks, blockers, "billing mode", billing_mode == "stripe", "production beta billing must use Stripe")
    stripe_secret = env.get("STRIPE_SECRET_KEY", "").strip()
    _check(checks, blockers, "Stripe live secret", stripe_secret.startswith("sk_live_") and _configured(stripe_secret), "STRIPE_SECRET_KEY must be a configured live-mode key")
    webhook_secret = env.get("STRIPE_WEBHOOK_SECRET", "").strip()
    _check(checks, blockers, "Stripe webhook signing secret", webhook_secret.startswith("whsec_") and _configured(webhook_secret), "STRIPE_WEBHOOK_SECRET must be configured")
    for key in STRIPE_PRICE_KEYS:
        value = env.get(key, "").strip()
        _check(checks, blockers, key, value.startswith("price_") and _configured(value), f"{key} must be configured")

    storage_root = env.get("CARRIEROS_PRIVATE_STORAGE_ROOT", "").strip()
    _check(checks, blockers, "private document storage", bool(storage_root) and _absolute_path(storage_root), "CARRIEROS_PRIVATE_STORAGE_ROOT must be an absolute private path")
    encrypted = env.get("CARRIEROS_STORAGE_ENCRYPTED_AT_REST", "").strip().lower() == "true"
    _check(checks, blockers, "storage encryption", encrypted, "CARRIEROS_STORAGE_ENCRYPTED_AT_REST must be true")

    scanner = env.get("CARRIEROS_MALWARE_SCANNER", "").strip().lower()
    _check(checks, blockers, "malware scanner", scanner in PRODUCTION_SCANNERS, "CARRIEROS_MALWARE_SCANNER must name a managed production scanner (manual/mock-clean are not release gates)")

    database = Path(database_path or env.get("CARRIEROS_DB", "carrieros_v02.db"))
    database_report = verify_sqlite_database(database)
    _check(checks, blockers, "database integrity", bool(database_report["ok"]), str(database_report["detail"]))

    backup_root = Path(backup_dir or env.get("CARRIEROS_BACKUP_DIR", ""))
    backup_report = verify_latest_backup(backup_root)
    _check(checks, blockers, "backup restoration evidence", bool(backup_report["ok"]), str(backup_report["detail"]))

    if environment != "production":
        warnings.append("This report is intended to gate a production promotion; non-production runs are expected to be blocked.")
    return {"ready": not blockers, "environment": environment, "checks": checks, "blockers": blockers, "warnings": warnings}
