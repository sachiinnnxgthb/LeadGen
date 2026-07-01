"""Export orchestration.

One facade that writes the full artifact set to the output directory: the CRM
workbook, standalone Dashboard + segment workbooks, CSV, JSON, and per-business
PDF audits. Individual failures are isolated (partial exports) so one bad file
never aborts the whole run.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from lead_intel.config.settings import Settings
from lead_intel.core.logging import get_logger
from lead_intel.domain.enums import WebsiteQuality, WebsiteStatus
from lead_intel.domain.models import Lead
from lead_intel.exporters import excel_exporter as excel
from lead_intel.exporters.analytics import compute_dashboard
from lead_intel.exporters.data_exporter import export_csv, export_json
from lead_intel.exporters.pdf_exporter import PdfAuditExporter

logger = get_logger("exporters.service")


@dataclass
class ExportSummary:
    """Result of an export run: what was written and what failed."""

    written: list[Path] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "business"


class ExportService:
    """Writes all export artifacts for a batch of leads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._output = Path(settings.output_dir)
        self._pdf = PdfAuditExporter(settings.agency)

    def export_all(self, leads: list[Lead], *, generate_pdfs: bool = True) -> ExportSummary:
        """Write every artifact; isolate and record per-artifact failures."""
        summary = ExportSummary()
        stats = compute_dashboard(leads, self._settings.revenue)

        self._safe(summary, "CRM.xlsx",
                   lambda: excel.save_workbook(
                       excel.build_crm_workbook(leads, stats), self._output / "CRM.xlsx"))
        self._safe(summary, "Dashboard.xlsx",
                   lambda: excel.save_workbook(
                       excel.build_dashboard_workbook(stats), self._output / "Dashboard.xlsx"))

        for filename, subset in self._segments(leads):
            self._safe(summary, filename, functools.partial(self._write_segment, filename, subset))

        self._safe(summary, "leads.csv", lambda: export_csv(leads, self._output / "leads.csv"))
        self._safe(summary, "leads.json", lambda: export_json(leads, self._output / "leads.json"))

        if generate_pdfs:
            self._export_pdfs(leads, summary)

        logger.info(
            "export run complete",
            extra={"written": len(summary.written), "errors": len(summary.errors)},
        )
        return summary

    def _write_segment(self, filename: str, subset: list[Lead]) -> Path:
        workbook = excel.build_segment_workbook(subset, title=filename.replace(".xlsx", ""))
        return excel.save_workbook(workbook, self._output / filename)

    def _segments(self, leads: list[Lead]) -> list[tuple[str, list[Lead]]]:
        return [
            ("HighPriority.xlsx", [x for x in leads if x.is_high_priority]),
            ("NoWebsite.xlsx",
             [x for x in leads if x.website_status == WebsiteStatus.NO_WEBSITE]),
            ("OutdatedWebsite.xlsx",
             [x for x in leads if x.website_quality == WebsiteQuality.OUTDATED]),
            ("BrokenWebsite.xlsx",
             [x for x in leads if x.website_quality == WebsiteQuality.BROKEN]),
        ]

    def _export_pdfs(self, leads: list[Lead], summary: ExportSummary) -> None:
        pdf_dir = self._output / "audits"
        seen: dict[str, int] = {}
        for lead in leads:
            slug = _slugify(lead.business.name)
            seen[slug] = seen.get(slug, 0) + 1
            if seen[slug] > 1:  # disambiguate duplicate names
                slug = f"{slug}-{seen[slug]}"
            self._safe(
                summary,
                f"audits/{slug}.pdf",
                functools.partial(self._pdf.export, lead, pdf_dir / f"{slug}.pdf"),
            )

    @staticmethod
    def _safe(summary: ExportSummary, label: str, action: Callable[[], Path]) -> None:
        try:
            summary.written.append(action())
        except Exception as exc:  # noqa: BLE001 - isolate per-artifact failures
            logger.exception("export failed", extra={"artifact": label})
            summary.errors[label] = str(exc)
