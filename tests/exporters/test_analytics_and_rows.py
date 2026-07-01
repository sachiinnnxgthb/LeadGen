"""Tests for dashboard analytics and the flat row mapping."""

from __future__ import annotations

from lead_intel.config.settings import Settings
from lead_intel.domain.models import Lead
from lead_intel.exporters.analytics import compute_dashboard
from lead_intel.exporters.rows import COLUMNS, lead_to_row


def _revenue() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_dashboard_counts(leads: list[Lead]) -> None:
    stats = compute_dashboard(leads, _revenue().revenue)
    assert stats.total_businesses == 4
    assert stats.without_website == 1
    assert stats.broken_websites == 1
    assert stats.outdated_websites == 1
    assert stats.modern_websites == 1
    assert stats.high_priority == 2


def test_dashboard_averages_and_distributions(leads: list[Lead]) -> None:
    stats = compute_dashboard(leads, _revenue().revenue)
    assert 0 <= stats.average_rating <= 5
    assert 0 <= stats.average_website_score <= 100
    assert stats.category_distribution["Gym"] == 1
    assert stats.area_distribution["Baner"] == 2  # gym + salon
    assert stats.potential_monthly_revenue > 0


def test_dashboard_empty_is_safe() -> None:
    stats = compute_dashboard([], _revenue().revenue)
    assert stats.total_businesses == 0
    assert stats.average_rating == 0.0
    assert stats.potential_monthly_revenue == 0.0


def test_kpi_pairs_are_ordered(leads: list[Lead]) -> None:
    stats = compute_dashboard(leads, _revenue().revenue)
    labels = [label for label, _ in stats.as_kpi_pairs()]
    assert labels[0] == "Total Businesses"
    assert "Potential Monthly Revenue (₹)" in labels


def test_lead_to_row_maps_all_columns(leads: list[Lead]) -> None:
    row = lead_to_row(leads[0])
    assert set(row.values) == set(COLUMNS)
    assert row.values["Business Name"] == "IronCore Gym"
    assert row.values["Priority"] == "High"
    assert row.values["Website Status"] == "No Website"
    assert row.values["Recommended Package"] == "Premium"
    assert row.values["WhatsApp Sent"] == "No"
    assert row.values["Contacted"] == "No"
