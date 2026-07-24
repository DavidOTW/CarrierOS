from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.help_content import HELP_GUIDES
from app.main import app


def test_help_center_lists_and_serves_every_workspace_guide(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "help-center.db"))
    with TestClient(app) as client:
        center = client.get("/help")
        assert center.status_code == 200
        assert "Know exactly what every tab does." in center.text
        assert "Guides for every workspace tab." in center.text
        assert 'href="/help/rate-quotes"' in center.text
        assert 'href="/help/referral-program"' in center.text
        assert 'href="/help/billing"' in center.text
        assert 'rel="canonical" href="https://otwcarrieros.com/help"' in center.text
        assert 'id="help-search"' in center.text
        assert 'name="q"' in center.text
        assert 'aria-describedby="help-search-status"' in center.text
        assert 'id="help-search-clear"' in center.text
        assert 'src="/static/help-search.js?v=' in center.text

        for slug, guide in HELP_GUIDES.items():
            page = client.get(f"/help/{slug}")
            assert page.status_code == 200
            assert f"<h1>{guide['title']}</h1>" in page.text
            assert "How to use it" in page.text
            assert "What to understand" in page.text
            assert (
                f'rel="canonical" href="https://otwcarrieros.com/help/{slug}"'
                in page.text
            )


def test_help_search_asset_and_public_navigation_regression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "help-search.db"))
    with TestClient(app) as client:
        search_script = client.get("/static/help-search.js")
        assert search_script.status_code == 200
        assert 'input.addEventListener("input", filterGuides)' in search_script.text
        assert 'clear?.addEventListener("click"' in search_script.text
        assert 'event.key === "/"' in search_script.text

        for path in (
            "/",
            "/solutions",
            "/small-fleet-trucking-software",
            "/help",
            "/help/dispatch",
            "/checkout",
            "/privacy",
            "/terms",
        ):
            response = client.get(path)
            assert response.status_code == 200
            assert 'class="public-nav-links"' in response.text
            assert 'class="public-mobile-menu"' in response.text
            assert 'aria-label="Mobile navigation"' in response.text
            assert 'href="/solutions"' in response.text
            assert 'href="/help"' in response.text
            assert 'href="/demo"' in response.text


def test_help_center_is_linked_and_indexed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "help-links.db"))
    with TestClient(app) as client:
        marketing = client.get("/")
        assert marketing.status_code == 200
        assert "CarrierOS Help Center" in marketing.text
        assert 'href="/help"' in marketing.text

        sitemap = client.get("/sitemap.xml")
        assert sitemap.status_code == 200
        assert "<loc>https://otwcarrieros.com/help</loc>" in sitemap.text
        for slug in HELP_GUIDES:
            assert f"<loc>https://otwcarrieros.com/help/{slug}</loc>" in sitemap.text

        assert client.get("/help/not-a-real-tab").status_code == 404
