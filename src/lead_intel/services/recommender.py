"""Sales package recommendation.

Chooses one of Starter / Growth / Premium for a lead and explains why, grounding
the rationale in the concrete signals (website state + business demand) rather
than a bare label. Prices come from :class:`PackageSettings`.

Mapping rests on the lead's priority (itself derived from the configurable lead
score), so "which package" stays consistent with "how hot is this lead":
High → Premium, Medium → Growth, Low → Starter.
"""

from __future__ import annotations

from lead_intel.config.settings import PackageSettings
from lead_intel.domain.enums import LeadPriority, PackageTier, WebsiteQuality, WebsiteStatus
from lead_intel.domain.models import Business, LeadScore, SalesRecommendation, WebsiteAudit

_PRIORITY_TO_TIER = {
    LeadPriority.HIGH: PackageTier.PREMIUM,
    LeadPriority.MEDIUM: PackageTier.GROWTH,
    LeadPriority.LOW: PackageTier.STARTER,
}


class PackageRecommender:
    """Recommends a sales package with a signal-grounded rationale."""

    def __init__(self, packages: PackageSettings) -> None:
        self._packages = packages

    def recommend(
        self, business: Business, audit: WebsiteAudit, lead_score: LeadScore
    ) -> SalesRecommendation:
        tier = _PRIORITY_TO_TIER[lead_score.priority]
        price = self._packages.price_for(tier)
        rationale = self._rationale(business, audit, lead_score, tier, price)
        return SalesRecommendation(package=tier, price=price, rationale=rationale)

    def _rationale(
        self,
        business: Business,
        audit: WebsiteAudit,
        lead_score: LeadScore,
        tier: PackageTier,
        price: int,
    ) -> str:
        need = self._need_phrase(audit)
        demand = self._demand_phrase(business)
        return (
            f"{need} {demand} "
            f"Lead score {lead_score.value:g}/10 ({lead_score.priority.value}) → "
            f"{tier.label} package (₹{price:,})."
        )

    @staticmethod
    def _need_phrase(audit: WebsiteAudit) -> str:
        if audit.status == WebsiteStatus.NO_WEBSITE:
            return "Business has no website — a full build captures demand it is currently losing."
        if audit.quality == WebsiteQuality.BROKEN:
            return "Existing website is broken — an urgent rebuild is needed to stop losing sales."
        if audit.quality == WebsiteQuality.OUTDATED:
            return "Website is outdated — a modern redesign will lift trust and conversions."
        return "Website works but has gaps that a refresh can close."

    @staticmethod
    def _demand_phrase(business: Business) -> str:
        bits = []
        rating = business.ratings.rating
        if rating is not None:
            bits.append(f"{rating}★ rating")
        if business.ratings.review_count:
            bits.append(f"{business.ratings.review_count} reviews")
        if not bits:
            return "Limited public demand signals available."
        return f"Strong local demand ({', '.join(bits)})."
