"""AI content service.

Produces the full :class:`AIContent` bundle for a lead. Two paths behind one API:

* **LLM path** (when an :class:`LLMClient` is supplied): one batch call using the
  centralized prompts, JSON-parsed, with per-field fallback to templates for any
  missing/unparseable value — so a lead is never left with blank content.
* **Template path** (no client): fully deterministic, offline, free.

The service knows nothing about which provider is used — only the interface.
"""

from __future__ import annotations

import json
import re

from lead_intel.ai import assets, prompts, templates
from lead_intel.ai.base import LLMClient
from lead_intel.ai.context import LeadContext, build_context
from lead_intel.config.settings import AgencySettings
from lead_intel.core.exceptions import LeadIntelError
from lead_intel.core.logging import get_logger
from lead_intel.domain.models import AIContent, Lead

logger = get_logger("ai.service")

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class AIContentService:
    """Generates personalized outreach content for a lead."""

    def __init__(self, *, agency: AgencySettings, client: LLMClient | None = None) -> None:
        """
        Args:
            agency: Agency identity woven into the content.
            client: Optional LLM client. When ``None``, deterministic templates
                are used (works offline, no API key).
        """
        self._agency = agency
        self._client = client

    @property
    def uses_llm(self) -> bool:
        return self._client is not None

    def generate(self, lead: Lead) -> AIContent:
        """Return a populated :class:`AIContent` for ``lead``."""
        ctx = build_context(lead, self._agency)
        rendered = self._generate_fields(ctx)
        return self._assemble(rendered)

    # -- field generation --------------------------------------------------

    def _generate_fields(self, ctx: LeadContext) -> dict[str, str]:
        """Produce every asset, LLM-first with template fallback per field."""
        base = templates.render_all(ctx)
        if self._client is None:
            return base

        llm_values = self._try_llm(ctx)
        # Merge: prefer a non-empty LLM value, else keep the template.
        merged = dict(base)
        for key in assets.ASSET_KEYS:
            value = llm_values.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()
        return merged

    def _try_llm(self, ctx: LeadContext) -> dict[str, str]:
        """Call the LLM once and parse a JSON object; empty dict on any failure."""
        try:
            raw = self._client.complete(  # type: ignore[union-attr]
                prompts.SYSTEM_PROMPT, prompts.build_batch_prompt(ctx)
            )
        except LeadIntelError:
            logger.warning("LLM generation failed; using template fallback", exc_info=True)
            return {}

        parsed = _extract_json_object(raw)
        if parsed is None:
            logger.warning("LLM response was not valid JSON; using template fallback")
            return {}
        return {k: v for k, v in parsed.items() if isinstance(v, str)}

    # -- assembly ----------------------------------------------------------

    @staticmethod
    def _assemble(fields: dict[str, str]) -> AIContent:
        return AIContent(
            whatsapp_message=fields[assets.WHATSAPP],
            email=fields[assets.EMAIL],
            cold_call_script=fields[assets.COLD_CALL],
            follow_ups=[fields[key] for key in assets.FOLLOW_UP_KEYS],
            objection_handling=fields[assets.OBJECTION],
            portfolio_response=fields[assets.PORTFOLIO],
            timeline_response=fields[assets.TIMELINE],
            why_choose_us=fields[assets.WHY_US],
        )

    def enrich(self, lead: Lead) -> Lead:
        """Attach generated content to ``lead`` in place and return it."""
        lead.ai_content = self.generate(lead)
        return lead


def _extract_json_object(text: str) -> dict[str, object] | None:
    """Best-effort extraction of the first JSON object from LLM text."""
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
