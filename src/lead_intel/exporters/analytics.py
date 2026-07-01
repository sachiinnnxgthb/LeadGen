"""Dashboard analytics.

Computes the aggregate metrics shown on the Dashboard sheet and used by the
Streamlit UI. Pure computation over a list of leads plus revenue assumptions —
no I/O, fully unit-testable.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from lead_intel.config.settings import RevenueSettings
from lead_intel.domain.enums import LeadPriority, WebsiteQuality, WebsiteStatus
from lead_intel.domain.models import Lead


@dataclass(frozen=True)
class DashboardStats:
    """Aggregate analytics across a batch of leads."""

    total_businesses: int
    without_website: int
    broken_websites: int
    outdated_websites: int
    modern_websites: int
    high_priority: int
    average_rating: float
    average_website_score: float
    category_distribution: dict[str, int] = field(default_factory=dict)
    area_distribution: dict[str, int] = field(default_factory=dict)
    potential_monthly_revenue: float = 0.0

    def as_kpi_pairs(self) -> list[tuple[str, object]]:
        """Ordered (label, value) pairs for rendering a KPI panel."""
        return [
            ("Total Businesses", self.total_businesses),
            ("Without Website", self.without_website),
            ("Broken Websites", self.broken_websites),
            ("Outdated Websites", self.outdated_websites),
            ("Modern Websites", self.modern_websites),
            ("High Priority Leads", self.high_priority),
            ("Average Rating", round(self.average_rating, 2)),
            ("Average Website Score", round(self.average_website_score, 1)),
            ("Potential Monthly Revenue (₹)", round(self.potential_monthly_revenue)),
        ]


def compute_dashboard(leads: list[Lead], revenue: RevenueSettings) -> DashboardStats:
    """Aggregate ``leads`` into :class:`DashboardStats`."""
    total = len(leads)

    without = sum(1 for lead in leads if lead.website_status == WebsiteStatus.NO_WEBSITE)
    broken = sum(1 for lead in leads if lead.website_quality == WebsiteQuality.BROKEN)
    outdated = sum(1 for lead in leads if lead.website_quality == WebsiteQuality.OUTDATED)
    modern = sum(1 for lead in leads if lead.website_quality == WebsiteQuality.MODERN)
    high = sum(1 for lead in leads if lead.priority == LeadPriority.HIGH)

    ratings = [
        lead.business.ratings.rating
        for lead in leads
        if lead.business.ratings.rating is not None
    ]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

    scores = [lead.website_score.total for lead in leads if lead.website_score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    categories = Counter(lead.business.industry.label for lead in leads)
    areas = Counter(lead.business.area or "Unknown" for lead in leads)

    revenue_potential = total * revenue.conversion_rate * revenue.avg_deal_value

    return DashboardStats(
        total_businesses=total,
        without_website=without,
        broken_websites=broken,
        outdated_websites=outdated,
        modern_websites=modern,
        high_priority=high,
        average_rating=avg_rating,
        average_website_score=avg_score,
        category_distribution=dict(categories.most_common()),
        area_distribution=dict(areas.most_common()),
        potential_monthly_revenue=revenue_potential,
    )
