from datetime import date, timedelta

import streamlit as st

import db
import helpers


def toon():
    st.title("Actieblad")

    tab_lijst, tab_nieuw, tab_sjablonen = st.tabs(
        ["📋 Acties", "➕ Nieuwe actie", "⚡ Meerdere taken uit sjabloon"])

    acties = db.query_df(
        "SELECT a.*, o.naam AS organisatie, d.titel AS deal FROM acties a "
        "LEFT JOIN organisaties o ON o.id = a.organisatie_id "
        "LEFT JOIN deals d ON d.id = a.deal_id ORDER BY a.datum")

    with tab_lijst:
        f1, f2, f3 = st.columns(3)
        with f1:
            status_filter = st.multiselect("Status", helpers.ACTIE_STATUSSEN, default=["Open", "Bezig"])
        with f2:
            prio_filter = st.multiselect("Prioriteit", helpers.PRIORITEITEN, default=[])
        with f3:
            zoek = st.text_input("Zoeken", placeholder="tekst in actie of klant")

        sub = acties.copy()
        if not sub.empty:
            if status_filter:
                sub = sub[sub["status"].isin(status_filter)]
            if prio_filter:
                sub = sub[sub["prioriteit"].isin(prio_filter)]
            if zoek.strip():
                z = zoek.lower()
                sub = sub[
                    sub["actie"].astype(str).str.lower().str.contains(z)
                    | sub["organisatie"].astype(str).str.lower().str.contains(z)]

        if sub.empty:
            st.info("Geen acties gevonden met deze filters.")
        else:
            for _, a in sub.iterrows():
                laat = helpers.te_laat(a["datum"]) and a["status"] in ("Open", "Bezig")
                c1, c2, c3 = st.columns([5, 1.2, 0.6])
                with c1:
                    datum_html = (f'<span class="telaat">{a["datum"]} — TE LAAT</span>'
                                  if laat else str(a["datum"]))
                    st.markdown(
                        f'<div class="kanban-kaart" style="--kaartkleur:'
                        f'{"#B4443C" if laat else "#2338B0"}">'
                        f'<b>{a["actie"]}</b> {helpers.prioriteit_badge(a["prioriteit"])}<br>'
                        f'<span class="kaart-meta">{a.get("organisatie") or "—"}'
                        f'{" · " + str(a.get("deal")) if a.get("deal") else ""} · {datum_html} · '
                        f'{a["status"]}</span></div>',
                        unsafe_allow_html=True)
                with c2:
                    nieuw_status = st.selectbox(
                        "Status", helpers.ACTIE_STATUSSEN,
                        index=helpers.ACTIE_STATUSSEN.index(a["status"])
                        if a["status"] in helpers.ACTIE_STATUSSEN else 0,
                        key=f"actie_status_{a['id']}", label_visibility="collapsed")
                    if nieuw_status != a["status"]:
                        db.werk_bij("acties", int(a["id"]), {"status": nieuw_status})
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"actie_del_{a['id']}", help="Verwijder deze taak",
                                use_container_width=True):
                        db.verwijder("acties", int(a["id"]))
                        st.rerun()

            # ---- Snel duplicaten opruimen: zelfde omschrijving + zelfde deal ----
            dupes = sub[sub.duplicated(subset=["actie", "deal_id"], keep="first")] if not sub.empty else sub
            if not dupes.empty:
                with st.expander(f"🧹 {len(dupes)} mogelijke duplicaat-taak(en) gevonden — snel opruimen"):
                    st.caption("Taken met exact dezelfde omschrijving én dezelfde deal — "
                              "waarschijnlijk per ongeluk meermaals toegevoegd. De EERSTE "
                              "van elke groep blijft altijd staan, enkel de rest wordt verwijderd.")
                    st.dataframe(dupes[["actie", "deal", "datum", "status"]], use_container_width=True, hide_index=True)
                    if st.button("🗑️ Verwijder deze duplicaten", key="verwijder_dupes"):
                        for did in dupes["id"]:
                            db.verwijder("acties", int(did))
                        st.success(f"{len(dupes)} duplicaten verwijderd.")
                        st.rerun()

            helpers.export_knop(sub.drop(columns=["organisatie_id", "installatie_id",
                                                  "partner_id", "deal_id"], errors="ignore"),
                                "acties.xlsx")

    with tab_nieuw:
        orgs = db.organisatie_opties()
        deals = db.deal_opties()
        with st.form("actie_nieuw"):
            actie = st.text_input("Actie*", placeholder="bv. Klant bellen voor plaatsbezoek")
            c1, c2, c3 = st.columns(3)
            with c1:
                datum = st.date_input("Uitvoeren op", value=date.today())
            with c2:
                prioriteit = st.selectbox("Prioriteit", helpers.PRIORITEITEN, index=1)
            with c3:
                organisatie_id = st.selectbox("Organisatie", list(orgs), format_func=orgs.get)
            deal_id = st.selectbox("Gekoppelde deal", list(deals), format_func=deals.get)
            if st.form_submit_button("Actie toevoegen", type="primary"):
                if not actie.strip():
                    st.error("Actie-omschrijving is verplicht.")
                else:
                    db.voeg_toe("acties", dict(
                        datum=datum.isoformat(), prioriteit=prioriteit,
                        organisatie_id=organisatie_id or None, deal_id=deal_id or None,
                        actie=actie.strip(), status="Open"))
                    st.success("Actie toegevoegd.")
                    st.rerun()

    with tab_sjablonen:
        st.caption("Kies een deal en vink de taken aan die je nodig hebt. De datums vormen een "
                  "keten: pas je er één aan, dan schuiven alle volgende automatisch mee. 🔒 = "
                  "manueel vastgezet.")
        orgs = db.organisatie_opties()
        deals = db.deal_opties()
        c1, c2 = st.columns(2)
        with c1:
            sj_deal_id = st.selectbox("Deal", list(deals), format_func=deals.get, key="sj_deal")
        with c2:
            sj_org_id = st.selectbox("Organisatie (optioneel, indien geen deal)",
                                     list(orgs), format_func=orgs.get, key="sj_org")

        st.markdown("**Taken**")
        gekozen = helpers.sjabloon_keten_ui("sj")

        if st.button("➕ Geselecteerde taken toevoegen", type="primary"):
            if not gekozen:
                st.error("Vink minstens één taak aan.")
            else:
                toegevoegd, overgeslagen = helpers.taken_toevoegen_zonder_duplicaten(
                    sj_deal_id or None, sj_org_id or None, gekozen)
                bericht = f"{toegevoegd} taken toegevoegd."
                if overgeslagen:
                    bericht += f" ({overgeslagen} overgeslagen — stonden al open voor deze deal.)"
                st.success(bericht)
                st.rerun()
