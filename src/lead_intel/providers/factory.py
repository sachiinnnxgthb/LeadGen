"""Provider factory.

Resolves a :class:`~lead_intel.domain.enums.DataProvider` to a concrete
:class:`~lead_intel.providers.base.BusinessProvider`, wiring in credentials and
tuning from :class:`~lead_intel.config.settings.Settings`. Callers depend on the
factory + interface, never on concrete provider constructors.
"""

from __future__ import annotations

from lead_intel.config.settings import Settings
from lead_intel.core.exceptions import ConfigurationError
from lead_intel.domain.enums import DataProvider
from lead_intel.providers.base import BusinessProvider
from lead_intel.providers.google_places import GooglePlacesProvider


def create_provider(provider: DataProvider, settings: Settings) -> BusinessProvider:
    """Build a configured provider for ``provider``.

    Raises:
        ConfigurationError: required credentials are missing.
        NotImplementedError: provider not yet implemented (e.g. Apify — Phase 3).
    """
    if provider == DataProvider.GOOGLE_PLACES:
        if not settings.google_places_api_key:
            raise ConfigurationError(
                "GOOGLE_PLACES_API_KEY is not set; cannot use the Google Places provider."
            )
        return GooglePlacesProvider(
            api_key=settings.google_places_api_key,
            max_retries=settings.audit.max_retries,
            timeout_seconds=settings.audit.request_timeout_seconds,
        )

    if provider == DataProvider.APIFY_GMAPS:
        raise NotImplementedError("Apify Google Maps provider is implemented in Phase 3.")

    raise ConfigurationError(f"Unknown data provider: {provider}")
