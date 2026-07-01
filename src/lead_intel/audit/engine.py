"""Website audit engine.

Orchestrates the audit of a single business: fetch → classify reachability →
detect features → apply heuristics → run enrichers, producing a
:class:`WebsiteAudit`. This is the core value of the platform — turning a raw URL
into concrete, explainable sales signals.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from lead_intel.audit.base import AuditContext, AuditEnricher
from lead_intel.audit.features import detect_features, parse_html
from lead_intel.audit.fetcher import FetchResult, PageFetcher
from lead_intel.audit.heuristics import is_mobile_friendly, is_slow, outdated_signals
from lead_intel.config.settings import AuditSettings, Settings
from lead_intel.core.logging import get_logger
from lead_intel.domain.enums import WebsiteStatus
from lead_intel.domain.models import Business, TechnicalCheck, WebsiteAudit

logger = get_logger("audit.engine")


class WebsiteAuditEngine:
    """Produces a :class:`WebsiteAudit` for a :class:`Business`."""

    def __init__(
        self,
        fetcher: PageFetcher,
        *,
        settings: AuditSettings,
        enrichers: tuple[AuditEnricher, ...] = (),
        current_year: int | None = None,
    ) -> None:
        """
        Args:
            fetcher: Injected page fetcher (mockable in tests).
            settings: Audit thresholds (slow response, outdated signal count, ...).
            enrichers: Optional post-heuristic refiners (Playwright/PageSpeed later).
            current_year: Reference year for staleness; defaults to the current UTC year.
        """
        self._fetcher = fetcher
        self._settings = settings
        self._enrichers = enrichers
        self._current_year = current_year or datetime.now(timezone.utc).year

    def audit(self, business: Business) -> WebsiteAudit:
        """Audit ``business``'s website, or return a NO_WEBSITE result."""
        website = business.contact.website
        if not website:
            return WebsiteAudit.no_website()

        fetch = self._fetcher.fetch(website)
        technical, status, problems = self._classify(business, fetch)
        audit = WebsiteAudit(
            status=status,
            final_url=fetch.final_url,
            technical=technical,
            problems=problems,
        )

        soup = None
        if technical.is_accessible and fetch.html:
            soup = self._analyze(fetch, audit)

        self._run_enrichers(audit, AuditContext(business=business, fetch=fetch, soup=soup))
        logger.info(
            "website audit complete",
            extra={
                "business": business.name,
                "status": str(audit.status),
                "quality": str(audit.quality),
                "problem_count": len(audit.problems),
            },
        )
        return audit

    # -- reachability classification ---------------------------------------

    def _classify(
        self, business: Business, fetch: FetchResult
    ) -> tuple[TechnicalCheck, WebsiteStatus, list[str]]:
        technical = TechnicalCheck(
            status_code=fetch.status_code,
            response_time_ms=fetch.response_time_ms,
            https_enabled=fetch.https,
            redirects=fetch.redirected,
            redirect_target=fetch.redirect_target,
        )
        problems: list[str] = []

        if not fetch.ok:
            if fetch.error_kind == "timeout":
                status = WebsiteStatus.INACCESSIBLE
                problems.append("Website timed out and could not be reached.")
            else:
                status = WebsiteStatus.BROKEN
                technical.is_broken = True
                problems.append("Website is broken or unreachable.")
            return technical, status, problems

        code = fetch.status_code or 0
        if code >= 400:
            technical.is_broken = True
            problems.append(f"Website returns an error (HTTP {code}).")
            return technical, WebsiteStatus.BROKEN, problems

        technical.is_accessible = True
        if fetch.redirected and not _same_site(business.contact.website, fetch.final_url):
            status = WebsiteStatus.REDIRECTED
            problems.append(f"Listed website redirects to a different site: {fetch.final_url}")
        else:
            status = WebsiteStatus.LIVE

        if not fetch.https:
            problems.append("Website is not served over HTTPS.")

        return technical, status, problems

    # -- content analysis --------------------------------------------------

    def _analyze(self, fetch: FetchResult, audit: WebsiteAudit) -> BeautifulSoup:
        assert fetch.html is not None
        soup = parse_html(fetch.html)

        audit.features = detect_features(soup)
        for missing in audit.features.missing_features():
            audit.problems.append(f"Missing: {missing}")

        audit.technical.mobile_friendly = is_mobile_friendly(soup)
        if audit.technical.mobile_friendly is False:
            audit.problems.append("Site does not appear mobile-friendly.")

        audit.technical.appears_slow = is_slow(
            fetch.response_time_ms, self._settings.slow_response_ms
        )
        if audit.technical.appears_slow:
            audit.problems.append(
                f"Site appears slow ({fetch.response_time_ms} ms to respond)."
            )

        reasons = outdated_signals(
            soup,
            https=fetch.https,
            current_year=self._current_year,
            stale_after_years=self._settings.stale_copyright_years,
        )
        audit.technical.is_outdated = len(reasons) >= self._settings.outdated_signal_threshold
        if audit.technical.is_outdated:
            audit.problems.extend(f"Outdated: {reason}" for reason in reasons)

        return soup

    def _run_enrichers(self, audit: WebsiteAudit, context: AuditContext) -> None:
        for enricher in self._enrichers:
            try:
                enricher.enrich(audit, context)
            except Exception:  # noqa: BLE001 - one enricher must not fail the audit
                logger.exception(
                    "audit enricher failed", extra={"enricher": type(enricher).__name__}
                )


def build_audit_engine(
    settings: Settings, *, enrichers: tuple[AuditEnricher, ...] = ()
) -> WebsiteAuditEngine:
    """Construct an engine (with its own :class:`PageFetcher`) from full settings."""
    fetcher = PageFetcher(timeout_seconds=settings.audit.request_timeout_seconds)
    return WebsiteAuditEngine(fetcher, settings=settings.audit, enrichers=enrichers)


def _same_site(original: str | None, final: str | None) -> bool:
    """True when two URLs share a registrable host (ignoring a leading ``www.``)."""
    if not original or not final:
        return True
    return _host(original) == _host(final)


def _host(url: str) -> str:
    netloc = urlsplit(url if "//" in url else f"//{url}").netloc.lower()
    netloc = netloc.split("@")[-1].split(":")[0]
    return netloc[4:] if netloc.startswith("www.") else netloc
