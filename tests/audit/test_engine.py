"""End-to-end tests for the website audit engine."""

from __future__ import annotations

import httpx

from lead_intel.audit.base import AuditContext
from lead_intel.audit.engine import WebsiteAuditEngine
from lead_intel.audit.fetcher import PageFetcher
from lead_intel.config.settings import AuditSettings
from lead_intel.domain.enums import DataProvider, Industry, WebsiteQuality, WebsiteStatus
from lead_intel.domain.models import Business, BusinessContact, WebsiteAudit

MODERN_HTML = """
<!doctype html>
<html><head><meta name="viewport" content="width=device-width"></head>
<body>
  <form><input name="e"></form>
  <a href="https://wa.me/91">wa</a>
  <a href="https://instagram.com/x">ig</a>
  <a href="/privacy">privacy</a><a href="/terms">terms</a>
  <a href="/contact">Enquiry</a>
  <iframe src="https://google.com/maps/embed"></iframe>
  <div class="testimonials gallery">reviews</div>
  <div id="faq">faq</div>
  <a href="tel:1">Book now</a>
  <p>&copy; 2026</p>
</body></html>
"""

OLD_HTML = "<html><body><font>old</font><center>c</center><p>Copyright 2009</p></body></html>"


def _business(url: str | None = "https://example.com") -> Business:
    return Business(
        source=DataProvider.GOOGLE_PLACES,
        source_id="1",
        name="Test Biz",
        industry=Industry.CLINIC,
        contact=BusinessContact(website=url),
    )


def _static_client(html: str) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, html=html)))


def _engine(
    handler: httpx.MockTransport, *, times: list[float] | None = None, **kw: object
) -> WebsiteAuditEngine:
    clock_iter = iter(times) if times else None
    fetcher = PageFetcher(
        client=httpx.Client(transport=handler, follow_redirects=True),
        clock=(lambda: next(clock_iter)) if clock_iter else (lambda: 0.0),
    )
    settings = AuditSettings(**kw)  # type: ignore[arg-type]
    return WebsiteAuditEngine(fetcher, settings=settings, current_year=2026)


def test_no_website_short_circuits() -> None:
    engine = _engine(httpx.MockTransport(lambda r: httpx.Response(200)))
    audit = engine.audit(_business(url=None))
    assert audit.status == WebsiteStatus.NO_WEBSITE
    assert audit.quality == WebsiteQuality.NONE


def test_modern_site_is_live_and_full_featured() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=MODERN_HTML)

    audit = _engine(httpx.MockTransport(handler)).audit(_business())
    assert audit.status == WebsiteStatus.LIVE
    assert audit.technical.is_accessible is True
    assert audit.technical.mobile_friendly is True
    assert audit.technical.is_outdated is False
    assert audit.quality == WebsiteQuality.MODERN
    assert audit.features.missing_features() == []


def test_broken_site_flagged() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, html="down")

    audit = _engine(httpx.MockTransport(handler)).audit(_business())
    assert audit.status == WebsiteStatus.BROKEN
    assert audit.technical.is_broken is True
    assert audit.quality == WebsiteQuality.BROKEN


def test_connection_failure_is_broken() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    audit = _engine(httpx.MockTransport(handler)).audit(_business())
    assert audit.status == WebsiteStatus.BROKEN


def test_timeout_is_inaccessible() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow")

    audit = _engine(httpx.MockTransport(handler)).audit(_business())
    assert audit.status == WebsiteStatus.INACCESSIBLE
    assert audit.quality == WebsiteQuality.BROKEN


def test_redirect_to_other_domain_flagged() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(301, headers={"Location": "https://parked-domain.com/"})
        return httpx.Response(200, html=MODERN_HTML)

    audit = _engine(httpx.MockTransport(handler)).audit(_business())
    assert audit.status == WebsiteStatus.REDIRECTED
    assert any("redirects" in p.lower() for p in audit.problems)


def test_www_redirect_stays_live() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(301, headers={"Location": "https://www.example.com/"})
        return httpx.Response(200, html=MODERN_HTML)

    audit = _engine(httpx.MockTransport(handler)).audit(_business())
    assert audit.status == WebsiteStatus.LIVE  # same registrable host


def test_outdated_site_detected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=OLD_HTML)

    audit = _engine(httpx.MockTransport(handler)).audit(_business(url="http://example.com"))
    assert audit.technical.is_outdated is True
    assert audit.quality == WebsiteQuality.OUTDATED
    assert any(p.startswith("Outdated:") for p in audit.problems)


def test_slow_site_flagged_via_clock() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=MODERN_HTML)

    # start=0.0, end=5.0 -> 5000 ms > default 3000 ms threshold
    audit = _engine(httpx.MockTransport(handler), times=[0.0, 5.0]).audit(_business())
    assert audit.technical.appears_slow is True
    assert any("slow" in p.lower() for p in audit.problems)


def test_enricher_is_invoked_and_can_refine() -> None:
    class ForceMobileFalse:
        def enrich(self, audit: WebsiteAudit, context: AuditContext) -> None:
            audit.technical.mobile_friendly = False
            audit.problems.append("enricher ran")

    fetcher = PageFetcher(client=_static_client(MODERN_HTML), clock=lambda: 0.0)
    engine = WebsiteAuditEngine(
        fetcher, settings=AuditSettings(), enrichers=(ForceMobileFalse(),), current_year=2026
    )
    audit = engine.audit(_business())
    assert audit.technical.mobile_friendly is False
    assert "enricher ran" in audit.problems


def test_failing_enricher_does_not_break_audit() -> None:
    class Boom:
        def enrich(self, audit: WebsiteAudit, context: AuditContext) -> None:
            raise RuntimeError("boom")

    fetcher = PageFetcher(client=_static_client(MODERN_HTML), clock=lambda: 0.0)
    engine = WebsiteAuditEngine(
        fetcher, settings=AuditSettings(), enrichers=(Boom(),), current_year=2026
    )
    audit = engine.audit(_business())
    assert audit.status == WebsiteStatus.LIVE  # audit still completes
