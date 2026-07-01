"""Website fetcher.

Performs a single, timed HTTP GET for a website and returns a structured
:class:`FetchResult` describing reachability, redirects, HTTPS, timing, and the
HTML body. All network concerns live here so the analysis code stays pure and
easily testable; the httpx client and clock are injected.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import httpx

from lead_intel.core.logging import get_logger

logger = get_logger("audit.fetcher")

# Present a real browser UA so sites don't serve a degraded/blocked page.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36 LeadIntelBot/1.0"
)

ErrorKind = Literal["timeout", "connect", "other"]


@dataclass(frozen=True)
class FetchResult:
    """Outcome of fetching one website."""

    ok: bool
    status_code: int | None
    final_url: str | None
    html: str | None
    response_time_ms: int | None
    redirected: bool
    redirect_target: str | None
    https: bool
    error: str | None = None
    error_kind: ErrorKind | None = None


class PageFetcher:
    """Fetches a URL's HTML with redirects followed and timing captured."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 15.0,
        max_html_bytes: int = 3_000_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """
        Args:
            client: Injected httpx client (tests pass a ``MockTransport`` client).
            timeout_seconds: Per-request timeout for the default client.
            max_html_bytes: Cap on HTML retained for analysis (avoids huge pages).
            clock: Monotonic clock hook so response timing is deterministic in tests.
        """
        self._max_html_bytes = max_html_bytes
        self._clock = clock
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )

    def fetch(self, url: str) -> FetchResult:
        """GET ``url``, following redirects, returning a :class:`FetchResult`.

        Never raises for network failures — transport errors are captured in the
        returned result so the audit engine can classify them into a status.
        """
        start = self._clock()
        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            return self._failure(url, exc, "timeout")
        except httpx.ConnectError as exc:
            return self._failure(url, exc, "connect")
        except httpx.HTTPError as exc:
            return self._failure(url, exc, "other")

        elapsed_ms = int((self._clock() - start) * 1000)
        final_url = str(response.url)
        redirected = len(response.history) > 0
        html = response.text[: self._max_html_bytes] if response.text else None

        return FetchResult(
            ok=True,
            status_code=response.status_code,
            final_url=final_url,
            html=html,
            response_time_ms=elapsed_ms,
            redirected=redirected,
            redirect_target=final_url if redirected else None,
            https=final_url.lower().startswith("https://"),
        )

    def _failure(self, url: str, exc: Exception, kind: ErrorKind) -> FetchResult:
        logger.info("website fetch failed", extra={"url": url, "kind": kind, "error": str(exc)})
        return FetchResult(
            ok=False,
            status_code=None,
            final_url=url,
            html=None,
            response_time_ms=None,
            redirected=False,
            redirect_target=None,
            https=url.lower().startswith("https://"),
            error=str(exc),
            error_kind=kind,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> PageFetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
