"""Provider abstraction.

Defines the :class:`BusinessProvider` interface every data source implements and
the :class:`SearchQuery` value object callers pass in. The rest of the platform
depends only on this interface — never on a concrete vendor — so Google Places,
Apify, or a future source are fully interchangeable (Open/Closed principle).
"""

from __future__ import annotations

import abc

from pydantic import BaseModel, Field

from lead_intel.core.logging import get_logger
from lead_intel.domain.enums import DataProvider, Industry
from lead_intel.domain.models import Business

logger = get_logger("providers.base")


class SearchQuery(BaseModel):
    """A single, provider-agnostic discovery request.

    One query targets one industry in one locality. Callers typically fan a list
    of industries into one query each. ``area`` narrows within a city (e.g.
    "Koregaon Park"); when omitted the whole city is searched.
    """

    industry: Industry
    city: str = "Pune"
    state: str = "Maharashtra"
    country: str = "India"
    area: str | None = None
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    min_reviews: int = Field(default=0, ge=0)
    max_results: int = Field(default=60, ge=1, le=500)

    def as_text_query(self) -> str:
        """Render a natural-language search string, e.g.
        ``"dental clinic in Koregaon Park, Pune, Maharashtra, India"``.
        """
        where = ", ".join(part for part in (self.area, self.city, self.state, self.country) if part)
        return f"{self.industry.label.lower()} in {where}"


class BusinessProvider(abc.ABC):
    """Abstract data source that returns the common :class:`Business` model.

    Concrete providers implement :meth:`_fetch` (the vendor-specific call) and
    inherit :meth:`search`, which applies uniform post-filtering so rating/review
    thresholds behave identically across providers.
    """

    #: Identifies the concrete provider; set by subclasses.
    provider: DataProvider

    @abc.abstractmethod
    def _fetch(self, query: SearchQuery) -> list[Business]:
        """Vendor-specific fetch + mapping to :class:`Business`. No filtering."""
        raise NotImplementedError

    def search(self, query: SearchQuery) -> list[Business]:
        """Fetch businesses for ``query`` and apply threshold filtering.

        Returns at most ``query.max_results`` businesses that meet the minimum
        rating and review thresholds. Vendor errors surface as
        :class:`~lead_intel.core.exceptions.ProviderError` subclasses.
        """
        raw = self._fetch(query)
        kept = [b for b in raw if self._passes_filters(b, query)]
        logger.info(
            "provider search complete",
            extra={
                "provider": str(self.provider),
                "industry": str(query.industry),
                "fetched": len(raw),
                "kept": len(kept),
            },
        )
        return kept[: query.max_results]

    @staticmethod
    def _passes_filters(business: Business, query: SearchQuery) -> bool:
        """Apply minimum-rating and minimum-review thresholds.

        A business with no rating passes only when no rating threshold is set —
        we never fabricate a rating to clear the bar.
        """
        if query.min_rating > 0:
            rating = business.ratings.rating
            if rating is None or rating < query.min_rating:
                return False
        return business.ratings.review_count >= query.min_reviews
