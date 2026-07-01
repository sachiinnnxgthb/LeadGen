"""AI content layer.

Generates personalized sales outreach for each lead. Centralized prompts drive
either an optional LLM (Claude) or a deterministic template generator that needs
no API key. Both paths sit behind :class:`AIContentService`.
"""

from __future__ import annotations

from lead_intel.ai.base import LLMClient
from lead_intel.ai.context import LeadContext, build_context
from lead_intel.ai.factory import create_ai_service, create_llm_client
from lead_intel.ai.service import AIContentService

__all__ = [
    "LLMClient",
    "LeadContext",
    "build_context",
    "AIContentService",
    "create_ai_service",
    "create_llm_client",
]
