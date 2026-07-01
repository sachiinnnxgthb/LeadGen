# Lead Intelligence & Website Audit Platform

A production-grade platform that helps a website design agency discover local
businesses most likely to buy a new website, audit their current web presence,
score them as sales leads, generate personalized AI outreach, and export a full
CRM workbook + PDF audit reports.

Primary market: **Pune, Maharashtra, India** — architected to scale to every
city in India (and beyond).

---

## Status

| Phase | Scope | State |
|-------|-------|-------|
| **1** | Architecture, folder structure, configuration, domain models | ✅ **Complete** |
| **2** | Provider abstraction + Google Places integration | ✅ **Complete** |
| **3** | Apify Google Maps provider | ✅ **Complete** |
| 4 | Website audit engine (reachability, HTTPS, features, heuristics) | ⏳ Planned |
| 5 | Scoring services (Website Score 0-100, Lead Score 0-10, package recommendation) | ⏳ Planned |
| 6 | AI content generation (centralized prompts, provider-agnostic LLM) | ⏳ Planned |
| 7 | Exporters (Excel CRM, dashboard, PDF audits, CSV/JSON) | ⏳ Planned |
| 8 | Streamlit application | ⏳ Planned |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design rationale.

---

## Architecture at a glance

Clean Architecture — dependencies point **inward**. The domain layer is pure and
has zero knowledge of networks, files, or vendors.

```
src/lead_intel/
├── domain/        # Pure models & enums (Business, WebsiteAudit, Lead, scores...)
│   ├── enums.py
│   └── models/
├── config/        # Typed settings loaded & validated from .env
├── core/          # Cross-cutting: structured logging, exception hierarchy
├── providers/     # BusinessProvider interface + Google Places + Apify + factory
│   (later) services/  audit/  ai/  exporters/  ui/
```

Key principles: SOLID, Repository/Provider pattern for data sources, a Service
layer for orchestration, Pydantic models everywhere, full type hints, structured
logging, and tests.

---

## Quick start (development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"          # core + test/lint/type tooling

cp .env.example .env             # then fill in API keys as phases land

pytest                           # run the test suite
mypy src                         # strict type checking
ruff check src tests             # lint
```

> Requires Python 3.9+. On 3.9/3.10 the `eval-type-backport` dependency lets
> Pydantic evaluate modern `X | None` annotations at runtime.

---

## Configuration

Everything is configurable through `.env` (see [.env.example](.env.example)):
API keys, target city/categories, minimum rating/reviews, lead- and
website-score weights, package prices, revenue assumptions, and agency identity.
Nested settings use a `__` delimiter, e.g. `LEAD_SCORE__NO_WEBSITE=4`.

```python
from lead_intel.config import get_settings

settings = get_settings()        # cached, validated, process-wide
settings.search.city             # "Pune"
settings.package.premium_price   # 14999
```

---

## License

Proprietary — built for commercial deployment.
