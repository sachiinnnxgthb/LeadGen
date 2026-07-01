"""Tests for the AI content layer (templates + LLM path + factory)."""

from __future__ import annotations

import json

import pytest

from lead_intel.ai import assets, templates
from lead_intel.ai.base import LLMClient
from lead_intel.ai.context import build_context
from lead_intel.ai.factory import create_ai_service, create_llm_client
from lead_intel.ai.service import AIContentService, _extract_json_object
from lead_intel.config.settings import Settings
from lead_intel.core.exceptions import ConfigurationError, LeadIntelError
from lead_intel.domain.enums import DataProvider, Industry, LeadPriority, PackageTier
from lead_intel.domain.models import (
    Business,
    BusinessContact,
    BusinessRatings,
    Lead,
    LeadScore,
    SalesRecommendation,
    WebsiteAudit,
)


def _settings(**kw: object) -> Settings:
    return Settings(_env_file=None, **kw)  # type: ignore[arg-type]


def _lead() -> Lead:
    business = Business(
        source=DataProvider.GOOGLE_PLACES,
        source_id="1",
        name="IronCore Gym",
        industry=Industry.GYM,
        area="Baner",
        city="Pune",
        contact=BusinessContact(phone="+91 98765 43210"),
        ratings=BusinessRatings(rating=4.8, review_count=320),
    )
    return Lead(
        business=business,
        audit=WebsiteAudit.no_website(),
        lead_score=LeadScore(value=10.0, priority=LeadPriority.HIGH),
        recommendation=SalesRecommendation(
            package=PackageTier.PREMIUM, price=14999, rationale="…"
        ),
    )


class _FakeLLM(LLMClient):
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self.response


class _BoomLLM(LLMClient):
    def complete(self, system: str, user: str) -> str:
        raise LeadIntelError("provider down")


# -- context ---------------------------------------------------------------


def test_context_captures_lead_and_agency() -> None:
    ctx = build_context(_lead(), _settings().agency)
    assert ctx.business_name == "IronCore Gym"
    assert ctx.category == "Gym"
    assert ctx.area == "Baner"
    assert "doesn't have a website" in ctx.gap_phrase
    assert "4.8" in ctx.demand_phrase


# -- templates -------------------------------------------------------------


def test_render_all_produces_every_asset() -> None:
    ctx = build_context(_lead(), _settings().agency)
    rendered = templates.render_all(ctx)
    assert set(rendered) == set(assets.ASSET_KEYS)
    assert all(text.strip() for text in rendered.values())
    # Personalized: the business name appears across the copy.
    assert all("IronCore Gym" in rendered[k] for k in (assets.WHATSAPP, assets.EMAIL))


# -- service: template mode ------------------------------------------------


def test_template_mode_populates_content() -> None:
    service = AIContentService(agency=_settings().agency, client=None)
    assert service.uses_llm is False
    content = service.generate(_lead())
    assert content.is_populated is True
    assert len(content.follow_ups) == 3
    assert "IronCore Gym" in content.whatsapp_message


def test_enrich_attaches_content() -> None:
    service = AIContentService(agency=_settings().agency, client=None)
    lead = service.enrich(_lead())
    assert lead.ai_content is not None
    assert lead.ai_content.is_populated


# -- service: LLM mode -----------------------------------------------------


def test_llm_values_are_used_when_valid() -> None:
    payload = {key: f"LLM-{key}" for key in assets.ASSET_KEYS}
    client = _FakeLLM(json.dumps(payload))
    service = AIContentService(agency=_settings().agency, client=client)

    content = service.generate(_lead())
    assert service.uses_llm is True
    assert client.calls == 1  # single batch call
    assert content.whatsapp_message == "LLM-whatsapp_message"
    assert content.follow_ups[0] == "LLM-follow_up_1"


def test_llm_json_with_prose_around_it_is_parsed() -> None:
    payload = {key: f"X-{key}" for key in assets.ASSET_KEYS}
    client = _FakeLLM(f"Here you go:\n{json.dumps(payload)}\nHope that helps!")
    content = AIContentService(agency=_settings().agency, client=client).generate(_lead())
    assert content.email == "X-email"


def test_partial_llm_response_falls_back_per_field() -> None:
    client = _FakeLLM(json.dumps({assets.WHATSAPP: "LLM wa only"}))
    content = AIContentService(agency=_settings().agency, client=client).generate(_lead())
    assert content.whatsapp_message == "LLM wa only"       # from LLM
    assert "IronCore Gym" in content.email                  # fell back to template


def test_garbage_llm_response_falls_back_to_templates() -> None:
    client = _FakeLLM("not json at all")
    content = AIContentService(agency=_settings().agency, client=client).generate(_lead())
    assert content.is_populated
    assert "IronCore Gym" in content.whatsapp_message


def test_llm_error_falls_back_to_templates() -> None:
    service = AIContentService(agency=_settings().agency, client=_BoomLLM())
    content = service.generate(_lead())
    assert content.is_populated  # audit still produced content


# -- json extraction -------------------------------------------------------


def test_extract_json_object_variants() -> None:
    assert _extract_json_object('{"a": "b"}') == {"a": "b"}
    assert _extract_json_object('prefix {"a": 1} suffix') == {"a": 1}
    assert _extract_json_object("no json") is None
    assert _extract_json_object("[1, 2, 3]") is None  # not an object


# -- factory ---------------------------------------------------------------


def test_factory_no_provider_returns_none_client() -> None:
    assert create_llm_client(_settings(llm_provider="none")) is None


def test_factory_anthropic_without_key_returns_none() -> None:
    assert create_llm_client(_settings(llm_provider="anthropic", anthropic_api_key="")) is None


def test_factory_unknown_provider_returns_none() -> None:
    assert create_llm_client(_settings(llm_provider="banana")) is None


def test_create_ai_service_defaults_to_template_mode() -> None:
    service = create_ai_service(_settings(llm_provider="none"))
    assert service.uses_llm is False


def test_anthropic_client_requires_key() -> None:
    from lead_intel.ai.anthropic_client import AnthropicClient

    with pytest.raises(ConfigurationError):
        AnthropicClient(api_key="")
