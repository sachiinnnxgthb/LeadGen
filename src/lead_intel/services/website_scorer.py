"""Website score (0-100) computation.

Turns a :class:`WebsiteAudit` into a :class:`WebsiteScore` with five sub-scores
(Performance, Mobile, Trust, SEO, User Experience) and a plain-language
explanation for each. The sub-score → total roll-up uses the configurable weights
from :class:`WebsiteScoreSettings`; the per-dimension rubric below is intentionally
transparent so the number is always defensible to a prospect.
"""

from __future__ import annotations

from lead_intel.config.settings import WebsiteScoreSettings
from lead_intel.domain.enums import ScoreDimension, WebsiteStatus
from lead_intel.domain.models import FeaturePresence, TechnicalCheck, WebsiteAudit, WebsiteScore

# Per-dimension rubric: how many points each positive signal contributes.
# Sub-scores are clamped to 0-100; the dimension weights (from settings) decide
# how much each rolls into the final total.
_TRUST_POINTS = {
    "https": 25,
    "privacy": 15,
    "terms": 10,
    "testimonials": 25,
    "social": 15,
    "contactable": 10,  # contact form or WhatsApp
}
_SEO_POINTS = {
    "https": 25,
    "mobile": 25,
    "not_outdated": 20,
    "maps": 15,
    "social": 15,
}
_UX_POINTS = {
    "cta": 20,
    "contact_form": 20,
    "enquiry": 15,
    "gallery": 15,
    "faq": 15,
    "whatsapp": 15,
}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _explain(missing: list[str], *, good: str, gap_label: str) -> str:
    """Return the positive message when nothing is missing, else list the gaps."""
    return good if not missing else f"{gap_label}: {', '.join(missing)}."


class WebsiteScorer:
    """Computes the 0-100 website score from an audit."""

    def __init__(self, weights: WebsiteScoreSettings) -> None:
        self._weights = weights.as_dimension_map()

    def score(self, audit: WebsiteAudit) -> WebsiteScore:
        """Return a :class:`WebsiteScore` for ``audit``."""
        if audit.status == WebsiteStatus.NO_WEBSITE:
            return self._zero("No website exists for this business.")

        dimensions = {
            ScoreDimension.PERFORMANCE: self._performance(audit.technical),
            ScoreDimension.MOBILE: self._mobile(audit.technical),
            ScoreDimension.TRUST: self._trust(audit),
            ScoreDimension.SEO: self._seo(audit),
            ScoreDimension.USER_EXPERIENCE: self._user_experience(audit.features),
        }
        subscores = {dim: round(val, 1) for dim, (val, _) in dimensions.items()}
        explanations = {dim: why for dim, (_, why) in dimensions.items()}
        total = round(sum(subscores[dim] * weight for dim, weight in self._weights.items()), 1)
        return WebsiteScore(total=total, subscores=subscores, explanations=explanations)

    # -- dimensions ---------------------------------------------------------

    def _performance(self, tech: TechnicalCheck) -> tuple[float, str]:
        if not tech.is_accessible:
            return 0.0, "Website is not reachable, so performance cannot be delivered."
        if tech.appears_slow:
            ms = tech.response_time_ms
            return 40.0, f"Site responds slowly ({ms} ms) — visitors are likely to bounce."
        return 92.0, "Site responds quickly."

    def _mobile(self, tech: TechnicalCheck) -> tuple[float, str]:
        if tech.mobile_friendly is True:
            return 95.0, "Responsive viewport detected — adapts to mobile screens."
        if tech.mobile_friendly is False:
            return 25.0, "No responsive viewport — likely broken on mobile devices."
        return 50.0, "Mobile-friendliness could not be determined."

    def _trust(self, audit: WebsiteAudit) -> tuple[float, str]:
        f = audit.features
        earned = {
            "https": audit.technical.https_enabled,
            "privacy": f.has_privacy_policy is True,
            "terms": f.has_terms is True,
            "testimonials": f.has_testimonials is True,
            "social": f.has_social_links is True,
            "contactable": f.has_contact_form is True or f.has_whatsapp is True,
        }
        score = _clamp(sum(_TRUST_POINTS[k] for k, ok in earned.items() if ok))
        missing = [k for k, ok in earned.items() if not ok]
        return score, _explain(
            missing, good="Strong trust signals.", gap_label="Missing trust signals"
        )

    def _seo(self, audit: WebsiteAudit) -> tuple[float, str]:
        tech = audit.technical
        f = audit.features
        earned = {
            "https": tech.https_enabled,
            "mobile": tech.mobile_friendly is True,
            "not_outdated": tech.is_outdated is not True,
            "maps": f.has_maps_embed is True,
            "social": f.has_social_links is True,
        }
        score = _clamp(sum(_SEO_POINTS[k] for k, ok in earned.items() if ok))
        missing = [k for k, ok in earned.items() if not ok]
        return score, _explain(missing, good="Solid on-page SEO basics.", gap_label="SEO gaps")

    def _user_experience(self, f: FeaturePresence) -> tuple[float, str]:
        earned = {
            "cta": f.has_cta is True,
            "contact_form": f.has_contact_form is True,
            "enquiry": f.has_enquiry_button is True,
            "gallery": f.has_gallery is True,
            "faq": f.has_faq is True,
            "whatsapp": f.has_whatsapp is True,
        }
        score = _clamp(sum(_UX_POINTS[k] for k, ok in earned.items() if ok))
        missing = [k for k, ok in earned.items() if not ok]
        return score, _explain(missing, good="Rich user experience.", gap_label="UX gaps")

    def _zero(self, reason: str) -> WebsiteScore:
        subscores = {dim: 0.0 for dim in ScoreDimension}
        explanations = {dim: reason for dim in ScoreDimension}
        return WebsiteScore(total=0.0, subscores=subscores, explanations=explanations)
