"""Tests for the end-to-end lead pipeline."""

from __future__ import annotations

import httpx

from lead_intel.ai.service import AIContentService
from lead_intel.audit.engine import WebsiteAuditEngine
from lead_intel.audit.fetcher import PageFetcher
from lead_intel.config.settings import AuditSettings, Settings
from lead_intel.core.exceptions import ProviderError
from lead_intel.domain.enums import DataProvider, Industry
from lead_intel.domain.models import Business, BusinessContact, BusinessRatings
from lead_intel.providers.base import BusinessProvider, SearchQuery
from lead_intel.services.pipeline import LeadPipeline, PipelineConfig, ProgressEvent
from lead_intel.services.scoring_service import ScoringService

MODERN_HTML = '<!doctype html><html><head><meta name="viewport" content="width=device-width">' \
              '</head><body><form><input></form></body></html>'


class FakeProvider(BusinessProvider):
    provider = DataProvider.GOOGLE_PLACES

    def __init__(
        self, by_industry: dict[Industry, list[Business]], *, fail: set[Industry] | None = None
    ):
        self._by_industry = by_industry
        self._fail = fail or set()

    def _fetch(self, query: SearchQuery) -> list[Business]:
        if query.industry in self._fail:
            raise ProviderError("boom", provider="google_places")
        return self._by_industry.get(query.industry, [])


def _biz(name: str, industry: Industry, *, website: str | None = None, rating: float = 4.6,
         reviews: int = 120, area: str = "Baner") -> Business:
    return Business(
        source=DataProvider.GOOGLE_PLACES, source_id=name, name=name, industry=industry,
        area=area, city="Pune", contact=BusinessContact(phone="1", website=website),
        ratings=BusinessRatings(rating=rating, review_count=reviews),
    )


def _pipeline(provider: BusinessProvider) -> LeadPipeline:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    transport = httpx.MockTransport(lambda r: httpx.Response(200, html=MODERN_HTML))
    fetcher = PageFetcher(client=httpx.Client(transport=transport), clock=lambda: 0.0)
    engine = WebsiteAuditEngine(fetcher, settings=AuditSettings(), current_year=2026)
    return LeadPipeline(provider, engine, ScoringService(settings),
                        AIContentService(agency=settings.agency, client=None))


def _config(*categories: Industry) -> PipelineConfig:
    return PipelineConfig(categories=list(categories), max_results_per_category=50)


def test_pipeline_produces_enriched_leads() -> None:
    provider = FakeProvider({
        Industry.GYM: [_biz("No Site Gym", Industry.GYM)],
        Industry.CAFE: [_biz("Modern Cafe", Industry.CAFE, website="https://cafe.example")],
    })
    result = _pipeline(provider).run(_config(Industry.GYM, Industry.CAFE))

    assert len(result.leads) == 2
    assert result.discovered == 2
    for lead in result.leads:
        assert lead.audit is not None
        assert lead.website_score is not None
        assert lead.lead_score is not None
        assert lead.recommendation is not None
        assert lead.ai_content is not None and lead.ai_content.is_populated


def test_pipeline_sorts_by_lead_score_desc() -> None:
    provider = FakeProvider({
        # No-website + strong reputation -> high score; modern low-review -> lower.
        Industry.GYM: [_biz("Hot Lead", Industry.GYM, rating=4.9, reviews=400)],
        Industry.CAFE: [_biz("Cold Lead", Industry.CAFE, website="https://c.example",
                             rating=3.2, reviews=5)],
    })
    result = _pipeline(provider).run(_config(Industry.GYM, Industry.CAFE))
    scores = [lead.lead_score.value for lead in result.leads if lead.lead_score]
    assert scores == sorted(scores, reverse=True)
    assert result.leads[0].business.name == "Hot Lead"


def test_pipeline_deduplicates() -> None:
    dup_a = _biz("Same Place", Industry.GYM, area="Baner")
    dup_b = _biz("Same Place", Industry.GYM, area="Baner")
    provider = FakeProvider({Industry.GYM: [dup_a, dup_b]})
    result = _pipeline(provider).run(_config(Industry.GYM))
    assert result.discovered == 2
    assert result.deduplicated == 1
    assert len(result.leads) == 1


def test_pipeline_survives_provider_failure() -> None:
    provider = FakeProvider(
        {Industry.CAFE: [_biz("Survivor Cafe", Industry.CAFE)]},
        fail={Industry.GYM},
    )
    result = _pipeline(provider).run(_config(Industry.GYM, Industry.CAFE))
    assert len(result.leads) == 1
    assert result.leads[0].business.name == "Survivor Cafe"


def test_pipeline_searches_each_area() -> None:
    calls: list[tuple[Industry, str | None]] = []

    class RecordingProvider(BusinessProvider):
        provider = DataProvider.GOOGLE_PLACES

        def _fetch(self, query: SearchQuery) -> list[Business]:
            calls.append((query.industry, query.area))
            return [_biz(f"{query.industry.value}-{query.area}", query.industry, area=query.area)]

    config = PipelineConfig(categories=[Industry.GYM], areas=["Baner", "Kothrud"])
    result = _pipeline(RecordingProvider()).run(config)

    assert (Industry.GYM, "Baner") in calls
    assert (Industry.GYM, "Kothrud") in calls
    assert result.discovered == 2  # one per area


def test_pipeline_uses_explicit_searches() -> None:
    calls: list[tuple[Industry, str | None]] = []

    class RecordingProvider(BusinessProvider):
        provider = DataProvider.GOOGLE_PLACES

        def _fetch(self, query: SearchQuery) -> list[Business]:
            calls.append((query.industry, query.area))
            return [_biz(f"{query.industry.value}-{query.area}", query.industry, area=query.area)]

    # Explicit list overrides the category×area product: only these two combos run.
    config = PipelineConfig(
        categories=[Industry.GYM, Industry.CAFE],
        areas=["Baner", "Kothrud"],
        searches=[(Industry.GYM, "Baner"), (Industry.CAFE, "Kothrud")],
    )
    result = _pipeline(RecordingProvider()).run(config)

    assert set(calls) == {(Industry.GYM, "Baner"), (Industry.CAFE, "Kothrud")}
    assert result.discovered == 2  # not 4 (would be the full cartesian)


def test_pipeline_emits_progress() -> None:
    provider = FakeProvider({Industry.GYM: [_biz("A Gym", Industry.GYM)]})
    events: list[ProgressEvent] = []
    _pipeline(provider).run(_config(Industry.GYM), on_progress=events.append)
    stages = {e.stage for e in events}
    assert {"discover", "audit", "done"} <= stages
    assert events[-1].stage == "done"
