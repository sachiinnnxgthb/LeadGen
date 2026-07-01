"""Business domain model.

The canonical, provider-agnostic representation of a discovered business.
Every data provider (Google Places, Apify, future sources) maps its raw payload
onto this shape so that the rest of the pipeline never depends on a vendor's
schema.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lead_intel.domain.enums import DataProvider, Industry


class GeoLocation(BaseModel):
    """A latitude/longitude coordinate pair."""

    model_config = ConfigDict(frozen=True)

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class BusinessContact(BaseModel):
    """Contact and online-presence channels for a business.

    All fields are optional: providers rarely return a complete set, and
    absence is itself a signal used by lead scoring.
    """

    phone: str | None = None
    website: str | None = None
    email: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    whatsapp: str | None = None

    @field_validator("website", mode="before")
    @classmethod
    def _normalize_website(cls, value: str | None) -> str | None:
        """Trim, drop empty strings, and ensure a scheme is present."""
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
            cleaned = f"https://{cleaned}"
        return cleaned

    @property
    def has_website(self) -> bool:
        return bool(self.website)

    @property
    def has_phone(self) -> bool:
        return bool(self.phone)

    @property
    def has_instagram(self) -> bool:
        return bool(self.instagram)


class BusinessRatings(BaseModel):
    """Aggregate review signals from the source platform."""

    rating: float | None = Field(default=None, ge=0.0, le=5.0)
    review_count: int = Field(default=0, ge=0)


class Business(BaseModel):
    """A single discovered business — the pipeline's primary input entity.

    Identity is keyed by ``source_id`` (the provider's stable id). A separate
    ``dedup_key`` is exposed for cross-provider de-duplication by name + area.
    """

    model_config = ConfigDict(extra="ignore")

    source: DataProvider
    source_id: str = Field(..., min_length=1)

    name: str = Field(..., min_length=1)
    industry: Industry = Industry.OTHER
    raw_category: str | None = Field(
        default=None,
        description="Provider's original category label, kept for traceability.",
    )

    area: str | None = Field(default=None, description="Locality / neighbourhood")
    address: str | None = None
    city: str | None = None
    location: GeoLocation | None = None

    contact: BusinessContact = Field(default_factory=BusinessContact)
    ratings: BusinessRatings = Field(default_factory=BusinessRatings)

    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="Untouched provider payload for debugging / re-mapping.",
    )

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Business name cannot be blank")
        return cleaned

    @property
    def dedup_key(self) -> str:
        """Provider-independent key for de-duplication.

        Normalizes the name (lowercased, alphanumerics only) and appends the
        lowercased area so the same shop from two providers collapses to one.
        """
        name_slug = re.sub(r"[^a-z0-9]+", "", self.name.lower())
        area_slug = (self.area or "").strip().lower()
        return f"{name_slug}|{area_slug}"

    @property
    def has_website(self) -> bool:
        return self.contact.has_website
