"""Website audit layer.

Turns a business's URL into an explainable :class:`WebsiteAudit`: reachability,
HTTPS/redirect/broken classification, conversion/trust feature presence, and
mobile/slow/outdated heuristics. HTML-only by default; the ``AuditEnricher`` seam
allows richer probes (Playwright, PageSpeed) to be added later.
"""

from __future__ import annotations

from lead_intel.audit.base import AuditContext, AuditEnricher
from lead_intel.audit.engine import WebsiteAuditEngine, build_audit_engine
from lead_intel.audit.fetcher import FetchResult, PageFetcher

__all__ = [
    "AuditContext",
    "AuditEnricher",
    "WebsiteAuditEngine",
    "build_audit_engine",
    "FetchResult",
    "PageFetcher",
]
