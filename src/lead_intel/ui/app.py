"""Streamlit application.

The interactive front end that drives the whole platform: configure a search,
generate leads (or load sample data), explore the dashboard + table, and download
the CRM workbook / PDF audits. All heavy logic lives in the service and exporter
layers; this module is a thin, well-organized rendering shell.

Run with:  ``streamlit run app.py``
"""

from __future__ import annotations

import streamlit as st

from lead_intel.config.settings import Settings
from lead_intel.core.exceptions import LeadIntelError
from lead_intel.domain.enums import DataProvider, Industry, LeadPriority, WebsiteStatus
from lead_intel.domain.models import Lead
from lead_intel.services.pipeline import PipelineConfig, ProgressEvent, build_pipeline
from lead_intel.ui import downloads
from lead_intel.ui.demo import sample_leads
from lead_intel.ui.formatting import (
    TABLE_COLUMNS,
    filter_leads,
    leads_to_dataframe,
    priority_counts,
)

_DARK_CSS = """
<style>
  .stApp { background-color: #0e1117; color: #fafafa; }
  section[data-testid="stSidebar"] { background-color: #161a23; }
</style>
"""

_DEFAULT_CATEGORIES = [Industry.GYM, Industry.CAFE, Industry.RESTAURANT, Industry.DENTAL_CLINIC,
                       Industry.SALON, Industry.SPA]


def _init_state() -> None:
    st.session_state.setdefault("leads", [])
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("dark_mode", False)


def _settings() -> Settings:
    """Load settings from .env / environment (cached per session)."""
    if "settings" not in st.session_state:
        st.session_state.settings = Settings()
    settings: Settings = st.session_state.settings
    return settings


# -- sidebar ---------------------------------------------------------------


def _render_sidebar(settings: Settings) -> None:
    st.sidebar.title("🔍 Lead Intelligence")
    st.session_state.dark_mode = st.sidebar.toggle("🌙 Dark mode", value=st.session_state.dark_mode)

    st.sidebar.header("Search")
    provider_label = st.sidebar.selectbox(
        "Provider", [DataProvider.GOOGLE_PLACES.value, DataProvider.APIFY_GMAPS.value]
    )
    city = st.sidebar.text_input("City", value=settings.search.city)
    categories = st.sidebar.multiselect(
        "Categories",
        options=list(Industry),
        default=_DEFAULT_CATEGORIES,
        format_func=lambda ind: ind.label,
    )
    min_rating = st.sidebar.slider(
        "Minimum rating", 0.0, 5.0, float(settings.search.min_rating), 0.1
    )
    min_reviews = st.sidebar.number_input(
        "Minimum reviews", 0, 10000, int(settings.search.min_reviews)
    )
    max_results = st.sidebar.slider("Max results per category", 5, 120, 30, 5)

    col1, col2 = st.sidebar.columns(2)
    if col1.button("🚀 Generate", type="primary", use_container_width=True):
        _run_pipeline(
            settings,
            provider=DataProvider(provider_label),
            config=PipelineConfig(
                categories=categories or _DEFAULT_CATEGORIES,
                city=city,
                min_rating=min_rating,
                min_reviews=int(min_reviews),
                max_results_per_category=int(max_results),
            ),
        )
    if col2.button("🧪 Sample data", use_container_width=True):
        st.session_state.leads = sample_leads(settings)
        st.session_state.logs = ["Loaded sample data."]

    with st.sidebar.expander("⚙️ Settings"):
        llm_mode = "key set" if settings.anthropic_api_key else "templates"
        st.write(f"**Agency:** {settings.agency.name}")
        st.write(f"**LLM:** {settings.llm_provider} ({llm_mode})")
        st.caption("Edit `.env` to change API keys, agency details, scoring weights, and prices.")


def _run_pipeline(settings: Settings, *, provider: DataProvider, config: PipelineConfig) -> None:
    """Execute the pipeline with a live progress bar + log stream."""
    st.session_state.logs = []
    progress = st.sidebar.progress(0.0, text="Starting…")
    logs = st.session_state.logs

    def on_progress(event: ProgressEvent) -> None:
        logs.append(f"[{event.stage}] {event.message}")
        progress.progress(min(event.fraction, 1.0), text=event.message)

    try:
        pipeline = build_pipeline(settings.model_copy(update={"default_provider": provider}))
        result = pipeline.run(config, on_progress=on_progress)
        st.session_state.leads = result.leads
        logs.append(
            f"Discovered {result.discovered}, deduped to {result.deduplicated}, "
            f"{len(result.leads)} leads, {result.skipped} skipped."
        )
    except LeadIntelError as exc:
        st.sidebar.error(str(exc))
        logs.append(f"ERROR: {exc}")
    finally:
        progress.empty()


# -- main panels -----------------------------------------------------------


def _render_dashboard(leads: list[Lead]) -> None:
    st.subheader("📊 Dashboard")
    total = len(leads)
    no_site = sum(1 for x in leads if x.website_status == WebsiteStatus.NO_WEBSITE)
    high = sum(1 for x in leads if x.is_high_priority)
    ratings = [x.business.ratings.rating for x in leads if x.business.ratings.rating is not None]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Businesses", total)
    c2.metric("No Website", no_site)
    c3.metric("High Priority", high)
    c4.metric("Avg Rating", avg_rating)

    counts = priority_counts(leads)
    st.bar_chart(counts)


def _render_table(leads: list[Lead]) -> None:
    st.subheader("📋 Leads")
    col1, col2, col3 = st.columns([2, 2, 2])
    search = col1.text_input("Search", placeholder="name, category, or area")
    status_opts = col2.multiselect("Website status", list(WebsiteStatus),
                                   format_func=lambda s: s.value.replace("_", " ").title())
    prio_opts = col3.multiselect("Priority", list(LeadPriority),
                                 format_func=lambda p: p.value.title())

    filtered = filter_leads(
        leads,
        search=search,
        statuses=set(status_opts) or None,
        priorities=set(prio_opts) or None,
    )
    st.caption(f"Showing {len(filtered)} of {len(leads)} leads")
    st.dataframe(leads_to_dataframe(filtered, columns=TABLE_COLUMNS), use_container_width=True,
                 hide_index=True)
    _render_lead_detail(filtered)


def _render_lead_detail(leads: list[Lead]) -> None:
    if not leads:
        return
    names = [x.business.name for x in leads]
    choice = st.selectbox("View outreach content for", names)
    lead = next(x for x in leads if x.business.name == choice)
    if lead.ai_content:
        tabs = st.tabs(["WhatsApp", "Email", "Cold Call", "Follow-ups"])
        tabs[0].code(lead.ai_content.whatsapp_message)
        tabs[1].code(lead.ai_content.email)
        tabs[2].code(lead.ai_content.cold_call_script)
        tabs[3].code("\n\n---\n\n".join(lead.ai_content.follow_ups))


def _render_downloads(settings: Settings, leads: list[Lead]) -> None:
    st.subheader("⬇️ Downloads")
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("CRM.xlsx", downloads.crm_excel_bytes(leads, settings.revenue),
                       file_name="CRM.xlsx", mime=downloads.EXCEL_MIME, use_container_width=True)
    c2.download_button("Leads.csv", downloads.csv_bytes(leads), file_name="leads.csv",
                       mime="text/csv", use_container_width=True)
    c3.download_button("Leads.json", downloads.json_bytes(leads), file_name="leads.json",
                       mime="application/json", use_container_width=True)
    c4.download_button("Audits.zip", downloads.pdf_zip_bytes(leads, settings.agency),
                       file_name="audits.zip", mime="application/zip", use_container_width=True)


def _render_logs() -> None:
    if st.session_state.logs:
        with st.expander("📜 Progress logs", expanded=False):
            st.code("\n".join(st.session_state.logs))


def main() -> None:
    st.set_page_config(page_title="Lead Intelligence", page_icon="🔍", layout="wide")
    _init_state()
    settings = _settings()

    if st.session_state.dark_mode:
        st.markdown(_DARK_CSS, unsafe_allow_html=True)

    _render_sidebar(settings)

    st.title("AI Lead Intelligence & Website Audit")
    leads = st.session_state.leads
    if not leads:
        st.info("Configure a search and click **Generate**, or click **Sample data** to explore.")
        _render_logs()
        return

    _render_dashboard(leads)
    _render_downloads(settings, leads)
    _render_table(leads)
    _render_logs()


if __name__ == "__main__":
    main()
