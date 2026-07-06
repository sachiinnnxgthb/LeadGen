"""Tests for the instant website mockup generator."""

from __future__ import annotations

from lead_intel.config.settings import Settings
from lead_intel.domain.enums import DataProvider, Industry
from lead_intel.domain.models import Business, BusinessContact, BusinessRatings, Lead
from lead_intel.mockup import build_mockup_html


def _lead(industry: Industry = Industry.GYM, *, name: str = "IronCore Gym") -> Lead:
    business = Business(
        source=DataProvider.GOOGLE_PLACES, source_id="1", name=name, industry=industry,
        area="Baner", city="Pune",
        contact=BusinessContact(phone="+91 98765 43210"),
        ratings=BusinessRatings(rating=4.8, review_count=210),
    )
    return Lead(business=business)


def _agency() -> object:
    return Settings(_env_file=None).agency  # type: ignore[call-arg]


def test_mockup_is_valid_html_with_business_details() -> None:
    html = build_mockup_html(_lead(), _agency())
    assert html.lstrip().startswith("<!doctype html>")
    assert "IronCore Gym" in html
    assert "Baner" in html
    assert "4.8" in html and "210" in html
    assert "wa.me/919876543210" in html  # WhatsApp CTA wired
    assert "tel:+91 98765 43210" in html or "tel:" in html


def test_mockup_is_category_specific() -> None:
    gym = build_mockup_html(_lead(Industry.GYM), _agency())
    cafe = build_mockup_html(_lead(Industry.CAFE, name="Brew Cafe"), _agency())
    assert "Expert Trainers" in gym
    assert "Freshly Brewed" in cafe


def test_mockup_uses_fallback_for_unmapped_category() -> None:
    html = build_mockup_html(_lead(Industry.PET_GROOMER, name="Paws"), _agency())
    assert "Trusted Service" in html  # fallback theme
    assert "Paws" in html


def test_mockup_credits_agency() -> None:
    html = build_mockup_html(_lead(), _agency())
    assert "crafted by" in html.lower()
    # escapes user content (no raw script injection via name)
    evil = build_mockup_html(_lead(name="<script>x</script>Gym"), _agency())
    assert "<script>x</script>Gym" not in evil
    assert "&lt;script&gt;" in evil
