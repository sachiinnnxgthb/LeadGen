"""Tests for the screenshot fetcher and proposal PDF exporter."""

from __future__ import annotations

from pathlib import Path

import httpx

from lead_intel.config.settings import Settings
from lead_intel.domain.models import Lead
from lead_intel.exporters.proposal_exporter import ProposalExporter
from lead_intel.exporters.screenshot import fetch_screenshot, screenshot_url

# A minimal valid 1x1 PNG, repeated to exceed the min-size threshold.
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
) + b"\x00" * 4000


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


# -- screenshot ------------------------------------------------------------


def test_screenshot_url_encodes_target() -> None:
    url = screenshot_url("https://example.com/a b")
    assert url.startswith("https://s.wordpress.com/mshots/v1/")
    assert "https%3A%2F%2Fexample.com" in url


def test_fetch_screenshot_returns_image_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_PNG, headers={"content-type": "image/png"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = fetch_screenshot("https://example.com", client=client)
    assert result is not None and result.startswith(b"\x89PNG")


def test_fetch_screenshot_none_for_empty_url() -> None:
    assert fetch_screenshot(None) is None
    assert fetch_screenshot("") is None


def test_fetch_screenshot_none_on_placeholder_or_error() -> None:
    def tiny(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"tiny", headers={"content-type": "image/png"})

    client = httpx.Client(transport=httpx.MockTransport(tiny))
    assert fetch_screenshot("https://example.com", client=client) is None  # too small

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client2 = httpx.Client(transport=httpx.MockTransport(boom))
    assert fetch_screenshot("https://example.com", client=client2) is None


# -- proposal --------------------------------------------------------------


def _lead() -> Lead:
    from lead_intel.domain.enums import DataProvider, Industry, LeadPriority, PackageTier
    from lead_intel.domain.models import (
        Business,
        BusinessContact,
        BusinessRatings,
        LeadScore,
        SalesRecommendation,
        WebsiteAudit,
    )

    business = Business(
        source=DataProvider.GOOGLE_PLACES, source_id="1", name="IronCore Gym",
        industry=Industry.GYM, area="Baner", city="Pune",
        contact=BusinessContact(phone="+91 90000 00000"),
        ratings=BusinessRatings(rating=4.8, review_count=200),
    )
    return Lead(
        business=business, audit=WebsiteAudit.no_website(),
        lead_score=LeadScore(value=9.0, priority=LeadPriority.HIGH),
        recommendation=SalesRecommendation(package=PackageTier.PREMIUM, price=14999, rationale="x"),
    )


def test_proposal_bytes_are_valid_pdf() -> None:
    data = ProposalExporter(_settings().agency, _settings().package).to_bytes(_lead())
    assert data.startswith(b"%PDF")
    assert len(data) > 1500


def test_proposal_embeds_screenshot_without_error() -> None:
    data = ProposalExporter(_settings().agency).to_bytes(_lead(), screenshot=_PNG)
    assert data.startswith(b"%PDF")


def test_proposal_to_file(tmp_path: Path) -> None:
    path = ProposalExporter(_settings().agency).export(_lead(), tmp_path / "proposal.pdf")
    assert path.exists() and path.read_bytes().startswith(b"%PDF")
