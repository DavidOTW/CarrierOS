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
