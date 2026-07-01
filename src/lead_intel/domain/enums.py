"""Domain enumerations.

Central, provider-agnostic vocabulary for the whole platform. Every layer
(providers, audit, scoring, exporters, UI) references these instead of raw
strings so that values stay consistent and refactor-safe.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String-valued enum (portable to Python 3.9, which lacks ``enum.StrEnum``).

    Members compare equal to their string value, serialize cleanly via Pydantic,
    and render as the value in f-strings.
    """

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class Industry(StrEnum):
    """Target business categories the agency sells websites to.

    Values are stable machine keys; human labels live in ``label``.
    New industries can be appended without breaking stored data.
    """

    GYM = "gym"
    CAFE = "cafe"
    RESTAURANT = "restaurant"
    DENTAL_CLINIC = "dental_clinic"
    CLINIC = "clinic"
    PHYSIOTHERAPY = "physiotherapy"
    SALON = "salon"
    SPA = "spa"
    COACHING_CLASS = "coaching_class"
    TUITION_CENTRE = "tuition_centre"
    BOUTIQUE = "boutique"
    YOGA_STUDIO = "yoga_studio"
    DANCE_ACADEMY = "dance_academy"
    MUSIC_ACADEMY = "music_academy"
    ARCHITECT = "architect"
    INTERIOR_DESIGNER = "interior_designer"
    PET_GROOMER = "pet_groomer"
    VETERINARY_CLINIC = "veterinary_clinic"
    CAR_WASH = "car_wash"
    CAR_DETAILING = "car_detailing"
    CLEANING_SERVICE = "cleaning_service"
    PEST_CONTROL = "pest_control"
    PACKERS_MOVERS = "packers_movers"
    BEAUTY_PARLOUR = "beauty_parlour"
    LOCAL_SERVICE = "local_service"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Human-friendly title, e.g. ``dental_clinic`` -> ``Dental Clinic``."""
        return self.value.replace("_", " ").title()


class DataProvider(StrEnum):
    """Supported business-data sources behind the provider interface."""

    GOOGLE_PLACES = "google_places"
    APIFY_GMAPS = "apify_gmaps"


class WebsiteStatus(StrEnum):
    """Outcome of probing a business's website."""

    NO_WEBSITE = "no_website"      # business has no website listed
    LIVE = "live"                  # reachable, 2xx
    REDIRECTED = "redirected"      # reachable but redirects away from listed URL
    BROKEN = "broken"              # 4xx/5xx or DNS/connection failure
    INACCESSIBLE = "inaccessible"  # timeout / TLS error / unreachable
    UNKNOWN = "unknown"            # not yet audited


class WebsiteQuality(StrEnum):
    """High-level quality bucket derived from the audit + website score."""

    NONE = "none"          # no website at all
    BROKEN = "broken"      # exists but broken/inaccessible
    OUTDATED = "outdated"  # works but old / low score
    MODERN = "modern"      # works and scores well


class LeadPriority(StrEnum):
    """Sales priority bucket derived from the lead score."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PackageTier(StrEnum):
    """Recommended sales package."""

    STARTER = "starter"
    GROWTH = "growth"
    PREMIUM = "premium"


class ContactStatus(StrEnum):
    """CRM outreach state for a lead."""

    NOT_CONTACTED = "not_contacted"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ScoreDimension(StrEnum):
    """Sub-dimensions that compose the 0-100 website score."""

    PERFORMANCE = "performance"
    MOBILE = "mobile"
    TRUST = "trust"
    SEO = "seo"
    USER_EXPERIENCE = "user_experience"
