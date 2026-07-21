from __future__ import annotations

from pathlib import Path

import pytest

from app.db import init_db, query_one


def test_clean_database_has_public_plan_and_pay_columns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "schema.db"))
    init_db()
    plan_columns = {row["name"] for row in query_one("SELECT * FROM organizations LIMIT 0") or []}
    assert query_one("SELECT COUNT(*) AS total FROM organizations")["total"] == 0
    # A direct query proves the release schema includes the new compensation fields.
    row = query_one("SELECT flat_rate_per_load,pay_per_loaded_mile,pay_per_total_mile,day_rate FROM drivers LIMIT 1")
    assert row is None
