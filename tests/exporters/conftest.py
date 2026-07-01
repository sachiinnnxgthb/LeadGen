"""Shared fixtures for exporter tests: a varied batch of enriched leads."""

from __future__ import annotations

import pytest

from lead_intel.domain.enums import (
    DataProvider,
    Industry,
    LeadPriority,
    PackageTier,
    ScoreDimension,
    WebsiteStatus,
)
from lead_intel.domain.models import (
    AIContent,
    Business,
    BusinessContact,
    BusinessRatings,
    FeaturePresence,
    Lead,
    LeadScore,
    SalesRecommendation,
    TechnicalCheck,
    WebsiteAudit,
    WebsiteScore,
)


def _ai() -> AIContent:
    return AIContent(
        whatsapp_message="Hi there!",
        email="Subject: Hello\n\nBody",
        cold_call_script="Opener...",
        follow_ups=["f1", "f2", "f3"],
        objection_handling="obj",
        portfolio_response="port",
        timeline_response="time",
        why_choose_us="why",
    )


def _scored_lead(
    name: str,
    industry: Industry,
    area: str,
    *,
    audit: WebsiteAudit,
    website_total: float,
    lead_value: float,
    priority: LeadPriority,
    package: PackageTier,
    rating: float | None = 4.6,
    reviews: int = 150,
    website: str | None = None,
    instagram: str | None = None,
) -> Lead:
    business = Business(
        source=DataProvider.GOOGLE_PLACES,
        source_id=name,
        name=name,
        industry=industry,
        area=area,
        city="Pune",
        address=f"{area}, Pune",
        contact=BusinessContact(phone="+91 90000 00000", website=website, instagram=instagram),
        ratings=BusinessRatings(rating=rating, review_count=reviews),
    )
    return Lead(
        business=business,
        audit=audit,
        website_score=WebsiteScore(
            total=website_total,
            subscores={dim: website_total for dim in ScoreDimension},
            explanations={dim: "reason" for dim in ScoreDimension},
        ),
        lead_score=LeadScore(value=lead_value, priority=priority),
        recommendation=SalesRecommendation(package=package, price=14999, rationale="because"),
        ai_content=_ai(),
    )


@pytest.fixture()
def leads() -> list[Lead]:
    modern_audit = WebsiteAudit(
        status=WebsiteStatus.LIVE,
        technical=TechnicalCheck(is_accessible=True, https_enabled=True, mobile_friendly=True,
                                 is_outdated=False),
        features=FeaturePresence(has_contact_form=True, has_whatsapp=True),
    )
    outdated_audit = WebsiteAudit(
        status=WebsiteStatus.LIVE,
        technical=TechnicalCheck(is_accessible=True, https_enabled=False, mobile_friendly=False,
                                 is_outdated=True),
        features=FeaturePresence(has_contact_form=False, has_whatsapp=False),
        problems=["Outdated: no viewport", "Missing: WhatsApp link"],
    )
    broken_audit = WebsiteAudit(status=WebsiteStatus.BROKEN,
                                technical=TechnicalCheck(is_broken=True),
                                problems=["Website is broken."])

    return [
        _scored_lead("IronCore Gym", Industry.GYM, "Baner", audit=WebsiteAudit.no_website(),
                     website_total=0, lead_value=10, priority=LeadPriority.HIGH,
                     package=PackageTier.PREMIUM, rating=4.9, reviews=320,
                     instagram="https://instagram.com/ironcore"),
        _scored_lead("Old Cafe", Industry.CAFE, "Kothrud", audit=outdated_audit,
                     website_total=35, lead_value=6, priority=LeadPriority.MEDIUM,
                     package=PackageTier.GROWTH, website="http://oldcafe.example"),
        _scored_lead("Broken Salon", Industry.SALON, "Baner", audit=broken_audit,
                     website_total=10, lead_value=7, priority=LeadPriority.HIGH,
                     package=PackageTier.PREMIUM, website="https://brokensalon.example"),
        _scored_lead("Shiny Dental", Industry.DENTAL_CLINIC, "Viman Nagar", audit=modern_audit,
                     website_total=88, lead_value=3, priority=LeadPriority.LOW,
                     package=PackageTier.STARTER, website="https://shinydental.example",
                     instagram="https://instagram.com/shiny"),
    ]
