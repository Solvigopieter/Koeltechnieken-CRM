from datetime import date

import streamlit as st

import db
import helpers


def toon():
    st.title("Communicatielog")

    tab_lijst, tab_nieuw = st.tabs(["📋 Log", "➕ Nieuwe notitie"])

    log = db.query_df(
        "SELECT c.*, o.naam AS organisatie, d.titel AS deal, k.naam AS contact "
        "FROM communicatie c "
        "LEFT JOIN organisaties o ON o.id = c.organisatie_id "
        "LEFT JOIN deals d ON d.id = c.deal_id "
        "LEFT JOIN contacten k ON k.id = c.contact_id ORDER BY c.datum DESC")

    with tab_lijst:
        zoek = st.text_input("Zoeken", placeholder="klant, deal of tekst")
        sub = log.copy()
        if not sub.empty and zoek.strip():
            z = zoek.lower()
            sub = sub[sub["organisatie"].astype(str).str.lower().str.contains(z)
                      | sub["deal"].astype(str).str.lower().str.contains(z)
                      | sub["samenvatting"].astype(str).str.lower().str.contains(z)]
        if sub.empty:
            st.info("Geen communicatie gevonden.")
        else:
            for _, c in sub.iterrows():
                st.markdown(
                    f'<div class="kanban-kaart" style="--kaartkleur:#5B6B8C">'
                    f'<b>{c["datum"]} · {c.get("type") or "Notitie"}</b> — '
                    f'{c.get("organisatie") or "—"}'
                    f'{" · " + str(c.get("contact")) if c.get("contact") else ""}<br>'
                    f'{c.get("samenvatting") or ""}'
                    f'{("<br><span class=\"kaart-meta\">Volgende stap: " + str(c.get("volgende_stap")) + "</span>") if c.get("volgende_stap") else ""}'
                    f'</div>', unsafe_allow_html=True)
            helpers.export_knop(sub, "communicatie.xlsx")

    with tab_nieuw:
        orgs = db.organisatie_opties()
        deals = db.deal_opties()
        with st.form("comm_nieuw"):
            c1, c2, c3 = st.columns(3)
            with c1:
                datum = st.date_input("Datum", value=date.today())
                ctype = st.selectbox("Type", helpers.COMM_TYPES)
            with c2:
                organisatie_id = st.selectbox("Organisatie", list(orgs), format_func=orgs.get)
            with c3:
                deal_id = st.selectbox("Deal", list(deals), format_func=deals.get)
            contacts = db.contact_opties(organisatie_id if organisatie_id else None)
            contact_id = st.selectbox("Contactpersoon", list(contacts), format_func=contacts.get)
            samenvatting = st.text_area("Samenvatting*", height=80)
            volgende_stap = st.text_input("Volgende stap")
            if st.form_submit_button("Notitie opslaan", type="primary"):
                if not samenvatting.strip():
                    st.error("Samenvatting is verplicht.")
                else:
                    db.voeg_toe("communicatie", dict(
                        datum=datum.isoformat(), type=ctype,
                        organisatie_id=organisatie_id or None, deal_id=deal_id or None,
                        contact_id=contact_id or None,
                        samenvatting=samenvatting.strip(), volgende_stap=volgende_stap))
                    st.success("Notitie opgeslagen.")
                    st.rerun()
