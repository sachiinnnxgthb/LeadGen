"""Deterministic content templates.

The zero-dependency generation path: real, personalized outreach copy built
purely from :class:`LeadContext` — no API key, no network. Also used as the
per-field fallback when an LLM response is missing or unparseable, so a lead is
never left with blank content.

Each function takes a :class:`LeadContext` and returns finished copy.
"""

from __future__ import annotations

from collections.abc import Callable

from lead_intel.ai import assets
from lead_intel.ai.context import LeadContext


def _package_line(ctx: LeadContext) -> str:
    if ctx.package_label and ctx.package_price:
        return f"our {ctx.package_label} package (₹{ctx.package_price:,})"
    return "a package tailored to your needs"


def whatsapp(ctx: LeadContext) -> str:
    return (
        f"Hi {ctx.business_name} team! 👋\n\n"
        f"I came across {ctx.business_name} in {ctx.area} — {ctx.demand_phrase} say a lot "
        f"about the work you do. I noticed {ctx.gap_phrase}, which means potential customers "
        f"searching online may not be finding you.\n\n"
        f"We design fast, modern websites for {ctx.category.lower()} businesses that turn "
        f"Google searches into real enquiries. I'd love to show you a quick mock-up of what "
        f"we'd build for you.\n\n"
        f"Open to a 10-minute chat this week?\n— {ctx.agency_name}"
    )


def email(ctx: LeadContext) -> str:
    return (
        f"Subject: A better website for {ctx.business_name}\n\n"
        f"Hi {ctx.business_name} team,\n\n"
        f"Your {ctx.demand_phrase} show customers love {ctx.business_name}. The one gap I "
        f"spotted: {ctx.gap_phrase}. In {ctx.category.lower()} today, most customers check "
        f"you online before they ever walk in — and a weak web presence quietly sends them "
        f"to competitors.\n\n"
        f"We build conversion-focused websites for local businesses like yours: mobile-first, "
        f"fast, with click-to-call, WhatsApp, enquiry forms, and Google Maps built in. I can "
        f"put together {_package_line(ctx)} and a free mock-up so you can see it before "
        f"deciding anything.\n\n"
        f"Would a short call this week work?\n\n"
        f"Best regards,\n{ctx.agency_name}\n{ctx.agency_phone} | {ctx.agency_email}\n"
        f"{ctx.agency_website}"
    )


def cold_call(ctx: LeadContext) -> str:
    return (
        f"COLD CALL SCRIPT — {ctx.business_name}\n\n"
        f"Opener: \"Hi, am I speaking with someone from {ctx.business_name}? Great — my name "
        f"is [Name] from {ctx.agency_name}. Do you have 30 seconds?\"\n\n"
        f"Hook: \"I was looking at {ctx.business_name} online — {ctx.demand_phrase}, clearly "
        f"customers rate you. I noticed {ctx.gap_phrase}, and I help {ctx.category.lower()} "
        f"businesses fix exactly that.\"\n\n"
        f"Value: \"A modern site would let people find you on Google, tap to call or WhatsApp "
        f"you, and book — all from their phone. Most of our clients see more enquiries within "
        f"weeks.\"\n\n"
        f"Ask: \"Can I send a free mock-up on WhatsApp so you can see what it'd look like? "
        f"What's the best number?\"\n\n"
        f"If interested: propose {_package_line(ctx)} and book a follow-up."
    )


def follow_up_1(ctx: LeadContext) -> str:
    return (
        f"Hi {ctx.business_name} team, just following up on my earlier message about a new "
        f"website. I genuinely think a modern site would help you convert more of the "
        f"customers already searching for {ctx.category.lower()} in {ctx.area}. Want me to "
        f"send over a free mock-up? — {ctx.agency_name}"
    )


def follow_up_2(ctx: LeadContext) -> str:
    return (
        f"Hi again! 😊 I put together some quick ideas for how {ctx.business_name}'s website "
        f"could look — mobile-friendly, with WhatsApp and enquiry buttons built in. No "
        f"obligation at all. Shall I share it? — {ctx.agency_name}"
    )


def follow_up_3(ctx: LeadContext) -> str:
    return (
        f"Hi {ctx.business_name} team — I won't keep messaging 🙂. If growing your online "
        f"enquiries is a priority this quarter, I'd love to help; if not, no worries and all "
        f"the best. Here whenever you're ready. — {ctx.agency_name}, {ctx.agency_phone}"
    )


def objection_handling(ctx: LeadContext) -> str:
    return (
        "OBJECTION HANDLING\n\n"
        f"\"We're too busy / not now\" → \"Totally understand — that's exactly why we handle "
        f"everything end-to-end. You approve the design, we do the rest.\"\n\n"
        f"\"It's expensive\" → \"A website is a one-time investment that works 24/7. "
        f"{_package_line(ctx).capitalize()} pays for itself with just a few extra customers a "
        f"month.\"\n\n"
        f"\"We already have Instagram / JustDial\" → \"Those are great, but you don't own them. "
        f"A proper website ranks on Google, builds trust, and sends enquiries to you.\"\n\n"
        f"\"Maybe later\" → \"Fair enough — can I at least send a free mock-up so it's ready "
        f"when you are?\""
    )


def portfolio_response(ctx: LeadContext) -> str:
    return (
        f"Absolutely! We've built websites for several {ctx.category.lower()} and local "
        f"businesses. I'll send a few examples on WhatsApp so you can see the style, speed, "
        f"and mobile experience. You can also view our recent work at {ctx.agency_website}. "
        f"I'll then tailor a concept specifically for {ctx.business_name}."
    )


def timeline_response(ctx: LeadContext) -> str:
    label = ctx.package_label or "your"
    return (
        f"Great question! For a {label.lower() if ctx.package_label else 'standard'} project we "
        f"typically go live in 1–3 weeks: Week 1 — design & content, Week 2 — build & your "
        f"review, Week 3 — launch. We keep {ctx.business_name} involved at each step, and you "
        f"only approve what you love."
    )


def why_choose_us(ctx: LeadContext) -> str:
    return (
        f"WHY {ctx.agency_name.upper()}?\n\n"
        f"• We specialise in local businesses — we understand {ctx.category.lower()} customers.\n"
        f"• Mobile-first, fast-loading sites built to convert, not just look pretty.\n"
        f"• Click-to-call, WhatsApp, enquiry forms, and Google Maps included.\n"
        f"• Transparent pricing and a free mock-up before you commit.\n"
        f"• Local support — reach us anytime at {ctx.agency_phone}.\n\n"
        f"We'd be proud to help {ctx.business_name} win more customers online."
    )


#: Asset key -> deterministic renderer.
TEMPLATES: dict[str, Callable[[LeadContext], str]] = {
    assets.WHATSAPP: whatsapp,
    assets.EMAIL: email,
    assets.COLD_CALL: cold_call,
    assets.FOLLOW_UP_1: follow_up_1,
    assets.FOLLOW_UP_2: follow_up_2,
    assets.FOLLOW_UP_3: follow_up_3,
    assets.OBJECTION: objection_handling,
    assets.PORTFOLIO: portfolio_response,
    assets.TIMELINE: timeline_response,
    assets.WHY_US: why_choose_us,
}


def render(key: str, ctx: LeadContext) -> str:
    """Render one asset deterministically from ``ctx``."""
    return TEMPLATES[key](ctx)


def render_all(ctx: LeadContext) -> dict[str, str]:
    """Render every asset deterministically."""
    return {key: renderer(ctx) for key, renderer in TEMPLATES.items()}
