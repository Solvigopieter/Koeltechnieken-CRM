"""
Solvigo Koeltechnieken CRM – hoofdapp
Start met:  streamlit run app.py
"""
import streamlit as st

import db
import seed
import helpers
from views import (
    dashboard, pipeline, acties, organisaties, contacten, installaties,
    plaatsbezoeken, offertes, jobs, onderhoud, communicatie,
)

st.set_page_config(
    page_title="Solvigo Koeltechnieken CRM",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()
seed.seed_indien_leeg()

st.markdown(helpers.CSS, unsafe_allow_html=True)

PAGINAS = {
    "Dashboard": dashboard.toon,
    "Pipeline": pipeline.toon,
    "Actieblad": acties.toon,
    "Organisaties": organisaties.toon,
    "Contactpersonen": contacten.toon,
    "Installatie-adressen": installaties.toon,
    "Plaatsbezoeken": plaatsbezoeken.toon,
    "Offertes": offertes.toon,
    "Uitvoering / Jobs": jobs.toon,
    "Onderhoudscontracten": onderhoud.toon,
    "Communicatielog": communicatie.toon,
}

with st.sidebar:
    from pathlib import Path as _Path
    _logo = _Path(__file__).parent / "logo.png"
    if _logo.exists():
        st.image(str(_logo), width=190)
    else:
        st.markdown("## Solvigo Koeltechnieken")
    st.caption("Airco · warmtepompen · onderhoud")
    st.divider()
    keuze = st.radio("Navigatie", list(PAGINAS.keys()), label_visibility="collapsed")
    st.divider()

    open_deals = db.query_df(
        "SELECT COUNT(*) n FROM deals WHERE stadium NOT IN ('Afgerond','Verloren')")["n"][0]
    telaat = db.query_df(
        "SELECT COUNT(*) n FROM acties WHERE status IN ('Open','Bezig') AND datum < date('now')")["n"][0]
    onderhoud_binnenkort = db.query_df(
        "SELECT COUNT(*) n FROM onderhoudscontracten "
        "WHERE status = 'Actief' AND volgende_beurt <= date('now', '+30 day')")["n"][0]
    st.markdown(f"**{int(open_deals)}** open deals")
    if telaat:
        st.markdown(
            f'<span style="color:#B4443C;font-weight:600;">{int(telaat)} acties te laat</span>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<span style="color:#1E8E5A;">Geen achterstallige acties</span>',
            unsafe_allow_html=True)
    if onderhoud_binnenkort:
        st.markdown(
            f'<span class="accent-geel" style="font-weight:600;">{int(onderhoud_binnenkort)} onderhoud(en) binnen 30 dagen</span>',
            unsafe_allow_html=True)

    import offerte_koppeling
    url = offerte_koppeling.offerte_app_url()
    if url:
        st.divider()
        st.link_button("📄 Open offertegenerator", url, use_container_width=True)

    st.caption(f"Opslag: {db.opslag_label()}")

PAGINAS[keuze]()
