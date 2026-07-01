"""Application configuration.

Typed, validated settings loaded from environment variables / ``.env`` using
pydantic-settings. Grouped into nested models (search, audit, scoring, packages,
agency, ...) that are addressed with a ``__`` delimiter, e.g.
``LEAD_SCORE__NO_WEBSITE=4``.

Access the singleton via :func:`get_settings` — it is cached so the ``.env`` file
is parsed once per process.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from lead_intel.domain.enums import DataProvider, PackageTier, ScoreDimension


class SearchSettings(BaseModel):
    """Defaults for business discovery queries."""

    city: str = "Pune"
    state: str = "Maharashtra"
    country: str = "India"
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    min_reviews: int = Field(default=0, ge=0)
    max_results_per_category: int = Field(default=60, ge=1, le=500)


class AuditSettings(BaseModel):
    """Website audit thresholds and networking limits."""

    request_timeout_seconds: int = Field(default=15, ge=1, le=120)
    slow_response_ms: int = Field(default=3000, ge=100)
    max_retries: int = Field(default=2, ge=0, le=10)


class LeadScoreSettings(BaseModel):
    """Configurable weights and thresholds for the 0-10 lead score."""

    no_website: int = 4
    broken_website: int = 3
    outdated_website: int = 2
    rating_gt_threshold: int = 2
    reviews_gt_threshold: int = 2
    has_instagram: int = 1
    has_phone: int = 1

    rating_threshold: float = Field(default=4.5, ge=0.0, le=5.0)
    reviews_threshold: int = Field(default=100, ge=0)

    high_priority_min: int = Field(default=7, ge=0, le=10)
    medium_priority_min: int = Field(default=4, ge=0, le=10)

    @model_validator(mode="after")
    def _check_thresholds(self) -> LeadScoreSettings:
        if self.medium_priority_min > self.high_priority_min:
            raise ValueError(
                "medium_priority_min must be <= high_priority_min"
            )
        return self


class WebsiteScoreSettings(BaseModel):
    """Sub-dimension weights for the 0-100 website score (must sum to 1.0)."""

    performance: float = Field(default=0.25, ge=0.0, le=1.0)
    mobile: float = Field(default=0.20, ge=0.0, le=1.0)
    trust: float = Field(default=0.20, ge=0.0, le=1.0)
    seo: float = Field(default=0.15, ge=0.0, le=1.0)
    user_experience: float = Field(default=0.20, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> WebsiteScoreSettings:
        total = self.performance + self.mobile + self.trust + self.seo + self.user_experience
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Website score weights must sum to 1.0 (got {total:.4f})")
        return self

    def as_dimension_map(self) -> dict[ScoreDimension, float]:
        """Expose weights keyed by :class:`ScoreDimension` for the scoring service."""
        return {
            ScoreDimension.PERFORMANCE: self.performance,
            ScoreDimension.MOBILE: self.mobile,
            ScoreDimension.TRUST: self.trust,
            ScoreDimension.SEO: self.seo,
            ScoreDimension.USER_EXPERIENCE: self.user_experience,
        }


class PackageSettings(BaseModel):
    """Package pricing in INR."""

    starter_price: int = Field(default=4999, ge=0)
    growth_price: int = Field(default=8999, ge=0)
    premium_price: int = Field(default=14999, ge=0)

    def price_for(self, tier: PackageTier) -> int:
        return {
            PackageTier.STARTER: self.starter_price,
            PackageTier.GROWTH: self.growth_price,
            PackageTier.PREMIUM: self.premium_price,
        }[tier]


class RevenueSettings(BaseModel):
    """Assumptions for the dashboard revenue projection."""

    conversion_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    avg_deal_value: int = Field(default=8999, ge=0)


class AgencySettings(BaseModel):
    """Agency identity used in outreach and PDF reports."""

    name: str = "Your Agency Name"
    phone: str = "+91-0000000000"
    email: str = "hello@youragency.com"
    website: str = "https://youragency.com"


class Settings(BaseSettings):
    """Root application settings.

    Reads from process environment and a ``.env`` file. Unknown keys are ignored
    so the same file can carry future settings without breaking older code.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False
    output_dir: str = "./output"

    default_provider: DataProvider = DataProvider.GOOGLE_PLACES
    google_places_api_key: str = ""
    apify_api_token: str = ""

    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    search: SearchSettings = Field(default_factory=SearchSettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)
    lead_score: LeadScoreSettings = Field(default_factory=LeadScoreSettings)
    website_score: WebsiteScoreSettings = Field(default_factory=WebsiteScoreSettings)
    package: PackageSettings = Field(default_factory=PackageSettings)
    revenue: RevenueSettings = Field(default_factory=RevenueSettings)
    agency: AgencySettings = Field(default_factory=AgencySettings)

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return upper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached, process-wide settings instance."""
    return Settings()
