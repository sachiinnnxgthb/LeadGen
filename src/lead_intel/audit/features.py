"""HTML feature detection.

Pure functions that inspect a parsed page and decide which conversion/trust
elements are present. Each returned flag is a concrete ``True``/``False`` — the
audit only ever reports a feature "missing" when it genuinely checked and did not
find it, which keeps the sales talking points honest.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from lead_intel.domain.models import FeaturePresence

# Keyword sets driving link/text based detection. Lower-cased comparisons.
_ENQUIRY_TERMS = (
    "enquiry", "inquiry", "get a quote", "get quote", "request a quote", "request quote",
)
_CTA_TERMS = (
    "book now", "call now", "contact us", "get started", "sign up", "buy now",
    "order now", "get a quote", "book appointment", "schedule", "book a", "enquire now",
)
_SOCIAL_HOSTS = (
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com", "t.me",
)


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML with the stdlib parser (no lxml dependency required)."""
    return BeautifulSoup(html, "html.parser")


def detect_features(soup: BeautifulSoup) -> FeaturePresence:
    """Return a fully-determined :class:`FeaturePresence` for the page."""
    links = _links(soup)
    text = soup.get_text(" ", strip=True).lower()
    markup = str(soup).lower()

    has_contact_form = _has_real_form(soup)
    has_whatsapp = any("wa.me" in href or "whatsapp" in href for href, _ in links)
    has_tel = any(href.startswith("tel:") for href, _ in links)

    return FeaturePresence(
        has_contact_form=has_contact_form,
        has_enquiry_button=_any_term(links, _ENQUIRY_TERMS),
        has_whatsapp=has_whatsapp,
        has_maps_embed=_has_maps_embed(soup),
        has_social_links=any(host in href for href, _ in links for host in _SOCIAL_HOSTS),
        has_testimonials="testimonial" in markup or "what our clients" in text,
        has_gallery="gallery" in markup or len(soup.find_all("img")) >= 8,
        has_faq="faq" in markup or "frequently asked" in text,
        has_privacy_policy=_any_link_matches(links, "privacy"),
        has_terms=_any_link_matches(links, "terms"),
        has_cta=has_contact_form or has_tel or _any_term(links, _CTA_TERMS),
    )


# -- helpers ---------------------------------------------------------------


def _links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """All anchors as ``(href_lower, text_lower)`` pairs."""
    pairs: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        pairs.append((str(a["href"]).strip().lower(), a.get_text(" ", strip=True).lower()))
    return pairs


def _has_real_form(soup: BeautifulSoup) -> bool:
    """A form counts only if it has at least one input/textarea (not a search box only)."""
    return any(form.find(["input", "textarea", "select"]) for form in soup.find_all("form"))


def _has_maps_embed(soup: BeautifulSoup) -> bool:
    for iframe in soup.find_all("iframe", src=True):
        src = str(iframe["src"]).lower()
        if "google.com/maps" in src or "maps.google" in src or "maps.app" in src:
            return True
    return False


def _any_term(links: list[tuple[str, str]], terms: tuple[str, ...]) -> bool:
    return any(any(term in text for term in terms) for _, text in links)


def _any_link_matches(links: list[tuple[str, str]], needle: str) -> bool:
    return any(needle in href or needle in text for href, text in links)
