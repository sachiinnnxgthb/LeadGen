"""Lead context for content generation.

A flat, serializable view of everything the prompts and templates need about a
lead. Building it once — tolerant of a partially-enriched lead — keeps prompt
templates and the deterministic fallback reading from the same variables, so the
two generation paths never drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lead_intel.config.settings import AgencySettings
from lead_intel.domain.enums import WebsiteQuality
from lead_intel.domain.models import Lead


@dataclass(frozen=True)
class LeadContext:
    """Immutable snapshot of a lead used to render outreach content."""

    business_name: str
    category: str
    area: str
    city: str

    rating: float | None
    review_count: int

    website_quality: WebsiteQuality
    problems: list[str] = field(default_factory=list)
    missing_features: list[str] = field(default_factory=list)

    website_score: float | None = None
    lead_score: float | None = None
    priority: str | None = None

    package_label: str | None = None
    package_price: int | None = None

    agency_name: str = ""
    agency_phone: str = ""
    agency_email: str = ""
    agency_website: str = ""

    @property
    def gap_phrase(self) -> str:
        """A short description of the prospect's core web problem."""
        return {
            WebsiteQuality.NONE: "your business doesn't have a website yet",
            WebsiteQuality.BROKEN: "your website appears to be broken or down",
            WebsiteQuality.OUTDATED: "your website looks a little dated",
            WebsiteQuality.MODERN: "there are a few things we could improve on your website",
        }[self.website_quality]

    @property
    def demand_phrase(self) -> str:
        """A short description of the prospect's public traction."""
        bits = []
        if self.rating is not None:
            bits.append(f"{self.rating}★")
        if self.review_count:
            bits.append(f"{self.review_count} reviews")
        return ", ".join(bits) if bits else "a great local reputation"


def build_context(lead: Lead, agency: AgencySettings) -> LeadContext:
    """Assemble a :class:`LeadContext` from a (possibly partial) lead + agency."""
    b = lead.business
    audit = lead.audit
    return LeadContext(
        business_name=b.name,
        category=b.industry.label,
        area=b.area or b.city or "your area",
        city=b.city or "",
        rating=b.ratings.rating,
        review_count=b.ratings.review_count,
        website_quality=lead.website_quality,
        problems=list(audit.problems[:5]) if audit else [],
        missing_features=audit.features.missing_features() if audit else [],
        website_score=lead.website_score.total if lead.website_score else None,
        lead_score=lead.lead_score.value if lead.lead_score else None,
        priority=lead.priority.value if lead.priority else None,
        package_label=lead.recommendation.package.label if lead.recommendation else None,
        package_price=lead.recommendation.price if lead.recommendation else None,
        agency_name=agency.name,
        agency_phone=agency.phone,
        agency_email=agency.email,
        agency_website=agency.website,
    )
