"""Tests for the Business domain model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lead_intel.domain.enums import DataProvider, Industry
from lead_intel.domain.models import Business, BusinessContact


def test_name_is_stripped(sample_business: Business) -> None:
    assert sample_business.name == "FitZone Gym"


def test_blank_name_rejected() -> None:
    with pytest.raises(ValidationError):
        Business(source=DataProvider.GOOGLE_PLACES, source_id="x", name="   ")


def test_website_gets_https_scheme() -> None:
    contact = BusinessContact(website="example.com")
    assert contact.website == "https://example.com"
    assert contact.has_website is True


def test_website_preserves_existing_scheme() -> None:
    assert BusinessContact(website="http://foo.com").website == "http://foo.com"


def test_empty_website_becomes_none() -> None:
    contact = BusinessContact(website="   ")
    assert contact.website is None
    assert contact.has_website is False


def test_dedup_key_is_provider_independent() -> None:
    a = Business(
        source=DataProvider.GOOGLE_PLACES,
        source_id="1",
        name="FitZone Gym!",
        area="Koregaon Park",
    )
    b = Business(
        source=DataProvider.APIFY_GMAPS,
        source_id="2",
        name="fitzone  gym",
        area="koregaon park",
    )
    assert a.dedup_key == b.dedup_key


def test_industry_label() -> None:
    assert Industry.DENTAL_CLINIC.label == "Dental Clinic"


def test_rating_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        Business(
            source=DataProvider.GOOGLE_PLACES,
            source_id="1",
            name="X",
            ratings={"rating": 6.0},
        )
