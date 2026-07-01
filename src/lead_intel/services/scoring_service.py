"""Scoring facade.

Composes the website scorer, lead scorer, and package recommender behind one
entry point. Callers hand in a :class:`Business` + :class:`WebsiteAudit` (or a
partially-built :class:`Lead`) and get back a fully scored result.
"""

from __future__ import annotations

from dataclasses import dataclass

from lead_intel.config.settings import Settings
from lead_intel.core.exceptions import LeadIntelError
from lead_intel.domain.models import (
    Business,
    Lead,
    LeadScore,
    SalesRecommendation,
    WebsiteAudit,
    WebsiteScore,
)
from lead_intel.services.lead_scorer import LeadScorer
from lead_intel.services.recommender import PackageRecommender
from lead_intel.services.website_scorer import WebsiteScorer


@dataclass(frozen=True)
class ScoringResult:
    """Bundle of everything the scoring stage produces for a business."""

    website_score: WebsiteScore
    lead_score: LeadScore
    recommendation: SalesRecommendation


class ScoringService:
    """One-call scoring of a business + audit into scores and a recommendation."""

    def __init__(self, settings: Settings) -> None:
        self._website_scorer = WebsiteScorer(settings.website_score)
        self._lead_scorer = LeadScorer(settings.lead_score)
        self._recommender = PackageRecommender(settings.package)

    def score(self, business: Business, audit: WebsiteAudit) -> ScoringResult:
        """Compute website score, lead score, and package recommendation."""
        website_score = self._website_scorer.score(audit)
        lead_score = self._lead_scorer.score(business, audit)
        recommendation = self._recommender.recommend(business, audit, lead_score)
        return ScoringResult(
            website_score=website_score,
            lead_score=lead_score,
            recommendation=recommendation,
        )

    def enrich(self, lead: Lead) -> Lead:
        """Populate a lead's score fields in place and return it.

        Raises:
            LeadIntelError: the lead has not been audited yet.
        """
        if lead.audit is None:
            raise LeadIntelError("Lead must be audited before scoring.")
        result = self.score(lead.business, lead.audit)
        lead.website_score = result.website_score
        lead.lead_score = result.lead_score
        lead.recommendation = result.recommendation
        return lead
