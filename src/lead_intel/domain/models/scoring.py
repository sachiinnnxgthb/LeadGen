"""Scoring domain models.

Holds the *results* of scoring — the computation lives in the service layer
(later phase). Each score carries human-readable explanations so the UI, PDF,
and CRM can always answer "why?".
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from lead_intel.domain.enums import LeadPriority, PackageTier, ScoreDimension


class ScoreContribution(BaseModel):
    """A single line item explaining part of a score."""

    reason: str
    points: float


class WebsiteScore(BaseModel):
    """0-100 website quality score with sub-dimension breakdown.

    ``subscores`` are keyed by :class:`ScoreDimension`; ``explanations`` gives a
    per-dimension rationale string. ``total`` is the weighted roll-up computed by
    the scoring service.
    """

    total: float = Field(..., ge=0.0, le=100.0)
    subscores: dict[ScoreDimension, float] = Field(default_factory=dict)
    explanations: dict[ScoreDimension, str] = Field(default_factory=dict)

    @property
    def performance(self) -> float | None:
        return self.subscores.get(ScoreDimension.PERFORMANCE)

    @property
    def mobile(self) -> float | None:
        return self.subscores.get(ScoreDimension.MOBILE)

    @property
    def trust(self) -> float | None:
        return self.subscores.get(ScoreDimension.TRUST)

    @property
    def seo(self) -> float | None:
        return self.subscores.get(ScoreDimension.SEO)

    @property
    def user_experience(self) -> float | None:
        return self.subscores.get(ScoreDimension.USER_EXPERIENCE)


class LeadScore(BaseModel):
    """0-10 sales-readiness score with a transparent breakdown."""

    value: float = Field(..., ge=0.0, le=10.0)
    priority: LeadPriority
    breakdown: list[ScoreContribution] = Field(default_factory=list)

    @property
    def summary(self) -> str:
        """One-line rationale joining all positive contributions."""
        parts = [f"{c.reason} (+{c.points:g})" for c in self.breakdown if c.points]
        return "; ".join(parts) if parts else "No qualifying signals."


class SalesRecommendation(BaseModel):
    """Recommended package and the reasoning behind it."""

    package: PackageTier
    price: int = Field(..., ge=0)
    rationale: str
