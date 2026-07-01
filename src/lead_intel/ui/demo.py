"""Sample data for exploring the UI without live API keys.

Produces a small, realistic batch of Pune leads spanning every website state
(none / broken / outdated / modern) and priority level, fully scored and
content-enriched via the real services so the UI looks exactly as it would with
live data.
"""

from __future__ import annotations

from lead_intel.ai.factory import create_ai_service
from lead_intel.config.settings import Settings
from lead_intel.domain.enums import DataProvider, Industry, WebsiteStatus
from lead_intel.domain.models import (
    Business,
    BusinessContact,
    BusinessRatings,
    FeaturePresence,
    Lead,
    TechnicalCheck,
    WebsiteAudit,
)
from lead_intel.services.scoring_service import ScoringService


def _modern_audit(url: str) -> WebsiteAudit:
    return WebsiteAudit(
        status=WebsiteStatus.LIVE,
        final_url=url,
        technical=TechnicalCheck(
            is_accessible=True, https_enabled=True, mobile_friendly=True,
            is_outdated=False, appears_slow=False, response_time_ms=600,
        ),
        features=FeaturePresence(
            has_contact_form=True, has_enquiry_button=True, has_whatsapp=True,
            has_maps_embed=True, has_social_links=True, has_testimonials=True,
            has_gallery=True, has_faq=True, has_privacy_policy=True, has_terms=True,
            has_cta=True,
        ),
    )


def _outdated_audit(url: str) -> WebsiteAudit:
    return WebsiteAudit(
        status=WebsiteStatus.LIVE,
        final_url=url,
        technical=TechnicalCheck(
            is_accessible=True, https_enabled=False, mobile_friendly=False,
            is_outdated=True, appears_slow=True, response_time_ms=4300,
        ),
        features=FeaturePresence(
            has_contact_form=False, has_enquiry_button=False, has_whatsapp=False,
            has_maps_embed=False, has_social_links=False, has_testimonials=False,
            has_gallery=False, has_faq=False, has_privacy_policy=False, has_terms=False,
            has_cta=False,
        ),
        problems=["Outdated: No mobile viewport", "Missing: WhatsApp link", "Site appears slow"],
    )


def _broken_audit(url: str) -> WebsiteAudit:
    return WebsiteAudit(
        status=WebsiteStatus.BROKEN, final_url=url,
        technical=TechnicalCheck(is_broken=True),
        problems=["Website returns an error (HTTP 503)."],
    )


_SEED = [
    ("IronCore Gym", Industry.GYM, "Baner", None, 4.9, 320, "https://instagram.com/ironcore"),
    ("Brew & Bloom Cafe", Industry.CAFE, "Kothrud", "outdated", 4.3, 145, None),
    ("Glow Salon & Spa", Industry.SALON, "Baner", "broken", 4.6, 88, "https://instagram.com/glow"),
    ("Shiny Smile Dental", Industry.DENTAL_CLINIC, "Viman Nagar", "modern", 4.7, 210,
     "https://instagram.com/shinysmile"),
    ("FlexZone Physiotherapy", Industry.PHYSIOTHERAPY, "Aundh", None, 4.8, 176, None),
    ("Little Picasso Art Academy", Industry.MUSIC_ACADEMY, "Wakad", "outdated", 4.5, 62, None),
]


def sample_leads(settings: Settings) -> list[Lead]:
    """Return a ranked batch of fully-enriched demo leads."""
    scoring = ScoringService(settings)
    ai = create_ai_service(settings)

    audits = {
        "modern": _modern_audit,
        "outdated": _outdated_audit,
        "broken": _broken_audit,
    }

    leads: list[Lead] = []
    for name, industry, area, state, rating, reviews, instagram in _SEED:
        if state is None:
            audit = WebsiteAudit.no_website()
        else:
            audit = audits[state](f"https://{name.split()[0].lower()}.example")
        business = Business(
            source=DataProvider.GOOGLE_PLACES,
            source_id=name,
            name=name,
            industry=industry,
            area=area,
            city="Pune",
            address=f"{area}, Pune",
            contact=BusinessContact(
                phone="+91 90000 00000", website=audit.final_url, instagram=instagram
            ),
            ratings=BusinessRatings(rating=rating, review_count=reviews),
        )
        lead = Lead(business=business, audit=audit)
        scoring.enrich(lead)
        ai.enrich(lead)
        leads.append(lead)

    leads.sort(key=lambda x: x.lead_score.value if x.lead_score else 0.0, reverse=True)
    return leads
