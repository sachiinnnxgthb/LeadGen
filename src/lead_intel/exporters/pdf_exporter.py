"""PDF website-audit report exporter.

Generates a professional, per-business PDF audit using reportlab's Platypus.
Sections mirror the product brief: business info, current status, problems found,
screenshot placeholder, website score, improvement suggestions, redesign benefits,
recommended package, timeline, and agency contact details.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lead_intel.config.settings import AgencySettings
from lead_intel.core.logging import get_logger
from lead_intel.domain.enums import ScoreDimension
from lead_intel.domain.models import Lead

logger = get_logger("exporters.pdf")

_NAVY = colors.HexColor("#1F3A5F")
_LIGHT = colors.HexColor("#F2F4F7")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], textColor=_NAVY, fontSize=22),
        "subtitle": ParagraphStyle("s", parent=base["Normal"], fontSize=11, textColor=colors.grey,
                                   alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=_NAVY, spaceBefore=12),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=10, leading=15),
        "bullet": ParagraphStyle("bl", parent=base["Normal"], fontSize=10, leading=15,
                                 leftIndent=12),
    }


class PdfAuditExporter:
    """Renders a single-business website audit PDF."""

    def __init__(self, agency: AgencySettings) -> None:
        self._agency = agency
        self._styles = _styles()

    def export(self, lead: Lead, path: Path) -> Path:
        """Write a PDF audit report for ``lead`` to ``path``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(path), pagesize=A4,
            topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
            title=f"Website Audit — {lead.business.name}",
        )
        doc.build(self._story(lead))
        logger.info("wrote PDF audit", extra={"path": str(path), "business": lead.business.name})
        return path

    # -- content -----------------------------------------------------------

    def _story(self, lead: Lead) -> list[object]:
        s = self._styles
        story: list[object] = [
            Paragraph("Website Audit Report", s["title"]),
            Paragraph(f"Prepared by {self._agency.name}", s["subtitle"]),
            Spacer(1, 0.6 * cm),
        ]
        story += self._business_info(lead)
        story += self._status_section(lead)
        story += self._problems_section(lead)
        story += self._screenshot_placeholder()
        story += self._score_section(lead)
        story += self._suggestions_section(lead)
        story += self._benefits_section()
        story += self._package_section(lead)
        story += self._contact_section()
        return story

    def _kv_table(self, rows: list[tuple[str, str]]) -> Table:
        table = Table(rows, colWidths=[5 * cm, 11 * cm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), _LIGHT),
                ("TEXTCOLOR", (0, 0), (0, -1), _NAVY),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        return table

    def _business_info(self, lead: Lead) -> list[object]:
        b = lead.business
        has_rating = b.ratings.rating is not None
        rating = f"{b.ratings.rating}★ ({b.ratings.review_count} reviews)" if has_rating else "—"
        rows = [
            ("Business", b.name),
            ("Category", b.industry.label),
            ("Location", ", ".join(p for p in (b.area, b.city) if p) or "—"),
            ("Phone", b.contact.phone or "—"),
            ("Website", b.contact.website or "No website"),
            ("Reputation", rating),
        ]
        return [Paragraph("Business Information", self._styles["h2"]), self._kv_table(rows),
                Spacer(1, 0.3 * cm)]

    def _status_section(self, lead: Lead) -> list[object]:
        audit = lead.audit
        status = audit.status.value.replace("_", " ").title() if audit else "Not audited"
        quality = lead.website_quality.value.title()
        rows = [("Current Status", status), ("Assessment", quality)]
        if audit and audit.technical.https_enabled is not None:
            rows.append(("HTTPS", "Yes" if audit.technical.https_enabled else "No"))
        return [Paragraph("Current Website Status", self._styles["h2"]), self._kv_table(rows),
                Spacer(1, 0.3 * cm)]

    def _problems_section(self, lead: Lead) -> list[object]:
        s = self._styles
        problems = lead.audit.problems if lead.audit else []
        out: list[object] = [Paragraph("Problems Found", s["h2"])]
        if not problems:
            out.append(Paragraph("No major problems detected.", s["body"]))
        else:
            out += [Paragraph(f"• {p}", s["bullet"]) for p in problems]
        out.append(Spacer(1, 0.3 * cm))
        return out

    def _screenshot_placeholder(self) -> list[object]:
        s = self._styles
        placeholder = Table([[Paragraph("[ Website screenshot placeholder ]", s["subtitle"])]],
                            colWidths=[16 * cm], rowHeights=[3.5 * cm])
        placeholder.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), _LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        return [Paragraph("Screenshot", s["h2"]), placeholder, Spacer(1, 0.3 * cm)]

    def _score_section(self, lead: Lead) -> list[object]:
        s = self._styles
        score = lead.website_score
        out: list[object] = [Paragraph("Website Score", s["h2"])]
        if score is None:
            out.append(Paragraph("Not scored.", s["body"]))
            return out
        rows = [("Overall", f"{score.total:g} / 100")]
        for dim in ScoreDimension:
            sub = score.subscores.get(dim)
            why = score.explanations.get(dim, "")
            label = dim.value.replace("_", " ").title()
            rows.append((label, f"{sub:g}/100 — {why}" if sub is not None else "—"))
        out += [self._kv_table(rows), Spacer(1, 0.3 * cm)]
        return out

    def _suggestions_section(self, lead: Lead) -> list[object]:
        s = self._styles
        suggestions = _improvements(lead)
        out: list[object] = [Paragraph("Improvement Suggestions", s["h2"])]
        out += [Paragraph(f"• {sug}", s["bullet"]) for sug in suggestions]
        out.append(Spacer(1, 0.3 * cm))
        return out

    def _benefits_section(self) -> list[object]:
        s = self._styles
        benefits = [
            "Be found on Google by customers searching for your services.",
            "Convert visitors with click-to-call, WhatsApp, and enquiry forms.",
            "Build trust with a modern, mobile-first design.",
            "Showcase testimonials, gallery, and services professionally.",
        ]
        out: list[object] = [Paragraph("Benefits of a Redesign", s["h2"])]
        out += [Paragraph(f"• {b}", s["bullet"]) for b in benefits]
        out.append(Spacer(1, 0.3 * cm))
        return out

    def _package_section(self, lead: Lead) -> list[object]:
        s = self._styles
        rec = lead.recommendation
        out: list[object] = [Paragraph("Recommended Package & Timeline", s["h2"])]
        if rec is None:
            out.append(Paragraph("To be discussed.", s["body"]))
            return out
        rows = [
            ("Recommended", f"{rec.package.label} (₹{rec.price:,})"),
            ("Why", rec.rationale),
            ("Estimated Timeline", "1–3 weeks (design → build → launch)"),
        ]
        out += [self._kv_table(rows), Spacer(1, 0.3 * cm)]
        return out

    def _contact_section(self) -> list[object]:
        s = self._styles
        a = self._agency
        rows = [
            ("Agency", a.name),
            ("Phone", a.phone),
            ("Email", a.email),
            ("Website", a.website),
        ]
        return [Paragraph("Get in Touch", s["h2"]), self._kv_table(rows)]


def _improvements(lead: Lead) -> list[str]:
    """Derive improvement suggestions from the audit's missing features/problems."""
    if lead.audit is None:
        return ["Commission a professional website to establish an online presence."]
    if lead.has_no_website:
        return [
            "Build a mobile-first website so customers can find and contact you online.",
            "Add click-to-call, WhatsApp, and an enquiry form to capture leads.",
            "List your services, gallery, and testimonials to build trust.",
        ]
    missing = lead.audit.features.missing_features()
    suggestions = [f"Add {feature.lower()} to the website." for feature in missing]
    if lead.audit.technical.is_outdated:
        suggestions.append("Modernise the design and ensure it is mobile-responsive.")
    if lead.audit.technical.appears_slow:
        suggestions.append("Improve page speed to reduce visitor drop-off.")
    return suggestions or ["Refine content and calls-to-action to lift conversions."]
