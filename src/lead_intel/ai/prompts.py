"""Centralized LLM prompts.

Single source of truth for the system prompt and the batch user prompt used to
generate all outreach assets in one call. Keeping every prompt here means the
copy/brand voice can be tuned in one place and reused across any LLM provider.

The batch prompt asks for a single JSON object keyed by :data:`ASSET_KEYS`, which
is cheaper and faster than ten separate calls and easy to parse + fall back on.
"""

from __future__ import annotations

from lead_intel.ai import assets
from lead_intel.ai.context import LeadContext

SYSTEM_PROMPT = (
    "You are an expert B2B sales copywriter for a website design agency in India. "
    "You write warm, concise, non-pushy outreach that sounds human and locally aware. "
    "You use simple English suited to small local business owners, occasional light emoji "
    "in chat channels only, and never make false claims. Prices are in Indian Rupees (₹). "
    "Always return exactly the requested JSON — no preamble, no markdown fences."
)

_KEY_INSTRUCTIONS = {
    assets.WHATSAPP: "A short, friendly WhatsApp message (max ~90 words) with a soft CTA.",
    assets.EMAIL: "A cold email with a 'Subject:' line then body; professional but warm.",
    assets.COLD_CALL: "A cold-call script with Opener, Hook, Value, and Ask sections.",
    assets.FOLLOW_UP_1: "A brief first follow-up message (gentle nudge).",
    assets.FOLLOW_UP_2: "A second follow-up offering a free mock-up.",
    assets.FOLLOW_UP_3: "A final, no-pressure follow-up that leaves the door open.",
    assets.OBJECTION: "Objection-handling responses to 3-4 common objections.",
    assets.PORTFOLIO: "A reply to 'can we see your portfolio?'.",
    assets.TIMELINE: "A reply to 'how long will it take?' with a realistic timeline.",
    assets.WHY_US: "A persuasive 'why choose us?' answer as short bullet points.",
}


def build_batch_prompt(ctx: LeadContext) -> str:
    """Build the single user prompt that requests all assets as JSON."""
    facts = _facts_block(ctx)
    keys_spec = "\n".join(f'  "{key}": {desc}' for key, desc in _KEY_INSTRUCTIONS.items())
    return (
        f"Write personalized sales outreach for this prospect.\n\n"
        f"PROSPECT FACTS:\n{facts}\n\n"
        f"Return a single JSON object with EXACTLY these keys (all string values):\n"
        f"{{\n{keys_spec}\n}}\n\n"
        f"Personalize using the business name, category, area, and reputation. "
        f"Reference the specific web gap. Keep the agency's name and contact details accurate."
    )


def _facts_block(ctx: LeadContext) -> str:
    lines = [
        f"- Business: {ctx.business_name}",
        f"- Category: {ctx.category}",
        f"- Area: {ctx.area}, {ctx.city}".rstrip(", "),
        f"- Reputation: {ctx.demand_phrase}",
        f"- Web situation: {ctx.gap_phrase}",
    ]
    if ctx.missing_features:
        lines.append(f"- Missing website features: {', '.join(ctx.missing_features)}")
    if ctx.package_label and ctx.package_price:
        lines.append(f"- Recommended package: {ctx.package_label} (₹{ctx.package_price:,})")
    lines.extend(
        [
            f"- Agency name: {ctx.agency_name}",
            f"- Agency phone: {ctx.agency_phone}",
            f"- Agency email: {ctx.agency_email}",
            f"- Agency website: {ctx.agency_website}",
        ]
    )
    return "\n".join(lines)
