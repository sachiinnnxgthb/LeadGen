"""Lead score (0-10) computation.

Turns a business + its website audit into a :class:`LeadScore` with a transparent,
configurable breakdown and a High/Medium/Low priority. Every weight and threshold
comes from :class:`LeadScoreSettings`, so the agency can re-tune what "a good lead"
means without code changes.
"""

from __future__ import annotations

from lead_intel.config.settings import LeadScoreSettings
from lead_intel.domain.enums import LeadPriority, WebsiteQuality, WebsiteStatus
from lead_intel.domain.models import Business, LeadScore, ScoreContribution, WebsiteAudit

_MAX_SCORE = 10.0


class LeadScorer:
    """Scores a business's sales potential on a 0-10 scale."""

    def __init__(self, rules: LeadScoreSettings) -> None:
        self._rules = rules

    def score(self, business: Business, audit: WebsiteAudit) -> LeadScore:
        """Return a :class:`LeadScore` for ``business`` given its ``audit``."""
        r = self._rules
        contributions: list[ScoreContribution] = []

        # Website state — mutually exclusive, highest need first.
        if audit.status == WebsiteStatus.NO_WEBSITE:
            self._add(contributions, "No website — greenfield opportunity", r.no_website)
        elif audit.quality == WebsiteQuality.BROKEN:
            self._add(contributions, "Website is broken", r.broken_website)
        elif audit.quality == WebsiteQuality.OUTDATED:
            self._add(contributions, "Website is outdated", r.outdated_website)

        # Business demand signals.
        rating = business.ratings.rating
        if rating is not None and rating > r.rating_threshold:
            self._add(contributions, f"High rating ({rating})", r.rating_gt_threshold)
        if business.ratings.review_count > r.reviews_threshold:
            self._add(
                contributions,
                f"Many reviews ({business.ratings.review_count})",
                r.reviews_gt_threshold,
            )
        if business.contact.has_instagram:
            self._add(contributions, "Active on Instagram", r.has_instagram)
        if business.contact.has_phone:
            self._add(contributions, "Phone number available", r.has_phone)

        raw = sum(c.points for c in contributions)
        value = min(raw, _MAX_SCORE)
        return LeadScore(value=value, priority=self._priority(value), breakdown=contributions)

    def _priority(self, value: float) -> LeadPriority:
        if value >= self._rules.high_priority_min:
            return LeadPriority.HIGH
        if value >= self._rules.medium_priority_min:
            return LeadPriority.MEDIUM
        return LeadPriority.LOW

    @staticmethod
    def _add(contributions: list[ScoreContribution], reason: str, points: float) -> None:
        if points:
            contributions.append(ScoreContribution(reason=reason, points=float(points)))
