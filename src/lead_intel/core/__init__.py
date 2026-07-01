"""Core cross-cutting concerns: logging and the exception hierarchy."""

from __future__ import annotations

from lead_intel.core.exceptions import (
    ConfigurationError,
    ExportError,
    LeadIntelError,
    ProviderAuthError,
    ProviderError,
    RateLimitError,
    WebsiteAuditError,
)
from lead_intel.core.logging import configure_logging, get_logger

__all__ = [
    "LeadIntelError",
    "ConfigurationError",
    "ProviderError",
    "ProviderAuthError",
    "RateLimitError",
    "WebsiteAuditError",
    "ExportError",
    "configure_logging",
    "get_logger",
]
