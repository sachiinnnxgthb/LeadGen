"""UI-facing pure helpers.

All non-trivial UI logic lives here — building the leads DataFrame and filtering
it — so it can be unit-tested without spinning up Streamlit. ``app.py`` stays a
thin rendering layer over these functions.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date, datetime

import pandas as pd

from lead_intel.domain.enums import ContactStatus, LeadPriority, WebsiteStatus
from lead_intel.domain.models import Lead
from lead_intel.exporters.rows import COLUMNS, lead_to_row

# Human-readable labels for the editable Status column, in workflow order.
STATUS_LABELS: list[str] = [s.value.replace("_", " ").title() for s in ContactStatus]
_LABEL_TO_STATUS = {label: status for label, status in zip(STATUS_LABELS, ContactStatus)}

# Compact column set shown in the interactive table (full set is in the export).
TABLE_COLUMNS: tuple[str, ...] = (
    "Business Name",
    "Category",
    "Area",
    "Phone",
    "Website Status",
    "Google Rating",
    "Review Count",
    "Website Score",
    "Lead Score",
    "Priority",
    "Recommended Package",
)


def leads_to_dataframe(leads: list[Lead], *, columns: tuple[str, ...] = COLUMNS) -> pd.DataFrame:
    """Build a DataFrame of leads limited to ``columns`` (in order)."""
    records = [lead_to_row(lead).values for lead in leads]
    frame = pd.DataFrame(records, columns=list(COLUMNS))
    return frame[list(columns)]


def filter_leads(
    leads: list[Lead],
    *,
    search: str = "",
    statuses: set[WebsiteStatus] | None = None,
    priorities: set[LeadPriority] | None = None,
) -> list[Lead]:
    """Filter leads by free-text search, website status, and priority.

    Empty/None filters mean "no restriction". Search matches business name,
    category, or area (case-insensitive substring).
    """
    needle = search.strip().lower()

    def matches(lead: Lead) -> bool:
        if statuses and lead.website_status not in statuses:
            return False
        if priorities and (lead.priority is None or lead.priority not in priorities):
            return False
        if needle:
            haystack = " ".join(
                [lead.business.name, lead.business.industry.label, lead.business.area or ""]
            ).lower()
            if needle not in haystack:
                return False
        return True

    return [lead for lead in leads if matches(lead)]


def merge_leads(existing: list[Lead], new: list[Lead]) -> list[Lead]:
    """Combine two lead lists, de-duplicating by business, keeping the newer entry.

    Used by the UI's "accumulate" mode so repeated searches build one growing,
    duplicate-free master list. Result is sorted by lead score (desc).
    """
    by_key: dict[str, Lead] = {lead.business.dedup_key: lead for lead in existing}
    for lead in new:
        by_key[lead.business.dedup_key] = lead  # newer wins on collision
    merged = list(by_key.values())
    merged.sort(key=lambda x: x.lead_score.value if x.lead_score else 0.0, reverse=True)
    return merged


def priority_counts(leads: list[Lead]) -> dict[str, int]:
    """Count leads per priority bucket (High/Medium/Low)."""
    counts = {p.value.title(): 0 for p in LeadPriority}
    for lead in leads:
        if lead.priority is not None:
            counts[lead.priority.value.title()] += 1
    return counts


def _status_label(status: ContactStatus) -> str:
    return status.value.replace("_", " ").title()


def tracking_editor_df(leads: list[Lead]) -> pd.DataFrame:
    """Build the editable tracking table (one row per lead, keyed by business)."""
    rows = [
        {
            "key": lead.business.dedup_key,
            "Business": lead.business.name,
            "Phone": lead.business.contact.phone or "",
            "Priority": lead.priority.value.title() if lead.priority else "",
            "Status": _status_label(lead.crm.contact_status),
            "WhatsApp Sent": lead.crm.whatsapp_sent,
            "Follow-up": lead.crm.follow_up_date,
            "Notes": lead.crm.notes,
        }
        for lead in leads
    ]
    return pd.DataFrame(rows)


def apply_tracking_edits(leads: list[Lead], edited: pd.DataFrame) -> None:
    """Write edits from the tracking table back onto each lead's CRM fields."""
    by_key = {lead.business.dedup_key: lead for lead in leads}
    for _, row in edited.iterrows():
        lead = by_key.get(row["key"])
        if lead is None:
            continue
        lead.crm.contact_status = _LABEL_TO_STATUS.get(
            row.get("Status", ""), lead.crm.contact_status
        )
        lead.crm.whatsapp_sent = bool(row.get("WhatsApp Sent", False))
        lead.crm.notes = str(row.get("Notes") or "")
        follow_up = row.get("Follow-up")
        lead.crm.follow_up_date = _coerce_date(follow_up)


def _coerce_date(value: object) -> date | None:
    # datetime (and pandas Timestamp, a datetime subclass) -> its .date();
    # plain date passes through; None / NaT / NaN -> None.
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def leads_from_json(data: bytes) -> list[Lead]:
    """Reconstruct leads from a previously-exported JSON workspace."""
    parsed = json.loads(data)
    if not isinstance(parsed, list):
        raise ValueError("Workspace file must be a JSON list of leads.")
    return [Lead.model_validate(item) for item in parsed]


def _e164_digits(phone: str | None, *, default_country: str = "91") -> str | None:
    """Normalize a phone number to bare international digits (e.g. ``919881344635``).

    Returns ``None`` when there is nothing usable. Tailored for Indian numbers:
    a bare 10-digit number gets the country code prepended.
    """
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if len(digits) == 10:
        digits = default_country + digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = default_country + digits[1:]
    return digits


def tel_link(phone: str | None) -> str | None:
    """Build a ``tel:`` URI so a tap dials the number on a phone."""
    digits = _e164_digits(phone)
    return f"tel:+{digits}" if digits else None


def whatsapp_link(phone: str | None, message: str = "") -> str | None:
    """Build a ``wa.me`` link that opens WhatsApp with the message pre-filled."""
    digits = _e164_digits(phone)
    if not digits:
        return None
    base = f"https://wa.me/{digits}"
    return f"{base}?text={urllib.parse.quote(message)}" if message else base
