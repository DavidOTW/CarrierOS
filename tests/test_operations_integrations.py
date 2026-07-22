from __future__ import annotations

import sys
from pathlib import Path

from app.emailing import smtp_configured
from app.offsite_backup import upload_backup_if_configured


def test_smtp_requires_auth_credentials_by_default(monkeypatch) -> None:
    monkeypatch.setenv("CARRIEROS_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("CARRIEROS_SMTP_FROM", "CarrierOS <support@example.test>")
    monkeypatch.setenv("CARRIEROS_SMTP_SECURITY", "starttls")
    monkeypatch.delenv("CARRIEROS_SMTP_USERNAME", raising=False)
    monkeypatch.delenv("CARRIEROS_SMTP_PASSWORD", raising=False)
    assert smtp_configured() is False

    monkeypatch.setenv("CARRIEROS_SMTP_USERNAME", "apikey")
    monkeypatch.setenv("CARRIEROS_SMTP_PASSWORD", "secret")
    assert smtp_configured() is True


def test_smtp_can_explicitly_use_anonymous_relay(monkeypatch) -> None:
    monkeypatch.setenv("CARRIEROS_SMTP_HOST", "relay.example.test")
    monkeypatch.setenv("CARRIEROS_SMTP_FROM", "CarrierOS <support@example.test>")
    monkeypatch.setenv("CARRIEROS_SMTP_SECURITY", "none")
    monkeypatch.setenv("CARRIEROS_SMTP_AUTH_REQUIRED", "false")
    monkeypatch.delenv("CARRIEROS_SMTP_USERNAME", raising=False)
    monkeypatch.delenv("CARRIEROS_SMTP_PASSWORD", raising=False)
    assert smtp_configured() is True


def test_offsite_backup_upload_is_optional_and_verifies_object(monkeypatch, tmp_path: Path) -> None:
    backup = tmp_path / "carrieros-20260722.db"
    backup.write_bytes(b"verified backup")
    assert upload_backup_if_configured(backup) is None

    uploaded: dict[str, object] = {}

    class FakeClient:
        def upload_file(self, filename, bucket, key, ExtraArgs):
            uploaded.update(filename=filename, bucket=bucket, key=key, extra=ExtraArgs)

        def head_object(self, **kwargs):
            return {"ContentLength": backup.stat().st_size, "ServerSideEncryption": "AES256"}

    class FakeBoto3:
        @staticmethod
        def client(name, **kwargs):
            assert name == "s3"
            assert kwargs["region_name"] == "us-east-1"
            return FakeClient()

    monkeypatch.setitem(sys.modules, "boto3", FakeBoto3)
    monkeypatch.setenv("CARRIEROS_OFFSITE_BACKUP_BUCKET", "carrieros-backups")
    monkeypatch.setenv("CARRIEROS_OFFSITE_BACKUP_PREFIX", "production")
    monkeypatch.setenv("CARRIEROS_OFFSITE_BACKUP_REGION", "us-east-1")
    report = upload_backup_if_configured(backup)
    assert report == {
        "configured": True,
        "uploaded": True,
        "bucket": "carrieros-backups",
        "key": "production/carrieros-20260722.db",
        "size_bytes": len(b"verified backup"),
        "server_side_encryption": "AES256",
    }
    assert uploaded["extra"] == {"ServerSideEncryption": "AES256"}
