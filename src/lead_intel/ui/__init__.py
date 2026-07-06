"""Streamlit UI layer.

Thin rendering shell over the service/exporter layers. Non-trivial logic lives in
:mod:`lead_intel.ui.formatting` and :mod:`lead_intel.ui.downloads` so it stays
unit-testable; :mod:`lead_intel.ui.app` is the Streamlit entry point.
"""

from __future__ import annotations

from lead_intel.ui.formatting import (
    apply_tracking_edits,
    filter_leads,
    leads_from_json,
    leads_to_dataframe,
    merge_leads,
    priority_counts,
    tracking_editor_df,
)

__all__ = [
    "apply_tracking_edits",
    "filter_leads",
    "leads_from_json",
    "leads_to_dataframe",
    "merge_leads",
    "priority_counts",
    "tracking_editor_df",
]
