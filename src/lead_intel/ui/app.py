"""Streamlit application.

The interactive front end that drives the whole platform: configure a search,
generate leads (or load sample data), explore the dashboard + mobile-friendly lead
cards, and download the CRM workbook / PDF audits. All heavy logic lives in the
service and exporter layers; this module is a thin, well-organized rendering shell.

Run with:  ``streamlit run app.py``
"""

from __future__ import annotations

import html
import os

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
    merge_leads,
    priority_counts,
    tel_link,
    whatsapp_link,
)

# Secret keys copied from st.secrets → env so cloud deploys work without a .env file.
_SECRET_KEYS = ("APIFY_API_TOKEN", "GOOGLE_PLACES_API_KEY", "ANTHROPIC_API_KEY", "DEFAULT_PROVIDER")

_DEFAULT_CATEGORIES = [Industry.GYM, Industry.CAFE, Industry.RESTAURANT, Industry.DENTAL_CLINIC,
                       Industry.SALON, Industry.SPA]

_BASE_CSS = """
<style>
  .block-container { padding-top: 2rem; max-width: 1100px; }
  /* Hero */
  .hero { background: linear-gradient(120deg,#1F3A5F 0%,#3A6EA5 100%);
          color:#fff; padding:1.4rem 1.6rem; border-radius:16px; margin-bottom:1.2rem; }
  .hero h1 { margin:0; font-size:1.6rem; line-height:1.2; }
  .hero p { margin:.3rem 0 0; opacity:.9; font-size:.95rem; }
  /* Buttons: big touch targets */
  .stButton>button, .stDownloadButton>button {
      border-radius:10px; font-weight:600; padding:.55rem 1rem; }
  /* Metric cards */
  div[data-testid="stMetric"] {
      background:rgba(31,58,95,.06); border:1px solid rgba(31,58,95,.12);
      border-radius:14px; padding:.7rem .9rem; }
  /* Lead card */
  .lead-card { border:1px solid rgba(128,128,128,.25); border-radius:16px;
      padding:1rem 1.1rem; margin-bottom:.9rem; background:rgba(128,128,128,.04); }
  .lead-card h4 { margin:0 0 .3rem; font-size:1.1rem; }
  .lead-meta { font-size:.85rem; opacity:.8; margin-bottom:.6rem; }
  .badge { display:inline-block; padding:.15rem .55rem; border-radius:999px;
      font-size:.72rem; font-weight:700; margin-right:.35rem; }
  .badge-high { background:#C6EFCE; color:#006100; }
  .badge-medium { background:#FFEB9C; color:#9C6500; }
  .badge-low { background:#E2E3E5; color:#41464b; }
  .badge-status { background:rgba(31,58,95,.12); color:inherit; }
  .card-actions a { display:inline-block; text-decoration:none; font-weight:600;
      padding:.5rem .9rem; border-radius:10px; margin:.25rem .4rem .1rem 0; font-size:.9rem; }
  .act-call { background:#1F3A5F; color:#fff !important; }
  .act-wa { background:#25D366; color:#fff !important; }
  .act-web { background:rgba(128,128,128,.18); color:inherit !important; }
  @media (max-width: 640px) { .block-container { padding:1rem .6rem; }
      .hero h1 { font-size:1.3rem; } }
</style>
"""

_DARK_CSS = """
<style>
  .stApp { background-color:#0e1117; color:#fafafa; }
  section[data-testid="stSidebar"] { background-color:#161a23; }
  .lead-card { background:rgba(255,255,255,.03); border-color:rgba(255,255,255,.12); }
  div[data-testid="stMetric"] {
      background:rgba(255,255,255,.04); border-color:rgba(255,255,255,.12); }
</style>
"""


# -- bootstrap -------------------------------------------------------------


def _load_secrets_into_env() -> None:
    """Copy Streamlit Cloud secrets into the environment before settings load."""
    try:
        secrets = st.secrets
    except Exception:  # noqa: BLE001 - no secrets file present (local dev)
        return
    for key in _SECRET_KEYS:
        if key in secrets and not os.environ.get(key):
            os.environ[key] = str(secrets[key])


def _init_state() -> None:
    st.session_state.setdefault("leads", [])
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("dark_mode", False)


def _settings() -> Settings:
    if "settings" not in st.session_state:
        st.session_state.settings = Settings()
    settings: Settings = st.session_state.settings
    return settings


def _check_password(settings_password: str | None) -> bool:
    """Optional password gate (set APP_PASSWORD in secrets to enable)."""
    if not settings_password:
        return True
    if st.session_state.get("authed"):
        return True
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    st.markdown('<div class="hero"><h1>🔒 Lead Intelligence</h1>'
                '<p>Enter the access password to continue.</p></div>', unsafe_allow_html=True)
    entered = st.text_input("Password", type="password")
    if entered and entered == settings_password:
        st.session_state.authed = True
        st.rerun()
    elif entered:
        st.error("Incorrect password.")
    return False


# -- sidebar ---------------------------------------------------------------


def _render_sidebar(settings: Settings) -> None:
    st.sidebar.title("🔍 Lead Intelligence")
    st.session_state.dark_mode = st.sidebar.toggle("🌙 Dark mode", value=st.session_state.dark_mode)

    st.sidebar.header("Search")
    provider_values = [DataProvider.GOOGLE_PLACES.value, DataProvider.APIFY_GMAPS.value]
    default_index = (
        provider_values.index(settings.default_provider.value)
        if settings.default_provider.value in provider_values else 0
    )
    provider_label = st.sidebar.selectbox("Provider", provider_values, index=default_index)
    city = st.sidebar.text_input("City", value=settings.search.city)
    areas_raw = st.sidebar.text_input(
        "Areas (optional, comma-separated)",
        placeholder="Baner, Kothrud, Viman Nagar",
        help="Search each area separately to find different businesses across the city.",
    )
    categories = st.sidebar.multiselect(
        "Categories", options=list(Industry), default=_DEFAULT_CATEGORIES,
        format_func=lambda ind: ind.label,
    )
    min_rating = st.sidebar.slider(
        "Minimum rating", 0.0, 5.0, float(settings.search.min_rating), 0.1
    )
    min_reviews = st.sidebar.number_input(
        "Minimum reviews", 0, 10000, int(settings.search.min_reviews)
    )
    max_results = st.sidebar.slider("Max results per search", 5, 120, 20, 5)
    accumulate = st.sidebar.toggle(
        "➕ Add to existing results", value=False,
        help="Keep previous results and merge new ones (de-duplicated) instead of replacing.",
    )

    if st.sidebar.button("🚀 Generate", type="primary", use_container_width=True):
        areas = [a.strip() for a in areas_raw.split(",") if a.strip()]
        _run_pipeline(
            settings,
            provider=DataProvider(provider_label),
            accumulate=accumulate,
            config=PipelineConfig(
                categories=categories or _DEFAULT_CATEGORIES, city=city, areas=areas,
                min_rating=min_rating, min_reviews=int(min_reviews),
                max_results_per_category=int(max_results),
            ),
        )
    if st.sidebar.button("🧪 Sample data", use_container_width=True):
        st.session_state.leads = sample_leads(settings)
        st.session_state.logs = ["Loaded sample data."]
    if st.session_state.leads and st.sidebar.button("🗑️ Clear results", use_container_width=True):
        st.session_state.leads = []
        st.session_state.logs = []

    with st.sidebar.expander("⚙️ Settings"):
        llm_mode = "Claude" if settings.anthropic_api_key else "templates"
        st.write(f"**Agency:** {settings.agency.name}")
        st.write(f"**Outreach copy:** {llm_mode}")
        st.caption("Edit `.env` or Streamlit secrets to change keys, agency, and pricing.")


def _run_pipeline(
    settings: Settings, *, provider: DataProvider, config: PipelineConfig, accumulate: bool
) -> None:
    st.session_state.logs = []
    progress = st.sidebar.progress(0.0, text="Starting…")
    logs = st.session_state.logs

    def on_progress(event: ProgressEvent) -> None:
        logs.append(f"[{event.stage}] {event.message}")
        progress.progress(min(event.fraction, 1.0), text=event.message)

    try:
        pipeline = build_pipeline(settings.model_copy(update={"default_provider": provider}))
        result = pipeline.run(config, on_progress=on_progress)
        if accumulate and st.session_state.leads:
            st.session_state.leads = merge_leads(st.session_state.leads, result.leads)
        else:
            st.session_state.leads = result.leads
        logs.append(
            f"Discovered {result.discovered}, deduped to {result.deduplicated}, "
            f"{len(result.leads)} new leads, {result.skipped} skipped. "
            f"Total now: {len(st.session_state.leads)}."
        )
    except LeadIntelError as exc:
        st.sidebar.error(str(exc))
        logs.append(f"ERROR: {exc}")
    finally:
        progress.empty()


# -- main panels -----------------------------------------------------------


def _render_dashboard(leads: list[Lead]) -> None:
    no_site = sum(1 for x in leads if x.website_status == WebsiteStatus.NO_WEBSITE)
    high = sum(1 for x in leads if x.is_high_priority)
    ratings = [x.business.ratings.rating for x in leads if x.business.ratings.rating is not None]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    r1c1, r1c2 = st.columns(2)
    r1c1.metric("Total Businesses", len(leads))
    r1c2.metric("🔥 High Priority", high)
    r2c1, r2c2 = st.columns(2)
    r2c1.metric("No Website", no_site)
    r2c2.metric("Avg Rating", avg_rating)
    st.bar_chart(priority_counts(leads), color="#1F3A5F")


def _badge(priority: LeadPriority | None) -> str:
    if priority is None:
        return ""
    cls = {"high": "badge-high", "medium": "badge-medium", "low": "badge-low"}[priority.value]
    return f'<span class="badge {cls}">{priority.value.title()}</span>'


def _render_lead_cards(leads: list[Lead]) -> None:
    """Mobile-friendly cards with tap-to-call and tap-to-WhatsApp actions."""
    for lead in leads:
        b = lead.business
        wa_msg = lead.ai_content.whatsapp_message if lead.ai_content else ""
        tel = tel_link(b.contact.phone)
        wa = whatsapp_link(b.contact.phone, wa_msg)
        status = lead.website_status.value.replace("_", " ").title()
        score = round(lead.website_score.total) if lead.website_score else "—"
        lead_val = lead.lead_score.value if lead.lead_score else "—"
        pkg = lead.recommendation.package.label if lead.recommendation else "—"

        actions = ""
        if tel:
            actions += f'<a class="act-call" href="{tel}">📞 Call</a>'
        if wa:
            actions += f'<a class="act-wa" href="{wa}" target="_blank">💬 WhatsApp</a>'
        if b.contact.website:
            web = html.escape(b.contact.website)
            actions += f'<a class="act-web" href="{web}" target="_blank">🌐 Site</a>'

        st.markdown(
            f'<div class="lead-card">'
            f'<h4>{html.escape(b.name)}</h4>'
            f'<div class="lead-meta">{html.escape(b.industry.label)} · '
            f'{html.escape(b.area or b.city or "")} · '
            f'⭐ {b.ratings.rating or "—"} ({b.ratings.review_count})</div>'
            f'<div>{_badge(lead.priority)}'
            f'<span class="badge badge-status">{status}</span>'
            f'<span class="badge badge-status">Web {score}/100</span>'
            f'<span class="badge badge-status">Lead {lead_val}/10</span>'
            f'<span class="badge badge-status">{pkg}</span></div>'
            f'<div class="card-actions">{actions}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if lead.ai_content:
            with st.expander("✉️ Outreach content"):
                t = st.tabs(["WhatsApp", "Email", "Cold Call", "Follow-ups"])
                t[0].code(lead.ai_content.whatsapp_message)
                t[1].code(lead.ai_content.email)
                t[2].code(lead.ai_content.cold_call_script)
                t[3].code("\n\n---\n\n".join(lead.ai_content.follow_ups))


def _render_leads(leads: list[Lead]) -> None:
    st.subheader("📋 Leads")
    c1, c2, c3 = st.columns(3)
    search = c1.text_input("Search", placeholder="name, category, area")
    status_opts = c2.multiselect("Website status", list(WebsiteStatus),
                                 format_func=lambda s: s.value.replace("_", " ").title())
    prio_opts = c3.multiselect("Priority", list(LeadPriority),
                               format_func=lambda p: p.value.title())
    filtered = filter_leads(leads, search=search, statuses=set(status_opts) or None,
                            priorities=set(prio_opts) or None)
    st.caption(f"Showing {len(filtered)} of {len(leads)} leads")

    view = st.radio("View", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")
    if view == "Cards":
        _render_lead_cards(filtered)
    else:
        st.dataframe(leads_to_dataframe(filtered, columns=TABLE_COLUMNS),
                     use_container_width=True, hide_index=True)


def _render_downloads(settings: Settings, leads: list[Lead]) -> None:
    st.subheader("⬇️ Download")
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("CRM.xlsx", downloads.crm_excel_bytes(leads, settings.revenue),
                       file_name="CRM.xlsx", mime=downloads.EXCEL_MIME, use_container_width=True)
    c2.download_button("CSV", downloads.csv_bytes(leads), file_name="leads.csv",
                       mime="text/csv", use_container_width=True)
    c3.download_button("JSON", downloads.json_bytes(leads), file_name="leads.json",
                       mime="application/json", use_container_width=True)
    c4.download_button("PDFs.zip", downloads.pdf_zip_bytes(leads, settings.agency),
                       file_name="audits.zip", mime="application/zip", use_container_width=True)


def _render_logs() -> None:
    if st.session_state.logs:
        with st.expander("📜 Progress logs"):
            st.code("\n".join(st.session_state.logs))


def main() -> None:
    st.set_page_config(page_title="Lead Intelligence", page_icon="🔍",
                       layout="centered", initial_sidebar_state="expanded")
    _load_secrets_into_env()
    _init_state()

    password = os.environ.get("APP_PASSWORD") or ""
    if not _check_password(password):
        return

    settings = _settings()
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    if st.session_state.dark_mode:
        st.markdown(_DARK_CSS, unsafe_allow_html=True)

    _render_sidebar(settings)
    st.markdown(
        '<div class="hero"><h1>AI Lead Intelligence</h1>'
        '<p>Find local businesses that need a website — audited, scored, and ready to contact.</p>'
        '</div>', unsafe_allow_html=True,
    )

    leads = st.session_state.leads
    if not leads:
        st.info("👈 Pick categories and tap **Generate**, or tap **Sample data** to explore.")
        _render_logs()
        return

    _render_dashboard(leads)
    _render_downloads(settings, leads)
    _render_leads(leads)
    _render_logs()


if __name__ == "__main__":
    main()
