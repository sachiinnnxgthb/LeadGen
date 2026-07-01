"""Lead aggregate root.

Composes a :class:`Business` with its audit, scores, sales recommendation,
AI content, and mutable CRM tracking state. This is the entity exporters
(Excel/PDF/CSV/JSON) and the UI consume.

The scoring/audit/AI sub-objects are optional because a lead is assembled
progressively through the pipeline: discovered -> audited -> scored -> written up.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from lead_intel.domain.enums import ContactStatus, LeadPriority, WebsiteQuality, WebsiteStatus
from lead_intel.domain.models.ai_content import AIContent
from lead_intel.domain.models.business import Business
from lead_intel.domain.models.scoring import LeadScore, SalesRecommendation, WebsiteScore
from lead_intel.domain.models.website_audit import WebsiteAudit


class CRMTracking(BaseModel):
    """Mutable, human-maintained sales tracking fields (editable in the CRM)."""

    contact_status: ContactStatus = ContactStatus.NOT_CONTACTED
    whatsapp_sent: bool = False
    call_status: str = ""
    follow_up_date: date | None = None
    notes: str = ""


class Lead(BaseModel):
    """The pipeline's output entity: a business enriched end-to-end."""

    business: Business
    audit: WebsiteAudit | None = None
    website_score: WebsiteScore | None = None
    lead_score: LeadScore | None = None
    recommendation: SalesRecommendation | None = None
    ai_content: AIContent | None = None
    crm: CRMTracking = Field(default_factory=CRMTracking)

    # --- Convenience accessors used by exporters / UI --------------------

    @property
    def priority(self) -> LeadPriority | None:
        return self.lead_score.priority if self.lead_score else None

    @property
    def website_status(self) -> WebsiteStatus:
        return self.audit.status if self.audit else WebsiteStatus.UNKNOWN

    @property
    def website_quality(self) -> WebsiteQuality:
        return self.audit.quality if self.audit else WebsiteQuality.NONE

    @property
    def has_no_website(self) -> bool:
        return self.website_status == WebsiteStatus.NO_WEBSITE

    @property
    def has_broken_website(self) -> bool:
        return self.website_quality == WebsiteQuality.BROKEN

    @property
    def has_outdated_website(self) -> bool:
        return self.website_quality == WebsiteQuality.OUTDATED

    @property
    def is_high_priority(self) -> bool:
        return self.priority == LeadPriority.HIGH
