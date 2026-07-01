"""Shared HTTP utilities for data providers.

Concrete providers differ only in *what* they request and *how* they map the
response. The transport concerns — retry with back-off, transient-vs-fatal
classification, and translating vendor HTTP errors into the platform exception
hierarchy — are identical, so they live here and are reused (DRY).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from lead_intel.core.exceptions import ProviderAuthError, ProviderError, RateLimitError
from lead_intel.core.logging import get_logger

logger = get_logger("providers.http")

_MAX_BACKOFF_SECONDS = 30.0


def extract_error_message(response: httpx.Response) -> str:
    """Best-effort human-readable message from a vendor error payload.

    Handles the common shapes ``{"error": {"message": ...}}``,
    ``{"error": "..."}``, and ``{"message": ...}``; falls back to raw text.
    """
    try:
        data: Any = response.json()
    except ValueError:
        return response.text or "unknown error"

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(error, str) and error:
            return error
        if data.get("message"):
            return str(data["message"])
    return response.text or "unknown error"


def classify_response(response: httpx.Response, *, provider: str) -> ProviderError | None:
    """Map a response to a platform exception, or ``None`` when successful.

    - 2xx            -> ``None``
    - 401 / 403      -> :class:`ProviderAuthError`
    - 429            -> :class:`RateLimitError` (honouring ``Retry-After``)
    - everything else -> :class:`ProviderError`
    """
    if response.is_success:
        return None

    message = extract_error_message(response)
    if response.status_code in (401, 403):
        return ProviderAuthError(message, provider=provider)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        return RateLimitError(
            message,
            provider=provider,
            retry_after=float(retry_after) if retry_after else None,
        )
    return ProviderError(f"HTTP {response.status_code}: {message}", provider=provider)


def backoff(attempt: int, sleep: Callable[[float], None], *, override: float | None = None) -> None:
    """Sleep before a retry using exponential back-off (or an explicit override)."""
    delay = override if override is not None else min(2.0 ** attempt, _MAX_BACKOFF_SECONDS)
    logger.warning("retrying request", extra={"attempt": attempt + 1, "delay_seconds": delay})
    sleep(delay)


def request_with_retries(
    send: Callable[[], httpx.Response],
    *,
    provider: str,
    max_retries: int,
    sleep: Callable[[float], None],
    classify: Callable[[httpx.Response], ProviderError | None] | None = None,
) -> httpx.Response:
    """Execute ``send`` with retry/back-off, returning the successful response.

    Retries only transient failures (rate-limit and 5xx) up to ``max_retries``;
    authentication and other 4xx errors fail fast. Network errors are retried and,
    if still failing, surfaced as :class:`ProviderError`.

    Args:
        send: Thunk that performs one HTTP request and returns the response.
        provider: Provider name used in error messages/logs.
        max_retries: Maximum retry attempts for transient failures.
        sleep: Injected sleep hook (tests pass a no-op for instant back-off).
        classify: Response classifier; defaults to :func:`classify_response`.
    """
    classifier = classify or (lambda r: classify_response(r, provider=provider))
    attempt = 0
    while True:
        try:
            response = send()
        except httpx.RequestError as exc:
            if attempt >= max_retries:
                raise ProviderError(
                    f"Network error contacting {provider}: {exc}", provider=provider
                ) from exc
            backoff(attempt, sleep)
            attempt += 1
            continue

        error = classifier(response)
        if error is None:
            return response

        transient = isinstance(error, RateLimitError) or (500 <= response.status_code < 600)
        if transient and attempt < max_retries:
            backoff(attempt, sleep, override=getattr(error, "retry_after", None))
            attempt += 1
            continue
        raise error
