"""Lead Intelligence & Website Audit Platform.

A production-grade toolkit that discovers local businesses, audits their web
presence, scores them as sales leads, generates AI outreach content, and exports
a full CRM workbook + PDF audits for a website design agency.

Built on Clean Architecture: the :mod:`lead_intel.domain` layer is pure and has
no outward dependencies; infrastructure (providers, audit, exporters, AI, UI)
depends inward on it.
"""

from __future__ import annotations

__version__ = "0.1.0"
