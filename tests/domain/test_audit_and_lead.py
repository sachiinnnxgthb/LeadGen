"""Tests for the website audit and lead aggregate models."""

from __future__ import annotations

from lead_intel.domain.enums import LeadPriority, WebsiteQuality, WebsiteStatus
from lead_intel.domain.models import (
    Business,
    FeaturePresence,
    Lead,
    LeadScore,
    TechnicalCheck,
    WebsiteAudit,
)


def test_no_website_factory() -> None:
    audit = WebsiteAudit.no_website()
    assert audit.status == WebsiteStatus.NO_WEBSITE
    assert audit.quality == WebsiteQuality.NONE
    assert audit.problems


def test_quality_broken_from_status() -> None:
    audit = WebsiteAudit(status=WebsiteStatus.BROKEN)
    assert audit.quality == WebsiteQuality.BROKEN


def test_quality_outdated_from_flag() -> None:
    audit = WebsiteAudit(
        status=WebsiteStatus.LIVE,
        technical=TechnicalCheck(is_accessible=True, is_outdated=True),
    )
    assert audit.quality == WebsiteQuality.OUTDATED


def test_missing_features_only_reports_false_not_none() -> None:
    features = FeaturePresence(has_contact_form=False, has_gallery=True, has_faq=None)
    missing = features.missing_features()
    assert "Contact form" in missing
    assert "Gallery" not in missing
    assert "FAQ" not in missing  # None = undetermined, not missing


def test_lead_convenience_accessors(sample_business: Business) -> None:
    lead = Lead(
        business=sample_business,
        audit=WebsiteAudit.no_website(),
        lead_score=LeadScore(value=8.0, priority=LeadPriority.HIGH),
    )
    assert lead.has_no_website is True
    assert lead.is_high_priority is True
    assert lead.website_status == WebsiteStatus.NO_WEBSITE


def test_lead_defaults_when_unenriched(sample_business: Business) -> None:
    lead = Lead(business=sample_business)
    assert lead.website_status == WebsiteStatus.UNKNOWN
    assert lead.priority is None
    assert lead.crm.whatsapp_sent is False
