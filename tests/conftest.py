"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from lead_intel.domain.enums import DataProvider, Industry
from lead_intel.domain.models import Business, BusinessContact, BusinessRatings


@pytest.fixture()
def sample_business() -> Business:
    """A representative business with website, phone, Instagram, and reviews."""
    return Business(
        source=DataProvider.GOOGLE_PLACES,
        source_id="place_123",
        name="  FitZone Gym  ",
        industry=Industry.GYM,
        area="Koregaon Park",
        city="Pune",
        contact=BusinessContact(
            phone="+91 98765 43210",
            website="fitzonegym.in",
            instagram="https://instagram.com/fitzonegym",
        ),
        ratings=BusinessRatings(rating=4.7, review_count=240),
    )
