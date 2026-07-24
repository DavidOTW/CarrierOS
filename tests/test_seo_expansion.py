from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import SEO_PAGES, app


NEW_SEARCH_PAGES = {
    "/small-fleet-tms": "A transportation management system sized for a small carrier.",
    "/trucking-dispatch-software": "Dispatch the load with the decision and the details still attached.",
    "/rate-confirmation-management-software": "Catch the booking-to-RateCon difference",
    "/trucking-document-management-software": "Put the document beside the decision it supports.",
    "/trucking-accounts-receivable-software": "A delivered load is not finished",
    "/trucking-compliance-management-software": "Keep important renewal dates visible",
    "/owner-operator-business-software": "Run the business behind the truck",
    "/box-truck-fleet-management-software": "Manage box-truck freight as a business",
    "/hotshot-trucking-software": "Make the hotshot rate answer",
}


def test_solution_hub_and_search_pages_are_indexable_and_connected(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "seo-expansion.db"))
    with TestClient(app) as client:
        hub = client.get("/solutions")
        assert hub.status_code == 200
        assert hub.headers.get("x-robots-tag") is None
        assert 'content="index, follow' in hub.text
        assert (
            '<link rel="canonical" href="https://otwcarrieros.com/solutions">'
            in hub.text
        )
        assert "Small-carrier software built around the work" in hub.text
        assert "Keep the operating record connected from the first rate check" in hub.text
        assert "&lt;built-in method" not in hub.text
        assert '"@type": "CollectionPage"' in hub.text
        assert '"@type": "BreadcrumbList"' in hub.text

        titles: set[str] = set()
        descriptions: set[str] = set()
        for path, phrase in NEW_SEARCH_PAGES.items():
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers.get("x-robots-tag") is None
            assert response.headers["cache-control"].startswith("public")
            assert phrase in response.text
            assert 'content="index, follow' in response.text
            assert (
                f'<link rel="canonical" href="https://otwcarrieros.com{path}">'
                in response.text
            )
            assert 'href="/solutions"' in response.text
            assert '"@type": "FAQPage"' in response.text
            assert '"@type": "BreadcrumbList"' in response.text
            assert '"@type": "WebApplication"' in response.text

            title = re.search(r"<title>(.*?)</title>", response.text, re.DOTALL)
            description = re.search(
                r'<meta name="description" content="([^"]+)">', response.text
            )
            assert title
            assert description
            titles.add(title.group(1).strip())
            descriptions.add(description.group(1).strip())

        assert len(titles) == len(NEW_SEARCH_PAGES)
        assert len(descriptions) == len(NEW_SEARCH_PAGES)
        for path in NEW_SEARCH_PAGES:
            assert f'href="{path}"' in hub.text


def test_help_center_header_no_longer_overrides_indexable_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "help-indexing.db"))
    with TestClient(app) as client:
        for path in ("/help", "/help/dispatch", "/help/ratecon-inbox"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers.get("x-robots-tag") is None
            assert response.headers["cache-control"].startswith("public")
            assert 'content="index, follow' in response.text
            assert '"@type": "BreadcrumbList"' in response.text


def test_sitemap_and_internal_links_cover_the_public_search_architecture(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "seo-map.db"))
    with TestClient(app) as client:
        sitemap = client.get("/sitemap.xml")
        assert sitemap.status_code == 200
        for path in ("/solutions", "/help", *NEW_SEARCH_PAGES):
            assert f"<loc>https://otwcarrieros.com{path}</loc>" in sitemap.text
        assert sitemap.text.count("<loc>") == len(set(re.findall(r"<loc>(.*?)</loc>", sitemap.text)))

        robots = client.get("/robots.txt")
        assert "Disallow: /help" not in robots.text
        assert "Disallow: /solutions" not in robots.text
        assert "Disallow: /dashboard" in robots.text

        home = client.get("/")
        assert 'href="/solutions"' in home.text
        assert 'href="/owner-operator-business-software"' in home.text
        assert 'href="/box-truck-fleet-management-software"' in home.text
        assert 'href="/hotshot-trucking-software"' in home.text

        login = client.get("/login")
        assert login.headers["x-robots-tag"] == "noindex, nofollow"


def test_every_search_page_has_substantial_unique_operating_content() -> None:
    assert len(SEO_PAGES) == 13
    for page in SEO_PAGES.values():
        assert len(page["benefits"]) == 4
        assert len(page["workflow"]) == 3
        assert len(page["deep_dives"]) == 2
        assert len(page["faqs"]) >= 3
        assert len(page["related"]) == 4
        combined = " ".join(
            [
                page["heading"],
                page["lead"],
                page["problem_copy"],
                *(copy for _, copy in page["benefits"]),
                *(copy for _, copy in page["workflow"]),
                *(copy for _, copy, _ in page["deep_dives"]),
                *(answer for _, answer in page["faqs"]),
            ]
        )
        assert len(combined.split()) >= 250
