"""Lead pipeline orchestrator.

The end-to-end engine the UI (and any future API) drives: discover businesses →
audit websites → score → generate outreach content → return ranked leads.

Each stage is isolated so one failing business never aborts the run, and a
progress callback lets callers surface live logs / progress bars.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from lead_intel.ai.service import AIContentService
from lead_intel.audit.engine import WebsiteAuditEngine
from lead_intel.config.settings import Settings
from lead_intel.core.logging import get_logger
from lead_intel.domain.enums import Industry
from lead_intel.domain.models import Business, Lead
from lead_intel.providers.base import BusinessProvider, SearchQuery
from lead_intel.services.scoring_service import ScoringService

logger = get_logger("services.pipeline")


@dataclass(frozen=True)
class PipelineConfig:
    """Parameters for one discovery+enrichment run."""

    categories: list[Industry]
    city: str = "Pune"
    state: str = "Maharashtra"
    country: str = "India"
    min_rating: float = 0.0
    min_reviews: int = 0
    max_results_per_category: int = 60


@dataclass(frozen=True)
class ProgressEvent:
    """A single progress update emitted during a run."""

    stage: str          # discover | audit | score | content | done
    message: str
    current: int = 0
    total: int = 0

    @property
    def fraction(self) -> float:
        return (self.current / self.total) if self.total else 0.0


ProgressCallback = Callable[[ProgressEvent], None]


@dataclass
class PipelineResult:
    """Output of a run: ranked leads plus run statistics."""

    leads: list[Lead] = field(default_factory=list)
    discovered: int = 0
    deduplicated: int = 0
    skipped: int = 0


class LeadPipeline:
    """Coordinates provider, audit engine, scoring, and AI content into leads."""

    def __init__(
        self,
        provider: BusinessProvider,
        audit_engine: WebsiteAuditEngine,
        scoring: ScoringService,
        ai: AIContentService,
        *,
        deduplicate: bool = True,
    ) -> None:
        self._provider = provider
        self._audit = audit_engine
        self._scoring = scoring
        self._ai = ai
        self._deduplicate = deduplicate

    def run(
        self, config: PipelineConfig, on_progress: ProgressCallback | None = None
    ) -> PipelineResult:
        """Execute the full pipeline and return ranked leads."""
        emit = on_progress or (lambda _e: None)
        result = PipelineResult()

        businesses = self._discover(config, emit)
        result.discovered = len(businesses)
        if self._deduplicate:
            businesses = self._dedupe(businesses)
        result.deduplicated = len(businesses)

        total = len(businesses)
        for index, business in enumerate(businesses, start=1):
            lead = self._enrich_one(business, index, total, emit)
            if lead is None:
                result.skipped += 1
                continue
            result.leads.append(lead)

        result.leads.sort(key=_lead_sort_key, reverse=True)
        emit(ProgressEvent("done", f"Completed: {len(result.leads)} leads ready.", total, total))
        logger.info(
            "pipeline run complete",
            extra={
                "discovered": result.discovered,
                "deduplicated": result.deduplicated,
                "leads": len(result.leads),
                "skipped": result.skipped,
            },
        )
        return result

    # -- stages ------------------------------------------------------------

    def _discover(self, config: PipelineConfig, emit: ProgressCallback) -> list[Business]:
        found: list[Business] = []
        total = len(config.categories)
        for i, industry in enumerate(config.categories, start=1):
            emit(ProgressEvent("discover", f"Searching {industry.label}…", i, total))
            query = SearchQuery(
                industry=industry,
                city=config.city,
                state=config.state,
                country=config.country,
                min_rating=config.min_rating,
                min_reviews=config.min_reviews,
                max_results=config.max_results_per_category,
            )
            try:
                results = self._provider.search(query)
            except Exception as exc:  # noqa: BLE001 - one category failure must not abort
                logger.warning("discovery failed for %s: %s", industry.label, exc)
                emit(ProgressEvent(
                    "discover", f"Failed to search {industry.label}: {exc}", i, total
                ))
                continue
            emit(ProgressEvent(
                "discover", f"Found {len(results)} {industry.label} businesses.", i, total
            ))
            found.extend(results)
        return found

    @staticmethod
    def _dedupe(businesses: list[Business]) -> list[Business]:
        seen: set[str] = set()
        unique: list[Business] = []
        for business in businesses:
            if business.dedup_key in seen:
                continue
            seen.add(business.dedup_key)
            unique.append(business)
        return unique

    def _enrich_one(
        self, business: Business, index: int, total: int, emit: ProgressCallback
    ) -> Lead | None:
        emit(ProgressEvent("audit", f"Auditing {business.name}…", index, total))
        try:
            audit = self._audit.audit(business)
            lead = Lead(business=business, audit=audit)
            self._scoring.enrich(lead)
            self._ai.enrich(lead)
        except Exception as exc:  # noqa: BLE001 - skip the business, keep the run alive
            logger.exception("failed to enrich %s", business.name)
            emit(ProgressEvent("audit", f"Skipped {business.name}: {exc}", index, total))
            return None
        return lead


def _lead_sort_key(lead: Lead) -> tuple[float, float]:
    """Rank by lead score, then website need (lower website score first)."""
    lead_value = lead.lead_score.value if lead.lead_score else 0.0
    website_gap = 100.0 - (lead.website_score.total if lead.website_score else 0.0)
    return (lead_value, website_gap)


def build_pipeline(settings: Settings, provider: BusinessProvider | None = None) -> LeadPipeline:
    """Wire a pipeline from settings.

    Args:
        settings: Application :class:`Settings`.
        provider: Optional provider override; defaults to the configured one.
    """
    from lead_intel.ai.factory import create_ai_service
    from lead_intel.audit.engine import build_audit_engine
    from lead_intel.providers.factory import create_provider

    resolved_provider = provider or create_provider(settings.default_provider, settings)
    return LeadPipeline(
        provider=resolved_provider,
        audit_engine=build_audit_engine(settings),
        scoring=ScoringService(settings),
        ai=create_ai_service(settings),
    )
