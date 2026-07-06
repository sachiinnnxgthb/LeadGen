"""Streamlit UI layer.

Thin rendering shell over the service/exporter layers. Non-trivial logic lives in
:mod:`lead_intel.ui.formatting` and :mod:`lead_intel.ui.downloads` so it stays
unit-testable; :mod:`lead_intel.ui.app` is the Streamlit entry point.
"""

from __future__ import annotations

from lead_intel.ui.formatting import (
    filter_leads,
    leads_to_dataframe,
    merge_leads,
    priority_counts,
)

__all__ = ["filter_leads", "leads_to_dataframe", "merge_leads", "priority_counts"]
