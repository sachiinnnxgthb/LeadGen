"""AI service factory.

Wires an :class:`AIContentService` from settings, choosing an LLM client only
when a provider and key are configured. Falls back silently to the deterministic
template path otherwise, so the platform always produces content.
"""

from __future__ import annotations

from lead_intel.ai.base import LLMClient
from lead_intel.ai.service import AIContentService
from lead_intel.config.settings import Settings
from lead_intel.core.logging import get_logger

logger = get_logger("ai.factory")


def create_llm_client(settings: Settings) -> LLMClient | None:
    """Return a configured LLM client, or ``None`` to use template generation."""
    provider = settings.llm_provider.lower()
    if provider in ("", "none"):
        return None

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            logger.info("LLM provider is 'anthropic' but no API key set; using templates.")
            return None
        from lead_intel.ai.anthropic_client import AnthropicClient

        return AnthropicClient(settings.anthropic_api_key, model=settings.llm_model)

    logger.warning("Unknown LLM provider '%s'; using templates.", provider)
    return None


def create_ai_service(settings: Settings) -> AIContentService:
    """Build an :class:`AIContentService` from settings."""
    return AIContentService(agency=settings.agency, client=create_llm_client(settings))
