"""Tests for the website page fetcher."""

from __future__ import annotations

import httpx

from lead_intel.audit.fetcher import PageFetcher


def _fetcher(handler: httpx.MockTransport, times: list[float] | None = None) -> PageFetcher:
    client = httpx.Client(transport=handler, follow_redirects=True)
    clock = iter(times) if times else None
    return PageFetcher(client=client, clock=(lambda: next(clock)) if clock else (lambda: 0.0))


def test_successful_fetch_captures_html_and_https() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html="<html><body>hi</body></html>")

    result = _fetcher(httpx.MockTransport(handler)).fetch("https://example.com")

    assert result.ok is True
    assert result.status_code == 200
    assert result.https is True
    assert result.redirected is False
    assert result.html is not None and "hi" in result.html


def test_response_time_measured_from_injected_clock() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html="ok")

    # clock returns start=1.0 then end=4.5 -> 3500 ms
    result = _fetcher(httpx.MockTransport(handler), times=[1.0, 4.5]).fetch("https://x.com")
    assert result.response_time_ms == 3500


def test_redirect_is_flagged() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(301, headers={"Location": "https://new.example.com/home"})
        return httpx.Response(200, html="landed")

    result = _fetcher(httpx.MockTransport(handler)).fetch("https://example.com")
    assert result.redirected is True
    assert result.redirect_target == "https://new.example.com/home"


def test_http_error_status_still_ok_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, html="not found")

    result = _fetcher(httpx.MockTransport(handler)).fetch("https://example.com")
    assert result.ok is True
    assert result.status_code == 404


def test_timeout_captured_as_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    result = _fetcher(httpx.MockTransport(handler)).fetch("https://slow.example.com")
    assert result.ok is False
    assert result.error_kind == "timeout"


def test_connect_error_captured_as_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    result = _fetcher(httpx.MockTransport(handler)).fetch("http://dead.example.com")
    assert result.ok is False
    assert result.error_kind == "connect"
