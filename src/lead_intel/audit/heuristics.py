"""Website quality heuristics.

Pure, configurable rules that decide whether a page looks mobile-friendly, slow,
or outdated. Each rule returns not just a verdict but the *reasons* behind it, so
the audit can explain itself to the sales team and the PDF report.

These are deliberately HTML-only heuristics (no headless browser). The audit
engine exposes an enricher seam (:mod:`lead_intel.audit.base`) so a Playwright or
PageSpeed probe can refine ``mobile_friendly``/``appears_slow`` later without
touching this module.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

_DEPRECATED_TAGS = ("font", "center", "marquee", "blink", "frameset", "frame")
_COPYRIGHT_YEAR_RE = re.compile(
    r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", re.IGNORECASE
)


def is_mobile_friendly(soup: BeautifulSoup) -> bool:
    """True when a responsive viewport meta tag is present.

    The ``width=device-width`` viewport tag is the single strongest HTML signal
    of a mobile-ready site; its absence almost always means a fixed-width layout.
    """
    meta = soup.find("meta", attrs={"name": "viewport"})
    if not meta:
        return False
    content = str(meta.get("content") or "").lower()
    return "width=device-width" in content or bool(content)


def is_slow(response_time_ms: int | None, threshold_ms: int) -> bool:
    """True when the measured response time exceeds the configured threshold."""
    return response_time_ms is not None and response_time_ms > threshold_ms


def outdated_signals(
    soup: BeautifulSoup,
    *,
    https: bool,
    current_year: int,
    stale_after_years: int,
) -> list[str]:
    """Collect human-readable reasons the site looks outdated.

    Args:
        soup: Parsed page.
        https: Whether the final URL was served over HTTPS.
        current_year: Reference year for copyright-staleness (injected for tests).
        stale_after_years: A copyright year older than this counts as stale.
    """
    reasons: list[str] = []

    if not soup.find("meta", attrs={"name": "viewport"}):
        reasons.append("No mobile viewport meta tag (not responsive)")

    if not https:
        reasons.append("Not served over HTTPS")

    found_deprecated = [tag for tag in _DEPRECATED_TAGS if soup.find(tag)]
    if found_deprecated:
        reasons.append(f"Uses deprecated HTML tags: {', '.join(found_deprecated)}")

    if _uses_flash(soup):
        reasons.append("Uses Flash content (unsupported by modern browsers)")

    if not _has_html5_doctype(soup):
        reasons.append("Missing modern HTML5 doctype")

    stale_year = _stale_copyright_year(soup, current_year, stale_after_years)
    if stale_year is not None:
        reasons.append(f"Stale copyright year ({stale_year})")

    return reasons


# -- helpers ---------------------------------------------------------------


def _uses_flash(soup: BeautifulSoup) -> bool:
    for embed in soup.find_all("embed", src=True):
        if str(embed["src"]).lower().endswith(".swf"):
            return True
    for obj in soup.find_all("object"):
        obj_type = str(obj.get("type") or "").lower()
        data = str(obj.get("data") or "").lower()
        if "flash" in obj_type or data.endswith(".swf"):
            return True
    return False


def _has_html5_doctype(soup: BeautifulSoup) -> bool:
    from bs4 import Doctype

    for item in soup.contents:
        if isinstance(item, Doctype):
            return item.strip().lower() == "html"
    return False


def _stale_copyright_year(
    soup: BeautifulSoup, current_year: int, stale_after_years: int
) -> int | None:
    text = soup.get_text(" ", strip=True)
    years = [int(m) for m in _COPYRIGHT_YEAR_RE.findall(text)]
    if not years:
        return None
    newest = max(years)
    if newest < current_year - stale_after_years:
        return newest
    return None
