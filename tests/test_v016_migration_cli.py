from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts.migrate_v016_foundation import _backup, _report


def test_migration_backup_is_verified_and_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO evidence (value) VALUES ('preserved')")
    _backup(source, backup)
    with sqlite3.connect(backup) as conn:
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT value FROM evidence").fetchone()[0] == "preserved"
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        _backup(source, backup)


def test_migration_report_records_integrity_and_version(tmp_path: Path) -> None:
    database = tmp_path / "report.db"
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA user_version=13")
    report = _report(database, mode="dry-run", validation={"valid": True})
    assert report["schema_version"] == 13
    assert report["expected_schema_version"] == 13
    assert report["integrity_check"] == "ok"
    assert report["validation"] == {"valid": True}
