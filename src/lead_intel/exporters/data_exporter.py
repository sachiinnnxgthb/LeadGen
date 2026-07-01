"""CSV and JSON exporters.

Flat CSV (the CRM columns) for spreadsheets, and rich JSON (full lead model) for
downstream systems / re-import. Both stream to disk and create parent dirs.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from lead_intel.core.logging import get_logger
from lead_intel.domain.models import Lead
from lead_intel.exporters.rows import COLUMNS, lead_to_row

logger = get_logger("exporters.data")


def export_csv(leads: list[Lead], path: Path) -> Path:
    """Write leads as a flat CSV using the CRM columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(COLUMNS))
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead_to_row(lead).values)
    logger.info("wrote CSV", extra={"path": str(path), "rows": len(leads)})
    return path


def export_json(leads: list[Lead], path: Path) -> Path:
    """Write leads as pretty JSON using the full domain model (JSON-safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [lead.model_dump(mode="json") for lead in leads]
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    logger.info("wrote JSON", extra={"path": str(path), "rows": len(leads)})
    return path
