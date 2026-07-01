"""Apify Google Maps provider.

Implements :class:`BusinessProvider` against Apify's Google Maps scraper actor
via the synchronous ``run-sync-get-dataset-items`` endpoint, which runs the actor
and returns the scraped dataset items in a single call. Each item is mapped onto
the common :class:`Business` model.

Design notes:
- Same injected-client + shared retry/error-translation stack as the Google
  provider, so behaviour is uniform and tests need no network or live token.
- Actor runs can take from seconds to minutes, so the default timeout is much
  larger than for a plain REST call.
- Field names vary across actor versions; mapping is defensive and tries several
  known keys before giving up on a record.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from lead_intel.core.exceptions import ProviderError
from lead_intel.core.logging import get_logger
from lead_intel.domain.enums import DataProvider
from lead_intel.domain.models import Business, BusinessContact, BusinessRatings, GeoLocation
from lead_intel.providers.base import BusinessProvider, SearchQuery
from lead_intel.providers.http import request_with_retries

logger = get_logger("providers.apify_gmaps")

_BASE_URL = "https://api.apify.com/v2/acts"
_DEFAULT_ACTOR_ID = "compass~crawler-google-places"


class ApifyGoogleMapsProvider(BusinessProvider):
    """Discovers businesses via an Apify Google Maps scraper actor."""

    provider = DataProvider.APIFY_GMAPS

    def __init__(
        self,
        api_token: str,
        *,
        actor_id: str = _DEFAULT_ACTOR_ID,
        client: httpx.Client | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 300.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """
        Args:
            api_token: Apify API token.
            actor_id: Actor to run (path form, e.g. ``compass~crawler-google-places``).
            client: Injected httpx client (tests pass a ``MockTransport`` client).
            max_retries: Retries for transient (5xx / rate-limit) failures.
            timeout_seconds: Per-request timeout; generous because actor runs are slow.
            sleep: Injected sleep hook so back-off is instant in tests.
        """
        if not api_token:
            raise ProviderError("Apify API token is required", provider="apify_gmaps")
        self._token = api_token
        self._actor_id = actor_id or _DEFAULT_ACTOR_ID
        self._max_retries = max_retries
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_seconds)

    # -- BusinessProvider ---------------------------------------------------

    def _fetch(self, query: SearchQuery) -> list[Business]:
        items = self._run_actor(query)
        businesses: list[Business] = []
        for item in items:
            mapped = self._map_item(item, query)
            if mapped is not None:
                businesses.append(mapped)
        return businesses

    # -- HTTP ---------------------------------------------------------------

    def _run_actor(self, query: SearchQuery) -> list[dict[str, Any]]:
        """Run the actor synchronously and return the raw dataset items."""
        url = f"{_BASE_URL}/{self._actor_id}/run-sync-get-dataset-items"
        actor_input = {
            "searchStringsArray": [query.as_text_query()],
            "maxCrawledPlacesPerSearch": query.max_results,
            "language": "en",
            "countryCode": query.country[:2].lower() if query.country else "in",
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        response = request_with_retries(
            lambda: self._client.post(url, json=actor_input, headers=headers),
            provider="apify_gmaps",
            max_retries=self._max_retries,
            sleep=self._sleep,
        )
        payload: Any = response.json()
        if not isinstance(payload, list):
            raise ProviderError(
                "Unexpected Apify response: expected a list of dataset items",
                provider="apify_gmaps",
            )
        return payload

    # -- Mapping ------------------------------------------------------------

    def _map_item(self, item: dict[str, Any], query: SearchQuery) -> Business | None:
        """Map one Apify dataset item to a :class:`Business`; skip malformed ones."""
        source_id = item.get("placeId") or item.get("cid") or item.get("fid") or item.get("url")
        name = item.get("title")
        if not source_id or not name:
            logger.debug("skipping apify item with missing id/title", extra={"raw": item})
            return None

        location = None
        loc = item.get("location")
        if isinstance(loc, dict) and "lat" in loc and "lng" in loc:
            location = GeoLocation(latitude=loc["lat"], longitude=loc["lng"])

        contact = BusinessContact(
            phone=item.get("phone") or item.get("phoneUnformatted"),
            website=item.get("website"),
        )
        ratings = BusinessRatings(
            rating=item.get("totalScore"),
            review_count=item.get("reviewsCount") or 0,
        )

        return Business(
            source=self.provider,
            source_id=str(source_id),
            name=name,
            industry=query.industry,
            raw_category=item.get("categoryName"),
            area=item.get("neighborhood") or query.area,
            address=item.get("address"),
            city=item.get("city") or query.city,
            location=location,
            contact=contact,
            ratings=ratings,
            raw=item,
        )

    # -- Lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying client if this provider created it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> ApifyGoogleMapsProvider:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
