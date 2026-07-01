"""Tests for the provider factory."""

from __future__ import annotations

import pytest

from lead_intel.config.settings import Settings
from lead_intel.core.exceptions import ConfigurationError
from lead_intel.domain.enums import DataProvider
from lead_intel.providers import GooglePlacesProvider, create_provider


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_creates_google_places_with_key() -> None:
    provider = create_provider(DataProvider.GOOGLE_PLACES, _settings(google_places_api_key="k"))
    assert isinstance(provider, GooglePlacesProvider)


def test_google_places_without_key_raises() -> None:
    with pytest.raises(ConfigurationError):
        create_provider(DataProvider.GOOGLE_PLACES, _settings(google_places_api_key=""))


def test_apify_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError):
        create_provider(DataProvider.APIFY_GMAPS, _settings(apify_api_token="t"))
