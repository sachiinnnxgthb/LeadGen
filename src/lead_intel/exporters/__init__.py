"""Exporter layer: Excel CRM, Dashboard, PDF audits, CSV/JSON.

Turns scored + content-enriched leads into the deliverable artifacts a sales team
uses. :class:`ExportService` is the one-call facade; individual exporters are
available for targeted use.
"""

from __future__ import annotations

from lead_intel.exporters.analytics import DashboardStats, compute_dashboard
from lead_intel.exporters.data_exporter import export_csv, export_json
from lead_intel.exporters.export_service import ExportService, ExportSummary
from lead_intel.exporters.pdf_exporter import PdfAuditExporter

__all__ = [
    "DashboardStats",
    "compute_dashboard",
    "export_csv",
    "export_json",
    "ExportService",
    "ExportSummary",
    "PdfAuditExporter",
]
