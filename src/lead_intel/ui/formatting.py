"""UI-facing pure helpers.

All non-trivial UI logic lives here — building the leads DataFrame and filtering
it — so it can be unit-tested without spinning up Streamlit. ``app.py`` stays a
thin rendering layer over these functions.
"""

from __future__ import annotations

import pandas as pd

from lead_intel.domain.enums import LeadPriority, WebsiteStatus
from lead_intel.domain.models import Lead
from lead_intel.exporters.rows import COLUMNS, lead_to_row

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


def priority_counts(leads: list[Lead]) -> dict[str, int]:
    """Count leads per priority bucket (High/Medium/Low)."""
    counts = {p.value.title(): 0 for p in LeadPriority}
    for lead in leads:
        if lead.priority is not None:
            counts[lead.priority.value.title()] += 1
    return counts
