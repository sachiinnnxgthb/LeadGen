"""Website screenshot fetcher.

Grabs a thumbnail of a live website for embedding in proposal/audit PDFs and for
the in-app preview. Uses the free WordPress mShots service so no headless browser
needs to be installed on the host (works locally and on Streamlit Cloud alike).

Always fail-safe: any error, timeout, or non-image response returns ``None`` and
the caller falls back to a placeholder.
"""

from __future__ import annotations

import urllib.parse

import httpx

from lead_intel.core.logging import get_logger

logger = get_logger("exporters.screenshot")

_MSHOTS = "https://s.wordpress.com/mshots/v1/"
# Below this size the response is almost certainly the "generating…" placeholder.
_MIN_IMAGE_BYTES = 3000


def screenshot_url(url: str, *, width: int = 1200) -> str:
    """Return the mShots URL that renders a screenshot of ``url`` (usable in ``st.image``)."""
    return f"{_MSHOTS}{urllib.parse.quote(url, safe='')}?w={width}"


def fetch_screenshot(
    url: str | None,
    *,
    width: int = 1200,
    timeout: float = 20.0,
    client: httpx.Client | None = None,
) -> bytes | None:
    """Fetch a website screenshot as PNG bytes, or ``None`` on any failure.

    Args:
        url: The website to screenshot (``None``/empty returns ``None``).
        width: Rendered width in pixels.
        timeout: Request timeout.
        client: Optional injected httpx client (tests pass a MockTransport client).
    """
    if not url:
        return None

    own_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = http.get(screenshot_url(url, width=width))
        content_type = response.headers.get("content-type", "")
        if response.status_code == 200 and content_type.startswith("image") \
                and len(response.content) >= _MIN_IMAGE_BYTES:
            return response.content
        logger.info(
            "screenshot unavailable",
            extra={"url": url, "status": response.status_code, "bytes": len(response.content)},
        )
        return None
    except httpx.HTTPError as exc:
        logger.info("screenshot fetch failed", extra={"url": url, "error": str(exc)})
        return None
    finally:
        if own_client:
            http.close()
