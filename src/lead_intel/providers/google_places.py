"""Google Places provider.

Implements :class:`BusinessProvider` against the **Places API (New) v1**
``places:searchText`` endpoint, mapping each result onto the common
:class:`Business` model.

Design notes:
- The HTTP client is injected, so tests drive the exact request-building and
  mapping code through ``httpx.MockTransport`` — no network, no live key.
- Vendor HTTP failures are translated into the platform exception hierarchy
  (auth / rate-limit / generic provider error) so callers handle them uniformly.
- Pagination follows ``nextPageToken`` until ``max_results`` is satisfied.
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

logger = get_logger("providers.google_places")

_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
_PAGE_SIZE = 20  # Places API (New) maximum for searchText.

# Only the fields we map are requested, keeping responses lean and billing lower.
_FIELD_MASK = ",".join(
    f"places.{f}"
    for f in (
        "id",
        "displayName",
        "formattedAddress",
        "rating",
        "userRatingCount",
        "websiteUri",
        "nationalPhoneNumber",
        "internationalPhoneNumber",
        "location",
        "types",
        "primaryType",
    )
) + ",nextPageToken"


class GooglePlacesProvider(BusinessProvider):
    """Discovers businesses via the Google Places API (New)."""

    provider = DataProvider.GOOGLE_PLACES

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 15.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """
        Args:
            api_key: Google Cloud API key with Places API (New) enabled.
            client: Injected httpx client (tests pass a ``MockTransport`` client).
                When omitted a default client is created lazily and owned here.
            max_retries: Retries for transient (5xx / rate-limit) failures.
            timeout_seconds: Per-request timeout for the default client.
            sleep: Injected sleep hook so back-off is instant in tests.
        """
        if not api_key:
            raise ProviderError("Google Places API key is required", provider="google_places")
        self._api_key = api_key
        self._max_retries = max_retries
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_seconds)

    # -- BusinessProvider ---------------------------------------------------

    def _fetch(self, query: SearchQuery) -> list[Business]:
        businesses: list[Business] = []
        page_token: str | None = None

        while len(businesses) < query.max_results:
            payload = self._request_page(query.as_text_query(), page_token)
            for place in payload.get("places", []) or []:
                mapped = self._map_place(place, query)
                if mapped is not None:
                    businesses.append(mapped)

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return businesses

    # -- HTTP ---------------------------------------------------------------

    def _request_page(self, text_query: str, page_token: str | None) -> dict[str, Any]:
        """POST one page of results, with retry/back-off on transient errors."""
        body: dict[str, object] = {"textQuery": text_query, "pageSize": _PAGE_SIZE}
        if page_token:
            body["pageToken"] = page_token
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }

        response = request_with_retries(
            lambda: self._client.post(_ENDPOINT, json=body, headers=headers),
            provider="google_places",
            max_retries=self._max_retries,
            sleep=self._sleep,
        )
        data: dict[str, Any] = response.json()
        return data

    # -- Mapping ------------------------------------------------------------

    def _map_place(self, place: dict[str, Any], query: SearchQuery) -> Business | None:
        """Map one Places result to a :class:`Business`; skip malformed entries."""
        place_id = place.get("id")
        name = (place.get("displayName") or {}).get("text")
        if not place_id or not name:
            logger.debug("skipping place with missing id/name", extra={"raw": place})
            return None

        location = None
        loc = place.get("location")
        if loc and "latitude" in loc and "longitude" in loc:
            location = GeoLocation(latitude=loc["latitude"], longitude=loc["longitude"])

        contact = BusinessContact(
            phone=place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber"),
            website=place.get("websiteUri"),
        )
        ratings = BusinessRatings(
            rating=place.get("rating"),
            review_count=place.get("userRatingCount") or 0,
        )

        return Business(
            source=self.provider,
            source_id=place_id,
            name=name,
            industry=query.industry,
            raw_category=place.get("primaryType"),
            area=query.area,
            address=place.get("formattedAddress"),
            city=query.city,
            location=location,
            contact=contact,
            ratings=ratings,
            raw=place,
        )

    # -- Lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying client if this provider created it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GooglePlacesProvider:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
