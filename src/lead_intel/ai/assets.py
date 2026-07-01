"""Canonical outreach asset keys.

Shared by the prompt library, the template generator, and the service so all
three agree on exactly which pieces of content exist and how they map onto the
:class:`~lead_intel.domain.models.AIContent` model.
"""

from __future__ import annotations

WHATSAPP = "whatsapp_message"
EMAIL = "email"
COLD_CALL = "cold_call_script"
FOLLOW_UP_1 = "follow_up_1"
FOLLOW_UP_2 = "follow_up_2"
FOLLOW_UP_3 = "follow_up_3"
OBJECTION = "objection_handling"
PORTFOLIO = "portfolio_response"
TIMELINE = "timeline_response"
WHY_US = "why_choose_us"

#: All asset keys, in a stable order.
ASSET_KEYS: tuple[str, ...] = (
    WHATSAPP,
    EMAIL,
    COLD_CALL,
    FOLLOW_UP_1,
    FOLLOW_UP_2,
    FOLLOW_UP_3,
    OBJECTION,
    PORTFOLIO,
    TIMELINE,
    WHY_US,
)

#: Follow-up keys in sequence order (assembled into ``AIContent.follow_ups``).
FOLLOW_UP_KEYS: tuple[str, ...] = (FOLLOW_UP_1, FOLLOW_UP_2, FOLLOW_UP_3)
