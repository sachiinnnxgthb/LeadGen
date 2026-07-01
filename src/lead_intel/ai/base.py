"""LLM client abstraction.

A minimal, provider-agnostic text-completion interface. The AI content service
depends only on this, so any provider (Anthropic today; OpenAI, local models
later) can be dropped in without touching prompt or service code.
"""

from __future__ import annotations

import abc


class LLMClient(abc.ABC):
    """Provider-agnostic single-turn text completion."""

    @abc.abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the model's text completion for a system + user prompt.

        Raises:
            LeadIntelError: on unrecoverable provider/config failures.
        """
        raise NotImplementedError
