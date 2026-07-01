"""Anthropic (Claude) LLM client.

Thin adapter over the ``anthropic`` SDK implementing :class:`LLMClient`. The SDK
is imported lazily so the package is only required when this client is actually
used — the default template generation path needs neither the SDK nor a key.
"""

from __future__ import annotations

from lead_intel.ai.base import LLMClient
from lead_intel.core.exceptions import ConfigurationError, LeadIntelError
from lead_intel.core.logging import get_logger

logger = get_logger("ai.anthropic")

_DEFAULT_MODEL = "claude-sonnet-5"
_MAX_TOKENS = 4096


class AnthropicClient(LLMClient):
    """Generates text via Anthropic's Messages API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _MAX_TOKENS,
    ) -> None:
        if not api_key:
            raise ConfigurationError("ANTHROPIC_API_KEY is required for the Anthropic client.")
        self._model = model
        self._max_tokens = max_tokens
        self._client = self._build_client(api_key)

    @staticmethod
    def _build_client(api_key: str) -> object:
        try:
            import anthropic  # noqa: PLC0415 - lazy import keeps the SDK optional
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ConfigurationError(
                "The 'anthropic' package is not installed. Install it with "
                "`pip install lead-intel[ai]` to use the Anthropic client."
            ) from exc
        return anthropic.Anthropic(api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        """Return Claude's completion for the given prompts."""
        try:
            message = self._client.messages.create(  # type: ignore[attr-defined]
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # noqa: BLE001 - normalize any SDK error
            raise LeadIntelError(f"Anthropic request failed: {exc}") from exc

        return self._extract_text(message)

    @staticmethod
    def _extract_text(message: object) -> str:
        """Pull concatenated text from a Messages API response."""
        blocks = getattr(message, "content", None) or []
        parts = [getattr(block, "text", "") for block in blocks]
        text = "".join(parts).strip()
        if not text:
            raise LeadIntelError("Anthropic returned an empty response.")
        return text
