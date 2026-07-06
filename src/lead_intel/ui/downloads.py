"""In-memory download builders for the UI.

Streamlit's ``download_button`` needs bytes, not file paths. These helpers reuse
the exporter layer to build each artifact entirely in memory, so nothing touches
disk until the user actually downloads. Kept out of ``app.py`` so they can be
unit-tested without Streamlit.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path

from lead_intel.config.settings import AgencySettings, PackageSettings, RevenueSettings
from lead_intel.domain.models import Lead
from lead_intel.exporters.analytics import compute_dashboard
from lead_intel.exporters.excel_exporter import build_crm_workbook
from lead_intel.exporters.export_service import _slugify
from lead_intel.exporters.pdf_exporter import PdfAuditExporter
from lead_intel.exporters.proposal_exporter import ProposalExporter
from lead_intel.exporters.rows import COLUMNS, lead_to_row

EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def crm_excel_bytes(leads: list[Lead], revenue: RevenueSettings) -> bytes:
    """Build the full CRM workbook as bytes."""
    stats = compute_dashboard(leads, revenue)
    workbook = build_crm_workbook(leads, stats)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def csv_bytes(leads: list[Lead]) -> bytes:
    """Build the flat CRM CSV as bytes."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(COLUMNS))
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead_to_row(lead).values)
    return buffer.getvalue().encode("utf-8")


def json_bytes(leads: list[Lead]) -> bytes:
    """Build the full-model JSON export as bytes."""
    payload = [lead.model_dump(mode="json") for lead in leads]
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def proposal_bytes(
    lead: Lead,
    agency: AgencySettings,
    packages: PackageSettings,
    *,
    screenshot: bytes | None = None,
) -> bytes:
    """Build a client-ready proposal PDF for one lead (optionally with a screenshot)."""
    return ProposalExporter(agency, packages).to_bytes(lead, screenshot=screenshot)


def pdf_zip_bytes(leads: list[Lead], agency: AgencySettings) -> bytes:
    """Build a ZIP of per-business PDF audit reports as bytes."""
    exporter = PdfAuditExporter(agency)
    buffer = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(
        buffer, "w", zipfile.ZIP_DEFLATED
    ) as archive:
        seen: dict[str, int] = {}
        for lead in leads:
            slug = _slugify(lead.business.name)
            seen[slug] = seen.get(slug, 0) + 1
            if seen[slug] > 1:
                slug = f"{slug}-{seen[slug]}"
            path = Path(tmp) / f"{slug}.pdf"
            exporter.export(lead, path)
            archive.write(path, arcname=f"{slug}.pdf")
    return buffer.getvalue()
