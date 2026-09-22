from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.demo_data import FREE_TIER_COPY, build_public_sample_data
from app.main import app


def test_public_sample_data_uses_one_relative_date_anchor() -> None:
    anchor = date(2030, 2, 8)
    sample = build_public_sample_data(anchor)

    assert sample["week_label"] == f"Week {anchor.isocalendar().week}"
    assert sample["month_label"] == "February"
    assert sample["month_to_date_label"] == "February month to date"
    assert [load["number"] for load in sample["marketing_loads"]] == [
        "FRT-1048",
        "FRT-1047",
        "FRT-1046",
    ]
    load_1048 = sample["loads_by_number"]["FRT-1048"]
    load_1045 = sample["loads_by_number"]["FRT-1045"]
    assert load_1048["pickup_date"] == (anchor - timedelta(days=3)).isoformat()
    assert load_1048["delivery_date"] == (anchor - timedelta(days=2)).isoformat()
    assert load_1045["pickup_date"] == (anchor - timedelta(days=1)).isoformat()
    assert load_1045["delivery_date"] == anchor.isoformat()


def test_home_and_demo_share_sample_ids_dates_and_free_tier_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "public-demo.db"))
    with TestClient(app) as client:
        home = client.get("/")
        demo = client.get("/demo")

    assert home.status_code == 200
    assert demo.status_code == 200
    assert "OTW-1048" not in home.text
    assert "FRT-1048" in home.text
    assert "FRT-1048" in demo.text
    assert FREE_TIER_COPY in home.text
    assert FREE_TIER_COPY in demo.text
    assert "Week 29" not in home.text
    assert "Week 29" not in demo.text
    assert "data-tour-start" in demo.text
    assert "Step 1 of 5" in demo.text
    assert "tour_start" in demo.text
    assert "tour_step" in demo.text
    assert "tour_complete" in demo.text
    assert "Ready to run your own fleet?" in demo.text
    assert "CEO cockpit" in demo.text
    assert "Break-even pace" in demo.text
    assert "Broker scorecard" in demo.text


def test_demo_has_no_per_screen_signup_ctas_and_mobile_overflow_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "demo-layout.db"))
    with TestClient(app) as client:
        demo = client.get("/demo")
        css = client.get("/static/app.css")

    assert demo.text.count('href="/signup?plan=free_operator"') >= 2
    assert '<div class="demo-heading"><div><span>Dispatch</span>' in demo.text
    assert "data-tour-complete" in demo.text
    assert ".demo-main,.demo-content,.demo-panel,.demo-card{min-width:0;max-width:100%}" in css.text
    assert ".demo-table-wrap>table{width:max-content;min-width:100%}" in css.text
    assert ".demo-card-heading{align-items:flex-start;flex-wrap:wrap}" in css.text


def test_founder_experience_phrase_is_consistent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "founder-copy.db"))
    with TestClient(app) as client:
        home = client.get("/")
        solutions = client.get("/solutions")

    combined = f"{home.text}\n{solutions.text}"
    assert "nearly two decades" in combined.lower()
    assert "20 years" not in combined.lower()


def test_pricing_route_uses_the_shared_free_tier_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "pricing.db"))
    with TestClient(app) as client:
        pricing = client.get("/pricing")

    assert pricing.status_code == 200
    assert FREE_TIER_COPY in pricing.text
    assert '<link rel="canonical" href="https://otwcarrieros.com/pricing">' in pricing.text


def test_public_shell_and_service_worker_fail_cleanly_offline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "public-shell.db"))
    with TestClient(app) as client:
        home = client.get("/")
        worker = client.get("/service-worker.js")

    assert '<meta name="mobile-web-app-capable" content="yes">' in home.text
    assert "new Response('Offline',{status:503" in worker.text
    assert "carrieros-v0.16.0a19" in worker.text
