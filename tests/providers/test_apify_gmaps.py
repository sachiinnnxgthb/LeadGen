"""Tests for the Apify Google Maps provider.

Drives request-building, error-translation, and mapping through
``httpx.MockTransport`` — no network, no live token.
"""

from __future__ import annotations

import httpx
import pytest

from lead_intel.core.exceptions import ProviderAuthError, ProviderError, RateLimitError
from lead_intel.domain.enums import DataProvider, Industry
from lead_intel.providers import ApifyGoogleMapsProvider, SearchQuery


def _item(place_id: str, title: str, **overrides: object) -> dict:
    base: dict = {
        "placeId": place_id,
        "title": title,
        "categoryName": "Gym",
        "address": "FC Road, Pune, Maharashtra, India",
        "neighborhood": "Shivajinagar",
        "city": "Pune",
        "phone": "+91 98765 43210",
        "website": "fitzonegym.in",
        "totalScore": 4.6,
        "reviewsCount": 180,
        "location": {"lat": 18.53, "lng": 73.85},
        "url": "https://maps.google.com/?cid=1",
    }
    base.update(overrides)
    return base


def _provider(handler: httpx.MockTransport, **kw: object) -> ApifyGoogleMapsProvider:
    client = httpx.Client(transport=handler)
    return ApifyGoogleMapsProvider(
        api_token="test-token", client=client, sleep=lambda _: None, **kw
    )


def _query(**kw: object) -> SearchQuery:
    defaults: dict = {"industry": Industry.GYM, "city": "Pune", "max_results": 60}
    defaults.update(kw)
    return SearchQuery(**defaults)  # type: ignore[arg-type]


def test_maps_item_to_business() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_item("p1", "FitZone Gym")])

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert len(results) == 1
    biz = results[0]
    assert biz.source == DataProvider.APIFY_GMAPS
    assert biz.source_id == "p1"
    assert biz.name == "FitZone Gym"
    assert biz.industry == Industry.GYM
    assert biz.area == "Shivajinagar"
    assert biz.contact.website == "https://fitzonegym.in"
    assert biz.ratings.rating == 4.6
    assert biz.ratings.review_count == 180
    assert biz.location is not None and biz.location.longitude == 73.85


def test_request_targets_run_sync_endpoint_with_auth() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["content"] = request.content
        return httpx.Response(200, json=[])

    provider = _provider(httpx.MockTransport(handler), actor_id="compass~crawler-google-places")
    provider.search(_query(industry=Industry.CAFE))

    assert "compass~crawler-google-places/run-sync-get-dataset-items" in captured["url"]
    assert captured["auth"] == "Bearer test-token"
    assert b"cafe in Pune" in captured["content"]
    assert b"searchStringsArray" in captured["content"]


def test_filters_applied_uniformly() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                _item("good", "Good", totalScore=4.9, reviewsCount=300),
                _item("low", "Low", totalScore=3.5, reviewsCount=300),
                _item("few", "Few", totalScore=4.9, reviewsCount=3),
            ],
        )

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query(min_rating=4.5, min_reviews=100))

    assert {b.source_id for b in results} == {"good"}


def test_fallback_source_id_when_place_id_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        item = _item("ignored", "NoPlaceId")
        del item["placeId"]
        item["cid"] = "cid-123"
        return httpx.Response(200, json=[item])

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert results[0].source_id == "cid-123"


def test_malformed_item_skipped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"categoryName": "Gym"}, _item("p1", "Valid")])

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert {b.source_id for b in results} == {"p1"}


def test_non_list_response_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "actor failed"})

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ProviderError):
        provider.search(_query())


def test_auth_error_on_401() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid token"}})

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ProviderAuthError):
        provider.search(_query())


def test_rate_limit_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": {"message": "slow down"}})
        return httpx.Response(200, json=[_item("p1", "A")])

    provider = _provider(httpx.MockTransport(handler))
    results = provider.search(_query())

    assert calls["n"] == 2
    assert len(results) == 1


def test_rate_limit_exhausts_and_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    provider = _provider(httpx.MockTransport(handler), max_retries=1)
    with pytest.raises(RateLimitError):
        provider.search(_query())


def test_missing_token_rejected() -> None:
    with pytest.raises(ProviderError):
        ApifyGoogleMapsProvider(api_token="")
