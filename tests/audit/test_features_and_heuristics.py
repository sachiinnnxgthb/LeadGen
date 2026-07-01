"""Tests for HTML feature detection and quality heuristics."""

from __future__ import annotations

from lead_intel.audit.features import detect_features, parse_html
from lead_intel.audit.heuristics import is_mobile_friendly, is_slow, outdated_signals

RICH_PAGE = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Modern Clinic</title>
</head>
<body>
  <a href="https://wa.me/919876543210">WhatsApp us</a>
  <a href="https://instagram.com/clinic">Instagram</a>
  <a href="tel:+919876543210">Call now</a>
  <a href="/privacy">Privacy Policy</a>
  <a href="/terms">Terms &amp; Conditions</a>
  <a href="/contact">Enquiry</a>
  <form action="/submit"><input name="email"><textarea></textarea></form>
  <iframe src="https://www.google.com/maps/embed?pb=xyz"></iframe>
  <section class="testimonials">What our clients say</section>
  <div class="gallery">Gallery</div>
  <section id="faq">Frequently asked questions</section>
  <p>&copy; 2025 Modern Clinic</p>
</body>
</html>
"""

BARE_PAGE = """
<html><head><title>Old Site</title></head>
<body>
  <font size="3">Welcome</font>
  <center>Est. 1999</center>
  <p>Copyright 2010 Old Traders</p>
</body></html>
"""


def test_detects_all_rich_features() -> None:
    features = detect_features(parse_html(RICH_PAGE))
    assert features.has_contact_form is True
    assert features.has_whatsapp is True
    assert features.has_maps_embed is True
    assert features.has_social_links is True
    assert features.has_testimonials is True
    assert features.has_gallery is True
    assert features.has_faq is True
    assert features.has_privacy_policy is True
    assert features.has_terms is True
    assert features.has_enquiry_button is True
    assert features.has_cta is True
    assert features.missing_features() == []


def test_bare_page_reports_missing_features() -> None:
    features = detect_features(parse_html(BARE_PAGE))
    missing = features.missing_features()
    assert "Contact form" in missing
    assert "WhatsApp link" in missing
    assert "Privacy Policy" in missing
    assert features.has_whatsapp is False


def test_mobile_friendly_detection() -> None:
    assert is_mobile_friendly(parse_html(RICH_PAGE)) is True
    assert is_mobile_friendly(parse_html(BARE_PAGE)) is False


def test_slow_detection() -> None:
    assert is_slow(3500, 3000) is True
    assert is_slow(1200, 3000) is False
    assert is_slow(None, 3000) is False


def test_modern_page_has_no_outdated_signals() -> None:
    reasons = outdated_signals(
        parse_html(RICH_PAGE), https=True, current_year=2026, stale_after_years=3
    )
    assert reasons == []


def test_old_page_accumulates_outdated_signals() -> None:
    reasons = outdated_signals(
        parse_html(BARE_PAGE), https=False, current_year=2026, stale_after_years=3
    )
    joined = " ".join(reasons).lower()
    assert "viewport" in joined
    assert "https" in joined
    assert "deprecated" in joined
    assert "2010" in joined
    assert len(reasons) >= 2
