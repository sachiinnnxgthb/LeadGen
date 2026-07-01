"""Configuration layer: typed, validated settings loaded from the environment."""

from __future__ import annotations

from lead_intel.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
