"""Data provider layer.

Business data sources behind a common interface. Import the interface and
factory from here; concrete providers stay implementation details.
"""

from __future__ import annotations

from lead_intel.providers.apify_gmaps import ApifyGoogleMapsProvider
from lead_intel.providers.base import BusinessProvider, SearchQuery
from lead_intel.providers.factory import create_provider
from lead_intel.providers.google_places import GooglePlacesProvider

__all__ = [
    "BusinessProvider",
    "SearchQuery",
    "create_provider",
    "GooglePlacesProvider",
    "ApifyGoogleMapsProvider",
]
