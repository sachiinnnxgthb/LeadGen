"""Tests for the scoring services (website score, lead score, recommendation)."""

from __future__ import annotations

import pytest

from lead_intel.config.settings import Settings
from lead_intel.core.exceptions import LeadIntelError
from lead_intel.domain.enums import (
    DataProvider,
    Industry,
    LeadPriority,
    PackageTier,
    ScoreDimension,
    WebsiteStatus,
)
from lead_intel.domain.models import (
    Business,
    BusinessContact,
    BusinessRatings,
    FeaturePresence,
    Lead,
    TechnicalCheck,
    WebsiteAudit,
)
from lead_intel.services import LeadScorer, PackageRecommender, WebsiteScorer
from lead_intel.services.scoring_service import ScoringService


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def _business(*, rating: float | None = 4.8, reviews: int = 250, instagram: bool = True,
              phone: bool = True) -> Business:
    return Business(
        source=DataProvider.GOOGLE_PLACES,
        source_id="1",
        name="Test Biz",
        industry=Industry.GYM,
        contact=BusinessContact(
            phone="123" if phone else None,
            instagram="https://instagram.com/x" if instagram else None,
        ),
        ratings=BusinessRatings(rating=rating, review_count=reviews),
    )


def _modern_audit() -> WebsiteAudit:
    return WebsiteAudit(
        status=WebsiteStatus.LIVE,
        technical=TechnicalCheck(
            is_accessible=True, https_enabled=True, mobile_friendly=True,
            appears_slow=False, is_outdated=False, response_time_ms=500,
        ),
        features=FeaturePresence(
            has_contact_form=True, has_enquiry_button=True, has_whatsapp=True,
            has_maps_embed=True, has_social_links=True, has_testimonials=True,
            has_gallery=True, has_faq=True, has_privacy_policy=True, has_terms=True,
            has_cta=True,
        ),
    )


def _outdated_audit() -> WebsiteAudit:
    return WebsiteAudit(
        status=WebsiteStatus.LIVE,
        technical=TechnicalCheck(
            is_accessible=True, https_enabled=False, mobile_friendly=False,
            appears_slow=True, is_outdated=True, response_time_ms=4200,
        ),
        features=FeaturePresence(
            has_contact_form=False, has_enquiry_button=False, has_whatsapp=False,
            has_maps_embed=False, has_social_links=False, has_testimonials=False,
            has_gallery=False, has_faq=False, has_privacy_policy=False, has_terms=False,
            has_cta=False,
        ),
    )


# -- WebsiteScorer ---------------------------------------------------------


def test_modern_site_scores_high() -> None:
    score = WebsiteScorer(_settings().website_score).score(_modern_audit())
    assert score.total >= 85
    assert set(score.subscores) == set(ScoreDimension)
    assert all(0 <= v <= 100 for v in score.subscores.values())
    assert all(score.explanations[d] for d in ScoreDimension)


def test_no_website_scores_zero() -> None:
    score = WebsiteScorer(_settings().website_score).score(WebsiteAudit.no_website())
    assert score.total == 0.0
    assert all(v == 0.0 for v in score.subscores.values())


def test_outdated_site_scores_low() -> None:
    score = WebsiteScorer(_settings().website_score).score(_outdated_audit())
    assert score.total < 40
    assert score.subscores[ScoreDimension.MOBILE] == 25.0


def test_broken_site_performance_zero() -> None:
    audit = WebsiteAudit(status=WebsiteStatus.BROKEN, technical=TechnicalCheck(is_broken=True))
    score = WebsiteScorer(_settings().website_score).score(audit)
    assert score.subscores[ScoreDimension.PERFORMANCE] == 0.0


# -- LeadScorer ------------------------------------------------------------


def test_no_website_high_value_scores_max() -> None:
    scorer = LeadScorer(_settings().lead_score)
    result = scorer.score(_business(), WebsiteAudit.no_website())
    # 4 (no site) + 2 (rating) + 2 (reviews) + 1 (insta) + 1 (phone) = 10
    assert result.value == 10.0
    assert result.priority == LeadPriority.HIGH
    assert len(result.breakdown) == 5


def test_website_state_contributions_are_mutually_exclusive() -> None:
    scorer = LeadScorer(_settings().lead_score)
    result = scorer.score(_business(instagram=False, phone=False), _outdated_audit())
    reasons = " ".join(c.reason for c in result.breakdown)
    assert "outdated" in reasons.lower()
    assert "no website" not in reasons.lower()
    assert "broken" not in reasons.lower()


def test_low_value_modern_site_is_low_priority() -> None:
    scorer = LeadScorer(_settings().lead_score)
    biz = _business(rating=3.5, reviews=10, instagram=False, phone=False)
    result = scorer.score(biz, _modern_audit())
    assert result.value == 0.0
    assert result.priority == LeadPriority.LOW


def test_score_is_capped_at_ten() -> None:
    scorer = LeadScorer(_settings().lead_score)
    result = scorer.score(_business(), WebsiteAudit.no_website())
    assert result.value <= 10.0


def test_priority_thresholds_respected() -> None:
    scorer = LeadScorer(_settings().lead_score)
    # rating(2) + reviews(2) = 4 -> Medium (default medium_min=4)
    biz = _business(rating=4.9, reviews=200, instagram=False, phone=False)
    result = scorer.score(biz, _modern_audit())
    assert result.value == 4.0
    assert result.priority == LeadPriority.MEDIUM


# -- Recommender -----------------------------------------------------------


def test_high_priority_gets_premium() -> None:
    settings = _settings()
    scorer = LeadScorer(settings.lead_score)
    rec = PackageRecommender(settings.package)
    lead_score = scorer.score(_business(), WebsiteAudit.no_website())
    result = rec.recommend(_business(), WebsiteAudit.no_website(), lead_score)
    assert result.package == PackageTier.PREMIUM
    assert result.price == 14999
    assert "no website" in result.rationale.lower()


def test_low_priority_gets_starter() -> None:
    settings = _settings()
    scorer = LeadScorer(settings.lead_score)
    rec = PackageRecommender(settings.package)
    biz = _business(rating=3.0, reviews=5, instagram=False, phone=False)
    lead_score = scorer.score(biz, _modern_audit())
    result = rec.recommend(biz, _modern_audit(), lead_score)
    assert result.package == PackageTier.STARTER
    assert result.price == 4999


# -- ScoringService facade -------------------------------------------------


def test_service_scores_end_to_end() -> None:
    service = ScoringService(_settings())
    result = service.score(_business(), _outdated_audit())
    assert 0 <= result.website_score.total <= 100
    assert result.lead_score.priority in set(LeadPriority)
    assert result.recommendation.price > 0


def test_enrich_populates_lead() -> None:
    service = ScoringService(_settings())
    lead = Lead(business=_business(), audit=_modern_audit())
    enriched = service.enrich(lead)
    assert enriched.website_score is not None
    assert enriched.lead_score is not None
    assert enriched.recommendation is not None


def test_enrich_without_audit_raises() -> None:
    service = ScoringService(_settings())
    with pytest.raises(LeadIntelError):
        service.enrich(Lead(business=_business()))
