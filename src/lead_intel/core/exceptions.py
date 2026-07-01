"""Exception hierarchy for the platform.

A single base (:class:`LeadIntelError`) lets callers catch anything the platform
raises, while specific subclasses allow targeted handling (e.g. back off on
:class:`RateLimitError`, skip on :class:`ProviderError`). Infrastructure layers
raise these instead of leaking vendor-specific exceptions upward.
"""

from __future__ import annotations


class LeadIntelError(Exception):
    """Base class for all platform errors."""


class ConfigurationError(LeadIntelError):
    """Invalid or missing configuration (e.g. absent API key, bad weights)."""


# --- Provider layer -------------------------------------------------------


class ProviderError(LeadIntelError):
    """A data provider failed to return usable results."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}" if provider else message)


class RateLimitError(ProviderError):
    """Provider signalled rate limiting; callers should back off and retry."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, provider)


class ProviderAuthError(ProviderError):
    """Authentication/authorization failure (bad or missing API key)."""


# --- Audit layer ----------------------------------------------------------


class WebsiteAuditError(LeadIntelError):
    """A recoverable failure while auditing a specific website."""


# --- Export layer ---------------------------------------------------------


class ExportError(LeadIntelError):
    """Failure while writing an Excel / PDF / CSV / JSON artifact."""
