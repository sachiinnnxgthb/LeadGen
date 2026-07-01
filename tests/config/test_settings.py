"""Tests for the configuration layer."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lead_intel.config.settings import (
    LeadScoreSettings,
    PackageSettings,
    Settings,
    WebsiteScoreSettings,
)
from lead_intel.domain.enums import PackageTier, ScoreDimension


def test_defaults_load_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure a stray .env in CWD can't influence the defaults under test.
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.search.city == "Pune"
    assert settings.package.premium_price == 14999
    assert settings.lead_score.no_website == 4


def test_website_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        WebsiteScoreSettings(performance=0.5, mobile=0.5, trust=0.5, seo=0.5, user_experience=0.5)


def test_website_weights_dimension_map() -> None:
    weights = WebsiteScoreSettings().as_dimension_map()
    assert set(weights) == set(ScoreDimension)
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_priority_thresholds_validated() -> None:
    with pytest.raises(ValidationError):
        LeadScoreSettings(high_priority_min=4, medium_priority_min=7)


def test_package_price_lookup() -> None:
    packages = PackageSettings()
    assert packages.price_for(PackageTier.STARTER) == 4999
    assert packages.price_for(PackageTier.GROWTH) == 8999
    assert packages.price_for(PackageTier.PREMIUM) == 14999


def test_nested_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEAD_SCORE__NO_WEBSITE", "9")
    monkeypatch.setenv("SEARCH__CITY", "Mumbai")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.lead_score.no_website == 9
    assert settings.search.city == "Mumbai"


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level="VERBOSE")  # type: ignore[call-arg]
