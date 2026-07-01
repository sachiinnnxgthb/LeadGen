# Architecture

This document explains the design of the Lead Intelligence & Website Audit
Platform: the layering, the key models, and the decisions that keep it
extensible toward the roadmap (multi-city, CRM integrations, REST API, billing).

## Guiding principles

- **Clean Architecture** — concentric layers; source-code dependencies only ever
  point inward. The domain never imports infrastructure.
- **SOLID** — small, single-responsibility classes; behaviour depends on
  abstractions (provider/LLM/exporter interfaces), not concretions.
- **Provider / Repository pattern** — data sources sit behind an interface that
  returns the common `Business` model, so Google Places, Apify, or a future
  source are interchangeable.
- **Service layer** — audit, scoring, AI generation, and export are orchestration
  services that consume domain models and produce enriched ones.
- **Everything configurable** — all thresholds, weights, and prices live in typed
  settings loaded from `.env`; no magic numbers in code.

## Layers

```
┌───────────────────────────────────────────────────────────────┐
│  Interface: Streamlit UI  ·  (future) REST API  ·  CLI          │  Phase 8
├───────────────────────────────────────────────────────────────┤
│  Exporters: Excel CRM · Dashboard · PDF audit · CSV/JSON        │  Phase 7
├───────────────────────────────────────────────────────────────┤
│  Services: Audit · Scoring · Recommendation · AI Content        │  Phases 4-6
├───────────────────────────────────────────────────────────────┤
│  Providers: GooglePlaces · Apify  (behind BusinessProvider)     │  Phases 2-3
├───────────────────────────────────────────────────────────────┤
│  Core: logging · exceptions          Config: typed settings     │  Phase 1
├───────────────────────────────────────────────────────────────┤
│  Domain: Business · WebsiteAudit · Scores · AIContent · Lead    │  Phase 1  ← pure
└───────────────────────────────────────────────────────────────┘
```

Arrows of dependency run downward only. The **domain** at the bottom depends on
nothing; each layer above may depend on the layers below it.

## Domain model (Phase 1)

The `Lead` aggregate is assembled progressively as it moves through the pipeline:

```
Business ──audit──▶ WebsiteAudit ──score──▶ WebsiteScore + LeadScore
   │                                              │
   └──────────────── Lead (aggregate root) ◀──────┘
                       + SalesRecommendation
                       + AIContent
                       + CRMTracking (mutable, human-edited)
```

| Model | Responsibility |
|-------|----------------|
| `Business` | Canonical, provider-agnostic business; owns `dedup_key` for cross-provider de-duplication and normalizes website URLs. |
| `BusinessContact` / `BusinessRatings` | Value objects for channels and review signals. |
| `WebsiteAudit` | Reachability + `FeaturePresence` (missing contact form, WhatsApp, testimonials…) + derived `WebsiteQuality`. |
| `WebsiteScore` | 0-100 with per-dimension subscores and explanations. |
| `LeadScore` | 0-10 with a transparent `breakdown` and `LeadPriority`. |
| `SalesRecommendation` | Chosen `PackageTier`, price, and rationale. |
| `AIContent` | All personalized outreach copy. |
| `Lead` | Aggregate root exporters and the UI consume. |

### Modelling decisions

- **Tri-state feature flags.** `FeaturePresence` fields are `Optional[bool]`:
  `None` = "not determined" (site unreachable), `False` = "checked and genuinely
  missing" — only the latter becomes a sales talking point. This distinction is
  load-bearing for honest audits.
- **Results, not logic, in the domain.** Score models carry values *and*
  explanations but never compute them; computation lives in Phase-5 services so
  scoring rules stay swappable and testable.
- **Explainability is mandatory.** Every score ships with human-readable reasons
  so the UI, PDF, and CRM can always answer "why?".

## Configuration

`config/settings.py` uses pydantic-settings with nested groups (`search`,
`audit`, `lead_score`, `website_score`, `package`, `revenue`, `agency`) addressed
via a `__` env delimiter. Validators enforce invariants at startup — e.g.
website-score weights must sum to 1.0, and `medium_priority_min <=
high_priority_min` — so misconfiguration fails fast instead of skewing results
silently. `get_settings()` is `lru_cache`d for a single parse per process.

## Cross-cutting core

- `core/logging.py` — stdlib-only structured logging; human console format in
  dev, line-delimited JSON in production (`LOG_JSON=true`). Idempotent setup.
- `core/exceptions.py` — one `LeadIntelError` base with targeted subclasses
  (`ProviderError`, `RateLimitError`, `ProviderAuthError`, `WebsiteAuditError`,
  `ExportError`, `ConfigurationError`) so callers can back off or skip precisely.
  Infrastructure translates vendor exceptions into these.

## Extensibility map (roadmap → seam)

| Future feature | Seam it plugs into |
|----------------|--------------------|
| Apify / LinkedIn / Facebook discovery | `BusinessProvider` interface (Phase 2) |
| HubSpot / Zoho / Salesforce / Sheets sync | Exporter interface (Phase 7) |
| Alternate LLMs | Centralized prompts + `LLMProvider` interface (Phase 6) |
| Multi-city / multi-country | `SearchSettings` + provider query params |
| REST API, auth, billing, scheduled scans | New interface layer over existing services |

## Quality gates

`pytest` (unit tests), `mypy --strict`, and `ruff` all run clean on Phase 1 and
gate every subsequent phase before it is considered complete.
