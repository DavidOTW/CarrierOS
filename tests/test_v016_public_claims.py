from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_copy_only_claims_supported_driver_pay_models() -> None:
    public_sources = "\n".join(
        [
            (ROOT / "app" / "templates" / "marketing.html").read_text(encoding="utf-8"),
            (ROOT / "app" / "templates" / "demo.html").read_text(encoding="utf-8"),
            (ROOT / "app" / "templates" / "seo_page.html").read_text(encoding="utf-8"),
        ]
    ).lower()
    assert "hourly" not in public_sources
    assert "salary" not in public_sources
    for supported in (
        "profit split",
        "contractor gross split",
        "owner-operator split",
        "flat per load",
        "loaded-mile rate",
        "total-mile rate",
        "day rate",
    ):
        assert supported in public_sources


def test_public_sample_never_claims_live_or_approved_operational_data() -> None:
    marketing = (ROOT / "app" / "templates" / "marketing.html").read_text(encoding="utf-8").lower()
    demo = (ROOT / "app" / "templates" / "demo.html").read_text(encoding="utf-8").lower()
    assert "real-time view" not in marketing
    assert "approved · week" not in marketing
    assert "sample driver settlement" not in demo
    assert "fictional sample" in marketing
    assert "fictional sample data" in demo
