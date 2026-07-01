"""Domain layer: pure, provider-agnostic business models and enumerations.

This package has no dependencies on infrastructure (network, files, vendors).
Everything else in the platform depends inward on it.
"""

from __future__ import annotations

from lead_intel.domain import enums
from lead_intel.domain.models import (
    AIContent,
    Business,
    BusinessContact,
    BusinessRatings,
    CRMTracking,
    FeaturePresence,
    GeoLocation,
    Lead,
    LeadScore,
    SalesRecommendation,
    TechnicalCheck,
    WebsiteAudit,
    WebsiteScore,
)

__all__ = [
    "enums",
    "AIContent",
    "Business",
    "BusinessContact",
    "BusinessRatings",
    "CRMTracking",
    "FeaturePresence",
    "GeoLocation",
    "Lead",
    "LeadScore",
    "SalesRecommendation",
    "TechnicalCheck",
    "WebsiteAudit",
    "WebsiteScore",
]
