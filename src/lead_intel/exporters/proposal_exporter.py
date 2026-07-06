"""Sales proposal PDF generator.

Produces a polished, client-ready website proposal for a single lead: the problem
(grounded in the audit), what we'll build, the investment (recommended package),
timeline, and next steps — branded with the agency's identity. Optionally embeds a
live screenshot of the prospect's current site.
"""

from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from lead_intel.config.settings import AgencySettings, PackageSettings
from lead_intel.core.logging import get_logger
from lead_intel.domain.enums import PackageTier
from lead_intel.domain.models import Lead

logger = get_logger("exporters.proposal")

_NAVY = colors.HexColor("#1F3A5F")
_ACCENT = colors.HexColor("#3A6EA5")
_LIGHT = colors.HexColor("#F2F4F7")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], textColor=_NAVY, fontSize=24),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=12, textColor=colors.grey,
                              alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=_NAVY, spaceBefore=14),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=10.5, leading=16),
        "bullet": ParagraphStyle("bl", parent=base["Normal"], fontSize=10.5, leading=16,
                                 leftIndent=12),
        "price": ParagraphStyle("p", parent=base["Normal"], fontSize=13, textColor=_NAVY),
    }


class ProposalExporter:
    """Renders a single-lead website proposal PDF."""

    def __init__(self, agency: AgencySettings, packages: PackageSettings | None = None) -> None:
        self._agency = agency
        self._packages = packages or PackageSettings()
        self._styles = _styles()

    def export(self, lead: Lead, path: Path, *, screenshot: bytes | None = None) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(path), pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
            leftMargin=1.9 * cm, rightMargin=1.9 * cm,
            title=f"Website Proposal — {lead.business.name}",
        )
        doc.build(self._story(lead, screenshot))
        logger.info("wrote proposal", extra={"path": str(path), "business": lead.business.name})
        return path

    def to_bytes(self, lead: Lead, *, screenshot: bytes | None = None) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
            leftMargin=1.9 * cm, rightMargin=1.9 * cm,
            title=f"Website Proposal — {lead.business.name}",
        )
        doc.build(self._story(lead, screenshot))
        return buffer.getvalue()

    # -- content -----------------------------------------------------------

    def _story(self, lead: Lead, screenshot: bytes | None) -> list[object]:
        s = self._styles
        b = lead.business
        story: list[object] = [
            Paragraph("Website Proposal", s["title"]),
            Paragraph(f"Prepared for {b.name} &nbsp;·&nbsp; by {self._agency.name}", s["sub"]),
            Spacer(1, 0.7 * cm),
            Paragraph(
                f"Dear {b.name} team, thank you for the opportunity. Below is our proposal to "
                f"give {b.name} a modern, high-converting website that turns online searches "
                f"in {b.area or b.city or 'your area'} into real customers.",
                s["body"],
            ),
            Spacer(1, 0.3 * cm),
        ]
        story += self._current_situation(lead, screenshot)
        story += self._what_we_build()
        story += self._investment(lead)
        story += self._timeline_and_next(lead)
        story += self._contact()
        return story

    def _current_situation(self, lead: Lead, screenshot: bytes | None) -> list[object]:
        s = self._styles
        out: list[object] = [Paragraph("Where you are today", s["h2"])]
        problems = lead.audit.problems if lead.audit else []
        if lead.has_no_website:
            out.append(Paragraph(
                "Your business currently has no website, so customers searching online can't "
                "find or evaluate you — and competitors with a web presence win that attention.",
                s["body"]))
        elif problems:
            out.append(Paragraph("We reviewed your current website and found:", s["body"]))
            out += [Paragraph(f"• {p}", s["bullet"]) for p in problems[:6]]
        else:
            out.append(Paragraph(
                "Your current website works, but has clear opportunities to convert more "
                "visitors into enquiries.", s["body"]))

        if screenshot:
            try:
                img = Image(io.BytesIO(screenshot), width=15 * cm, height=9 * cm,
                            kind="proportional")
                out += [Spacer(1, 0.3 * cm), img,
                        Paragraph("Your current website", s["sub"])]
            except Exception:  # noqa: BLE001 - never let a bad image break the PDF
                logger.info("could not embed screenshot")
        out.append(Spacer(1, 0.3 * cm))
        return out

    def _what_we_build(self) -> list[object]:
        s = self._styles
        features = [
            "A fast, mobile-first website that looks great on every phone",
            "Click-to-call, WhatsApp, and enquiry forms so customers reach you instantly",
            "Google Maps, photo gallery, services, and testimonials to build trust",
            "Search-engine basics so you're found on Google",
            "Clear calls-to-action designed to turn visitors into bookings",
        ]
        out: list[object] = [Paragraph("What we'll build", s["h2"])]
        out += [Paragraph(f"• {f}", s["bullet"]) for f in features]
        out.append(Spacer(1, 0.3 * cm))
        return out

    def _investment(self, lead: Lead) -> list[object]:
        rec = lead.recommendation
        rows = [["Package", "Best for", "Investment"]]
        tiers = [
            (PackageTier.STARTER, "A clean, professional presence"),
            (PackageTier.GROWTH, "More pages, SEO, and lead capture"),
            (PackageTier.PREMIUM, "A complete, custom conversion-focused build"),
        ]
        rec_tier = rec.package if rec else PackageTier.GROWTH
        for tier, blurb in tiers:
            label = tier.label + ("  ★ Recommended" if tier == rec_tier else "")
            rows.append([label, blurb, f"₹{self._packages.price_for(tier):,}"])

        table = Table(rows, colWidths=[5.2 * cm, 7.3 * cm, 3.5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return [Paragraph("Your investment", self._styles["h2"]), table, Spacer(1, 0.3 * cm)]

    def _timeline_and_next(self, lead: Lead) -> list[object]:
        s = self._styles
        return [
            Paragraph("Timeline", s["h2"]),
            Paragraph("Most projects go live in <b>1–3 weeks</b>: Week 1 — design &amp; content, "
                      "Week 2 — build &amp; your review, Week 3 — launch.", s["body"]),
            Spacer(1, 0.2 * cm),
            Paragraph("Next steps", s["h2"]),
            Paragraph("Reply to confirm your preferred package and we'll share a free mock-up "
                      "within 48 hours — no obligation. Once you're happy, we begin.", s["body"]),
            Spacer(1, 0.3 * cm),
        ]

    def _contact(self) -> list[object]:
        a = self._agency
        rows = [["Agency", a.name], ["Phone", a.phone], ["Email", a.email], ["Website", a.website]]
        table = Table(rows, colWidths=[4 * cm, 12 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), _ACCENT),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return [Paragraph("Let's talk", self._styles["h2"]), table]
