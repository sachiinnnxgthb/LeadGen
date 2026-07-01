"""Tests for the Google Places provider.

Uses ``httpx.MockTransport`` to exercise the real request-building, pagination,
error-translation, and mapping code without any network or live API key.
"""

from __future__ import annotations

import httpx
import pytest

from lead_intel.core.exceptions import ProviderAuthError, ProviderError, RateLimitError
from lead_intel.domain.enums import DataProvider, Industry
from lead_intel.providers import GooglePlacesProvider, SearchQuery


def _place(place_id: str, name: str, **overrides: object) -> dict:
    base: dict = {
        "id": place_id,
        "displayName": {"text": name, "languageCode": "en"},
        "formattedAddress": "FC Road, Pune, Maharashtra, India",
        "rating": 4.7,
        "userRatingCount": 240,
        "websiteUri": "fitzonegym.in",
        "nationalPhoneNumber": "098765 43210",
        "location": {"latitude": 18.52, "longitude": 73.85},
        "primaryType": "gym",
    }
    base.update(overrides)
    return base


def _provider(handler: httpx.MockTransport) -> GooglePlacesProvider:
    client = httpx.Client(transport=handler)
    # sleep is stubbed so retry back-off never actually waits.
    return GooglePlacesProvider(api_key="test-key", client=client, sleep=lambda _: None)


def _query(**kw: object) -> SearchQuery:
    defaults: dict = {"industry": Industry.GYM, "city": "Pune", "max_results": 60}
    defaults.update(kw)
    return SearchQuery(**defaults)  # type: ignore[arg-type]


def test_maps_place_to_business() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"places": [_place("p1", "FitZone Gym")]})

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert len(results) == 1
    biz = results[0]
    assert biz.source == DataProvider.GOOGLE_PLACES
    assert biz.source_id == "p1"
    assert biz.name == "FitZone Gym"
    assert biz.industry == Industry.GYM
    assert biz.contact.website == "https://fitzonegym.in"  # scheme normalized
    assert biz.contact.phone == "098765 43210"
    assert biz.ratings.rating == 4.7
    assert biz.ratings.review_count == 240
    assert biz.location is not None and biz.location.latitude == 18.52


def test_request_shape_headers_and_body() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["content"] = request.content
        return httpx.Response(200, json={"places": []})

    provider = _provider(httpx.MockTransport(handler))
    provider.search(_query(industry=Industry.DENTAL_CLINIC, area="Koregaon Park"))

    assert captured["headers"]["X-Goog-Api-Key"] == "test-key"
    assert "places.id" in captured["headers"]["X-Goog-FieldMask"]
    assert b"dental clinic in Koregaon Park, Pune" in captured["content"]


def test_pagination_follows_next_page_token() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                200,
                json={"places": [_place("p1", "A")], "nextPageToken": "tok"},
            )
        return httpx.Response(200, json={"places": [_place("p2", "B")]})

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert calls["n"] == 2
    assert {b.source_id for b in results} == {"p1", "p2"}


def test_max_results_caps_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        places = [_place(f"p{i}", f"Gym {i}") for i in range(20)]
        # Always advertise another page; provider must stop at max_results.
        return httpx.Response(200, json={"places": places, "nextPageToken": "more"})

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query(max_results=5))

    assert len(results) == 5


def test_filters_by_min_rating_and_reviews() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "places": [
                    _place("good", "Good", rating=4.8, userRatingCount=300),
                    _place("low_rating", "LowRating", rating=3.9, userRatingCount=300),
                    _place("few_reviews", "FewReviews", rating=4.9, userRatingCount=5),
                    _place("no_rating", "NoRating", rating=None, userRatingCount=0),
                ]
            },
        )

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query(min_rating=4.5, min_reviews=100))

    assert {b.source_id for b in results} == {"good"}


def test_auth_error_raised_on_403() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "API key invalid"}})

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ProviderAuthError):
        provider.search(_query())


def test_rate_limit_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"error": {"message": "slow down"}},
            )
        return httpx.Response(200, json={"places": [_place("p1", "A")]})

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert calls["n"] == 2
    assert len(results) == 1


def test_rate_limit_exhausts_retries_and_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GooglePlacesProvider(api_key="k", client=client, max_retries=1, sleep=lambda _: None)
    with pytest.raises(RateLimitError):
        provider.search(_query())


def test_server_error_translated() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "boom"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GooglePlacesProvider(api_key="k", client=client, max_retries=0, sleep=lambda _: None)
    with pytest.raises(ProviderError):
        provider.search(_query())


def test_malformed_place_is_skipped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"places": [{"id": "no-name"}, _place("p1", "Valid")]},
        )

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert {b.source_id for b in results} == {"p1"}


def test_missing_api_key_rejected() -> None:
    with pytest.raises(ProviderError):
        GooglePlacesProvider(api_key="")
