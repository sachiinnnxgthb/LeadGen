"""Instant website mockup generator.

Produces a complete, good-looking, responsive single-page website preview for a
business — using its real name, category, area, and rating. This is the agency's
strongest closing tool: the prospect *sees their own future site*.

Output is a fully self-contained HTML string (inline CSS, no external assets) so
it renders inside the app, downloads as one file, and can be sent to the business.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from lead_intel.config.settings import AgencySettings
from lead_intel.domain.models import Lead
from lead_intel.ui.formatting import whatsapp_link


@dataclass(frozen=True)
class _Theme:
    tagline: str
    services: list[tuple[str, str, str]]  # (emoji, title, blurb)


# Category-specific copy so each mockup feels tailored, with a sensible fallback.
_THEMES: dict[str, _Theme] = {
    "Gym": _Theme("Stronger every day — your fitness journey starts here", [
        ("🏋️", "Modern Equipment", "State-of-the-art machines and free weights."),
        ("🧑‍🏫", "Expert Trainers", "Certified coaches to guide every workout."),
        ("📅", "Flexible Memberships", "Plans that fit your schedule and goals."),
    ]),
    "Cafe": _Theme("Great coffee, warm vibes, unforgettable moments", [
        ("☕", "Freshly Brewed", "Specialty coffee roasted to perfection."),
        ("🍰", "Fresh Bakes", "Cakes, pastries, and snacks made daily."),
        ("🎶", "Cozy Ambience", "The perfect spot to relax or work."),
    ]),
    "Restaurant": _Theme("Delicious food, memorable dining", [
        ("🍽️", "Signature Dishes", "Crafted by our expert chefs."),
        ("🥗", "Fresh Ingredients", "Locally sourced, always fresh."),
        ("🚚", "Dine-in & Delivery", "Enjoy at home or with us."),
    ]),
    "Dental Clinic": _Theme("Healthy smiles, gentle care", [
        ("🦷", "Complete Dentistry", "From cleanings to advanced treatments."),
        ("😁", "Painless Care", "Comfortable, modern procedures."),
        ("📆", "Easy Appointments", "Book online in seconds."),
    ]),
    "Salon": _Theme("Look good, feel amazing", [
        ("💇", "Expert Styling", "Cuts, colour, and care by pros."),
        ("💅", "Beauty Services", "Skin, nails, and grooming."),
        ("✨", "Premium Products", "Only the best for your look."),
    ]),
    "Spa": _Theme("Relax, rejuvenate, restore", [
        ("💆", "Signature Therapies", "Massages and treatments to unwind."),
        ("🌸", "Serene Space", "A calm escape from the everyday."),
        ("🧖", "Wellness Packages", "Tailored to how you feel."),
    ]),
}

_FALLBACK = _Theme("Quality service you can trust", [
    ("⭐", "Trusted Service", "Loved by customers across the area."),
    ("💬", "Easy to Reach", "Call or WhatsApp us anytime."),
    ("📍", "Conveniently Located", "Right in your neighbourhood."),
])


def build_mockup_html(lead: Lead, agency: AgencySettings) -> str:
    """Return a self-contained HTML mockup website for the lead's business."""
    b = lead.business
    theme = _THEMES.get(b.industry.label, _FALLBACK)
    name = html.escape(b.name)
    category = html.escape(b.industry.label)
    area = html.escape(b.area or b.city or "your city")
    phone = html.escape(b.contact.phone or agency.phone)
    rating = b.ratings.rating
    reviews = b.ratings.review_count
    wa = whatsapp_link(b.contact.phone) or "#"

    rating_line = (
        f"★ {rating} rated by {reviews}+ happy customers" if rating else "Loved by our customers"
    )
    services_html = "".join(
        f'<div class="card"><div class="ico">{emoji}</div>'
        f"<h3>{html.escape(title)}</h3><p>{html.escape(blurb)}</p></div>"
        for emoji, title, blurb in theme.services
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; font-family:-apple-system,Segoe UI,Roboto,sans-serif; }}
  body {{ color:#1a2230; line-height:1.6; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 20px; }}
  header {{ background:#0e1b2e; color:#fff; padding:16px 0; position:sticky; top:0; z-index:10; }}
  header .wrap {{ display:flex; justify-content:space-between; align-items:center; }}
  .logo {{ font-weight:800; font-size:1.3rem; }}
  .nav a {{ color:#cfd8e6; text-decoration:none; margin-left:20px; font-size:.95rem; }}
  .hero {{ background:linear-gradient(135deg,#0e1b2e,#26456e); color:#fff; padding:90px 0; text-align:center; }}
  .hero h1 {{ font-size:2.6rem; margin-bottom:14px; }}
  .hero p {{ font-size:1.15rem; opacity:.92; max-width:640px; margin:0 auto 26px; }}
  .btns a {{ display:inline-block; padding:14px 26px; border-radius:10px; font-weight:700;
             text-decoration:none; margin:6px; }}
  .btn-primary {{ background:#22c55e; color:#fff; }}
  .btn-ghost {{ background:rgba(255,255,255,.15); color:#fff; border:1px solid rgba(255,255,255,.4); }}
  .stats {{ background:#f5f7fb; padding:18px 0; text-align:center; font-weight:600; color:#26456e; }}
  section {{ padding:64px 0; }}
  h2 {{ text-align:center; font-size:2rem; margin-bottom:8px; color:#0e1b2e; }}
  .sub {{ text-align:center; color:#6b7688; margin-bottom:40px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:22px; }}
  .card {{ background:#fff; border:1px solid #e6eaf0; border-radius:16px; padding:28px; text-align:center;
           box-shadow:0 6px 20px rgba(20,40,80,.05); }}
  .ico {{ font-size:2.4rem; margin-bottom:12px; }}
  .card h3 {{ margin-bottom:8px; color:#0e1b2e; }}
  .card p {{ color:#6b7688; font-size:.96rem; }}
  .gallery {{ background:#f5f7fb; }}
  .gimg {{ background:linear-gradient(135deg,#dfe6f2,#c7d3e8); border-radius:14px; height:150px;
           display:flex; align-items:center; justify-content:center; color:#5f7396; }}
  .cta {{ background:#0e1b2e; color:#fff; text-align:center; }}
  .cta h2 {{ color:#fff; }}
  footer {{ background:#08111d; color:#9fb0c8; text-align:center; padding:26px 0; font-size:.9rem; }}
  footer a {{ color:#8fd0ff; text-decoration:none; }}
  @media(max-width:640px){{ .hero h1{{font-size:1.9rem;}} .nav{{display:none;}} }}
</style></head>
<body>
<header><div class="wrap"><div class="logo">{name}</div>
  <nav class="nav"><a href="#services">Services</a><a href="#gallery">Gallery</a>
  <a href="#contact">Contact</a></nav></div></header>

<div class="hero"><div class="wrap">
  <h1>{name}</h1>
  <p>{html.escape(theme.tagline)} — proudly serving {area}.</p>
  <div class="btns">
    <a class="btn-primary" href="{wa}">💬 WhatsApp Us</a>
    <a class="btn-ghost" href="tel:{phone}">📞 Call {phone}</a>
  </div>
</div></div>

<div class="stats"><div class="wrap">{html.escape(rating_line)} &nbsp;·&nbsp; {category} in {area}</div></div>

<section id="services"><div class="wrap">
  <h2>What We Offer</h2><p class="sub">Everything {name} does best</p>
  <div class="grid">{services_html}</div>
</div></section>

<section id="gallery" class="gallery"><div class="wrap">
  <h2>Gallery</h2><p class="sub">A glimpse of {name}</p>
  <div class="grid">
    <div class="gimg">Your photo here</div>
    <div class="gimg">Your photo here</div>
    <div class="gimg">Your photo here</div>
  </div>
</div></section>

<section id="contact"><div class="wrap" style="text-align:center">
  <h2>Visit or Contact Us</h2>
  <p class="sub">We'd love to hear from you</p>
  <p style="font-size:1.1rem"><strong>📍 {area}</strong><br>📞 {phone}</p>
  <div class="btns" style="margin-top:18px">
    <a class="btn-primary" href="{wa}">💬 Message on WhatsApp</a>
  </div>
</div></section>

<section class="cta"><div class="wrap">
  <h2>Ready to get started?</h2>
  <p class="sub" style="color:#b9c6db">Book your visit today.</p>
  <div class="btns"><a class="btn-primary" href="tel:{phone}">📞 Call Now</a></div>
</div></section>

<footer><div class="wrap">
  Website preview crafted by <strong>{html.escape(agency.name)}</strong> — like it? Let's build it for real.<br>
  <a href="tel:{html.escape(agency.phone)}">{html.escape(agency.phone)}</a> ·
  <a href="mailto:{html.escape(agency.email)}">{html.escape(agency.email)}</a> ·
  <a href="{html.escape(agency.website)}">{html.escape(agency.website)}</a>
</div></footer>
</body></html>"""
