from datetime import date

import streamlit as st

import db
import helpers


def toon():
    st.title("Uitvoering / Jobs")

    tab_lijst, tab_nieuw = st.tabs(["📋 Jobs", "➕ Nieuwe job"])

    jobs = db.query_df(
        "SELECT j.*, d.titel AS deal, i.naam AS installatie FROM jobs j "
        "LEFT JOIN deals d ON d.id = j.deal_id "
        "LEFT JOIN installaties i ON i.id = j.installatie_id ORDER BY j.datum")

    with tab_lijst:
        status_filter = st.multiselect("Status", helpers.JOB_STATUSSEN, default=["Gepland", "Bezig"])
        sub = jobs.copy()
        if not sub.empty and status_filter:
            sub = sub[sub["status"].isin(status_filter)]
        if sub.empty:
            st.info("Geen jobs met deze filters.")
        else:
            for _, j in sub.iterrows():
                with st.expander(f"{j['datum']} — {j.get('installatie') or j.get('deal') or 'Job'} "
                                 f"({j['status']})"):
                    st.markdown(f"**Team:** {j.get('team') or '—'}")
                    st.markdown(f"**Toestellen:** {j.get('toestellen') or '—'}")
                    st.markdown(f"**Werkzaamheden:** {j.get('werkzaamheden') or '—'}")
                    st.markdown(f"**Indienststelling:** {j.get('indienststelling') or '—'}")
                    if j.get("werkverslag"):
                        st.info(f"**Werkverslag:** {j['werkverslag']}")
                    c1, c2 = st.columns([2, 3])
                    with c1:
                        nieuw_status = st.selectbox(
                            "Status", helpers.JOB_STATUSSEN,
                            index=helpers.JOB_STATUSSEN.index(j["status"])
                            if j["status"] in helpers.JOB_STATUSSEN else 0,
                            key=f"job_status_{j['id']}")
                    with c2:
                        verslag = st.text_input("Werkverslag bijwerken",
                                                value=j.get("werkverslag") or "",
                                                key=f"job_verslag_{j['id']}")
                    if st.button("Opslaan", key=f"job_save_{j['id']}", type="primary"):
                        db.werk_bij("jobs", int(j["id"]),
                                    {"status": nieuw_status, "werkverslag": verslag})
                        if nieuw_status == "Uitgevoerd" and j.get("deal_id"):
                            helpers.wijzig_stadium(int(j["deal_id"]), "Uitgevoerd")
                        st.success("Job bijgewerkt.")
                        st.rerun()
            helpers.export_knop(sub, "jobs.xlsx")

    with tab_nieuw:
        deals = db.deal_opties()
        installaties = db.installatie_opties()
        with st.form("job_nieuw"):
            c1, c2, c3 = st.columns(3)
            with c1:
                datum = st.date_input("Datum", value=date.today())
            with c2:
                deal_id = st.selectbox("Deal", list(deals), format_func=deals.get)
            with c3:
                installatie_id = st.selectbox("Installatie-adres", list(installaties),
                                              format_func=installaties.get)
            team = st.text_input("Team", placeholder="bv. Pieter + hulp")
            toestellen = st.text_input("Toestellen", placeholder="bv. Panasonic TZ 3,5 kW + TZ 2,5 kW")
            werkzaamheden = st.text_area("Werkzaamheden", height=70,
                                         placeholder="bv. plaatsing 2 mono-splits, leidingwerk via zolder")
            indienststelling = st.text_area(
                "Indienststelling-checklist", height=60,
                value="Vacumeren · lektest · opstart · parameters · uitleg klant")
            if st.form_submit_button("Job inplannen", type="primary"):
                db.voeg_toe("jobs", dict(
                    deal_id=deal_id or None, installatie_id=installatie_id or None,
                    datum=datum.isoformat(), team=team, toestellen=toestellen,
                    werkzaamheden=werkzaamheden, indienststelling=indienststelling,
                    status="Gepland"))
                if deal_id:
                    helpers.wijzig_stadium(int(deal_id), "In uitvoering")
                st.success("Job ingepland"
                           + (" — deal naar 'In uitvoering'." if deal_id else "."))
                st.rerun()
