"""Audit extension seam.

Defines the context object and the :class:`AuditEnricher` protocol. The engine
runs HTML heuristics first, then hands each enricher the audit-in-progress plus
the fetch context. Future probes — a Playwright render check, a Google PageSpeed
call — implement this protocol to refine signals like ``mobile_friendly`` or
``appears_slow`` without changing the engine or the heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from bs4 import BeautifulSoup

from lead_intel.audit.fetcher import FetchResult
from lead_intel.domain.models import Business, WebsiteAudit


@dataclass
class AuditContext:
    """Everything an enricher needs about the page being audited."""

    business: Business
    fetch: FetchResult
    soup: BeautifulSoup | None  # None when the page could not be parsed


@runtime_checkable
class AuditEnricher(Protocol):
    """Optional post-heuristic refiner of a :class:`WebsiteAudit`.

    Implementations mutate ``audit`` in place (e.g. set a more accurate
    ``technical.mobile_friendly``) and may append to ``audit.problems``.
    """

    def enrich(self, audit: WebsiteAudit, context: AuditContext) -> None: ...
