"""Flat lead → row mapping.

The single definition of the CRM columns and how a :class:`Lead` maps onto them.
Shared by the Excel and CSV exporters so both always agree on column set, order,
and formatting.
"""

from __future__ import annotations

from dataclasses import dataclass

from lead_intel.domain.enums import ContactStatus
from lead_intel.domain.models import Lead

# Column order exactly as specified by the product brief.
COLUMNS: tuple[str, ...] = (
    "Business Name",
    "Category",
    "Area",
    "Address",
    "Phone",
    "Website",
    "Website Status",
    "Instagram",
    "Google Rating",
    "Review Count",
    "Website Score",
    "Lead Score",
    "Priority",
    "Recommended Package",
    "WhatsApp Message",
    "Cold Call Script",
    "Contacted",
    "WhatsApp Sent",
    "Call Status",
    "Follow-up Date",
    "Notes",
)

# Columns that should render as clickable hyperlinks in Excel.
HYPERLINK_COLUMNS = ("Website", "Instagram")

# Long free-text columns that should wrap and use a wider (capped) width.
WIDE_TEXT_COLUMNS = ("Address", "WhatsApp Message", "Cold Call Script", "Notes")


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _status_label(status: ContactStatus) -> str:
    return status.value.replace("_", " ").title()


@dataclass(frozen=True)
class LeadRow:
    """A lead flattened to the CRM column values (all display-ready)."""

    values: dict[str, object]

    def as_tuple(self) -> tuple[object, ...]:
        return tuple(self.values[col] for col in COLUMNS)


def lead_to_row(lead: Lead) -> LeadRow:
    """Flatten ``lead`` into the ordered CRM columns."""
    b = lead.business
    audit = lead.audit
    ai = lead.ai_content
    crm = lead.crm

    website_status = audit.status.value.replace("_", " ").title() if audit else "Unknown"
    website_score = round(lead.website_score.total) if lead.website_score else ""
    lead_score = lead.lead_score.value if lead.lead_score else ""
    priority = lead.priority.value.title() if lead.priority else ""
    package = lead.recommendation.package.label if lead.recommendation else ""

    values: dict[str, object] = {
        "Business Name": b.name,
        "Category": b.industry.label,
        "Area": b.area or "",
        "Address": b.address or "",
        "Phone": b.contact.phone or "",
        "Website": b.contact.website or "",
        "Website Status": website_status,
        "Instagram": b.contact.instagram or "",
        "Google Rating": b.ratings.rating if b.ratings.rating is not None else "",
        "Review Count": b.ratings.review_count,
        "Website Score": website_score,
        "Lead Score": lead_score,
        "Priority": priority,
        "Recommended Package": package,
        "WhatsApp Message": ai.whatsapp_message if ai else "",
        "Cold Call Script": ai.cold_call_script if ai else "",
        "Contacted": _yes_no(crm.contact_status != ContactStatus.NOT_CONTACTED),
        "WhatsApp Sent": _yes_no(crm.whatsapp_sent),
        "Call Status": crm.call_status or _status_label(crm.contact_status),
        "Follow-up Date": crm.follow_up_date.isoformat() if crm.follow_up_date else "",
        "Notes": crm.notes or "",
    }
    return LeadRow(values=values)
