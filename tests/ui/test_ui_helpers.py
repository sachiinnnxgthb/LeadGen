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
    merge_leads,
    priority_counts,
    tel_link,
    whatsapp_link,
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


# -- phone / whatsapp links ------------------------------------------------


def test_tel_link_normalizes_indian_number() -> None:
    assert tel_link("+91 98813 44635") == "tel:+919881344635"
    assert tel_link("9881344635") == "tel:+919881344635"       # bare 10-digit gets +91
    assert tel_link("098813 44635") == "tel:+919881344635"      # leading 0 stripped
    assert tel_link(None) is None
    assert tel_link("") is None


def test_whatsapp_link_builds_wa_me_with_message() -> None:
    link = whatsapp_link("+91 98813 44635", "Hi there!")
    assert link is not None
    assert link.startswith("https://wa.me/919881344635?text=")
    assert "Hi%20there" in link
    assert whatsapp_link(None, "x") is None


def test_whatsapp_link_without_message() -> None:
    assert whatsapp_link("9881344635") == "https://wa.me/919881344635"


# -- merge / accumulate ----------------------------------------------------


def test_merge_leads_deduplicates_and_prefers_new() -> None:
    leads = _leads()
    first_two = leads[:2]
    overlap = [leads[1], leads[2]]  # leads[1] appears in both
    merged = merge_leads(first_two, overlap)
    keys = [x.business.dedup_key for x in merged]
    assert len(keys) == len(set(keys))          # no duplicates
    assert len(merged) == 3                       # 2 + 2 - 1 overlap


def test_merge_leads_sorted_by_score() -> None:
    merged = merge_leads(_leads(), [])
    scores = [x.lead_score.value for x in merged if x.lead_score]
    assert scores == sorted(scores, reverse=True)
