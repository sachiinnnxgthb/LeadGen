"""Website audit domain model.

Structured result of probing a business's website. Populated by the audit
service (later phase); scoring consumes it. Every boolean here maps to a
concrete "missing feature" the sales team can point at.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from lead_intel.domain.enums import WebsiteQuality, WebsiteStatus


class TechnicalCheck(BaseModel):
    """Low-level reachability and hygiene signals."""

    is_accessible: bool = False
    https_enabled: bool = False
    is_broken: bool = False
    redirects: bool = False
    redirect_target: str | None = None
    status_code: int | None = None
    response_time_ms: int | None = Field(default=None, ge=0)
    mobile_friendly: bool | None = None  # None = could not determine
    appears_slow: bool | None = None
    is_outdated: bool | None = None


class FeaturePresence(BaseModel):
    """Presence/absence of conversion & trust elements on the site.

    ``None`` means "not determined" (e.g. site unreachable); ``False`` means
    "checked and genuinely missing" — a real sales talking point.
    """

    has_contact_form: bool | None = None
    has_enquiry_button: bool | None = None
    has_whatsapp: bool | None = None
    has_maps_embed: bool | None = None
    has_social_links: bool | None = None
    has_testimonials: bool | None = None
    has_gallery: bool | None = None
    has_faq: bool | None = None
    has_privacy_policy: bool | None = None
    has_terms: bool | None = None
    has_cta: bool | None = None

    def missing_features(self) -> list[str]:
        """Human-readable list of features explicitly determined to be missing."""
        labels = {
            "has_contact_form": "Contact form",
            "has_enquiry_button": "Enquiry button",
            "has_whatsapp": "WhatsApp link",
            "has_maps_embed": "Google Maps embed",
            "has_social_links": "Social media links",
            "has_testimonials": "Testimonials",
            "has_gallery": "Gallery",
            "has_faq": "FAQ",
            "has_privacy_policy": "Privacy Policy",
            "has_terms": "Terms of Service",
            "has_cta": "Call to action",
        }
        return [
            label
            for attr, label in labels.items()
            if getattr(self, attr) is False
        ]


class WebsiteAudit(BaseModel):
    """Aggregated audit outcome for one business's website."""

    status: WebsiteStatus = WebsiteStatus.UNKNOWN
    final_url: str | None = None
    technical: TechnicalCheck = Field(default_factory=TechnicalCheck)
    features: FeaturePresence = Field(default_factory=FeaturePresence)
    problems: list[str] = Field(
        default_factory=list,
        description="Plain-language issues surfaced by the audit.",
    )
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def quality(self) -> WebsiteQuality:
        """Coarse quality bucket derived from status + outdated flag."""
        if self.status == WebsiteStatus.NO_WEBSITE:
            return WebsiteQuality.NONE
        if self.status in (WebsiteStatus.BROKEN, WebsiteStatus.INACCESSIBLE):
            return WebsiteQuality.BROKEN
        if self.technical.is_outdated:
            return WebsiteQuality.OUTDATED
        return WebsiteQuality.MODERN

    @classmethod
    def no_website(cls) -> WebsiteAudit:
        """Factory for businesses with no website listed."""
        return cls(
            status=WebsiteStatus.NO_WEBSITE,
            problems=["No website found for this business."],
        )
