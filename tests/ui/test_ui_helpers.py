"""Tests for UI formatting helpers, download builders, and demo data."""

from __future__ import annotations

import io
import json
import zipfile

from lead_intel.config.settings import Settings
from lead_intel.domain.enums import LeadPriority, WebsiteStatus
from lead_intel.ui import downloads
from lead_intel.ui.demo import sample_leads
from lead_intel.ui.formatting import (
    TABLE_COLUMNS,
    filter_leads,
    leads_to_dataframe,
    priority_counts,
)


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def _leads():
    return sample_leads(_settings())


# -- demo ------------------------------------------------------------------


def test_sample_leads_are_fully_enriched() -> None:
    leads = _leads()
    assert len(leads) >= 4
    for lead in leads:
        assert lead.website_score is not None
        assert lead.lead_score is not None
        assert lead.ai_content is not None and lead.ai_content.is_populated


# -- formatting ------------------------------------------------------------


def test_leads_to_dataframe_uses_requested_columns() -> None:
    frame = leads_to_dataframe(_leads(), columns=TABLE_COLUMNS)
    assert list(frame.columns) == list(TABLE_COLUMNS)
    assert len(frame) == len(_leads())


def test_filter_by_search() -> None:
    leads = _leads()
    result = filter_leads(leads, search="gym")
    assert result
    assert all("gym" in x.business.name.lower() or x.business.industry.value == "gym"
               for x in result)


def test_filter_by_status_and_priority() -> None:
    leads = _leads()
    no_site = filter_leads(leads, statuses={WebsiteStatus.NO_WEBSITE})
    assert all(x.website_status == WebsiteStatus.NO_WEBSITE for x in no_site)

    high = filter_leads(leads, priorities={LeadPriority.HIGH})
    assert all(x.priority == LeadPriority.HIGH for x in high)


def test_empty_filters_return_all() -> None:
    leads = _leads()
    assert len(filter_leads(leads)) == len(leads)


def test_priority_counts_sum_to_total() -> None:
    leads = _leads()
    counts = priority_counts(leads)
    assert set(counts) == {"High", "Medium", "Low"}
    assert sum(counts.values()) == sum(1 for x in leads if x.priority is not None)


# -- downloads -------------------------------------------------------------


def test_excel_bytes_are_valid_xlsx() -> None:
    data = downloads.crm_excel_bytes(_leads(), _settings().revenue)
    assert data[:2] == b"PK"  # xlsx is a zip container


def test_csv_bytes_have_header_and_rows() -> None:
    import csv

    data = downloads.csv_bytes(_leads()).decode("utf-8")
    rows = list(csv.reader(io.StringIO(data)))  # handles quoted newlines correctly
    assert rows[0][0] == "Business Name"
    assert len(rows) == len(_leads()) + 1


def test_json_bytes_parse() -> None:
    data = json.loads(downloads.json_bytes(_leads()).decode("utf-8"))
    assert len(data) == len(_leads())
    assert "business" in data[0]


def test_pdf_zip_contains_one_pdf_per_lead() -> None:
    leads = _leads()
    data = downloads.pdf_zip_bytes(leads, _settings().agency)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
    assert len(names) == len(leads)
    assert all(name.endswith(".pdf") for name in names)
