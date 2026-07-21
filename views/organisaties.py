import streamlit as st

import db
import helpers


def toon():
    st.title("Organisaties")

    tab_lijst, tab_nieuw, tab_bewerk = st.tabs(["📋 Lijst", "➕ Nieuw", "✏️ Bewerken"])

    orgs = db.query_df("SELECT * FROM organisaties ORDER BY naam")

    with tab_lijst:
        f1, f2 = st.columns(2)
        with f1:
            type_filter = st.multiselect("Type", helpers.ORG_TYPES, default=[])
        with f2:
            zoek = st.text_input("Zoeken", placeholder="naam of gemeente")
        sub = orgs.copy()
        if not sub.empty:
            if type_filter:
                sub = sub[sub["type"].isin(type_filter)]
            if zoek.strip():
                z = zoek.lower()
                sub = sub[sub["naam"].astype(str).str.lower().str.contains(z)
                          | sub["gemeente"].astype(str).str.lower().str.contains(z)]
        if sub.empty:
            st.info("Geen organisaties gevonden.")
        else:
            st.dataframe(
                sub[["naam", "type", "gemeente", "status", "relatietype", "btw", "notities"]],
                use_container_width=True, hide_index=True)
            helpers.export_knop(sub, "organisaties.xlsx")

    with tab_nieuw:
        with st.form("org_nieuw"):
            naam = st.text_input("Naam*")
            c1, c2, c3 = st.columns(3)
            with c1:
                otype = st.selectbox("Type", helpers.ORG_TYPES)
                btw = st.text_input("BTW-nummer")
            with c2:
                adres = st.text_input("Adres")
                gemeente = st.text_input("Gemeente")
            with c3:
                status = st.selectbox("Status", helpers.ORG_STATUSSEN, index=1)
                relatietype = st.selectbox("Relatietype", helpers.RELATIETYPES)
            sector = st.text_input("Sector", placeholder="bv. Particulier, Horeca, Bouw")
            website = st.text_input("Website")
            notities = st.text_area("Notities", height=80)
            if st.form_submit_button("Toevoegen", type="primary"):
                if not naam.strip():
                    st.error("Naam is verplicht.")
                else:
                    db.voeg_toe("organisaties", dict(
                        naam=naam.strip(), type=otype, btw=btw, adres=adres,
                        gemeente=gemeente, sector=sector, website=website,
                        status=status, relatietype=relatietype, notities=notities))
                    st.success("Organisatie toegevoegd.")
                    st.rerun()

    with tab_bewerk:
        if orgs.empty:
            st.info("Nog geen organisaties.")
            return
        keuze = st.selectbox("Kies organisatie", orgs["id"].tolist(),
                             format_func=lambda i: orgs.set_index("id").loc[i, "naam"])
        o = db.haal_rij("organisaties", int(keuze)) or {}
        with st.form("org_bewerk"):
            naam = st.text_input("Naam*", value=o.get("naam") or "")
            c1, c2, c3 = st.columns(3)
            with c1:
                otype = st.selectbox("Type", helpers.ORG_TYPES,
                                     index=helpers.ORG_TYPES.index(o.get("type"))
                                     if o.get("type") in helpers.ORG_TYPES else 0)
                btw = st.text_input("BTW-nummer", value=o.get("btw") or "")
            with c2:
                adres = st.text_input("Adres", value=o.get("adres") or "")
                gemeente = st.text_input("Gemeente", value=o.get("gemeente") or "")
            with c3:
                status = st.selectbox("Status", helpers.ORG_STATUSSEN,
                                      index=helpers.ORG_STATUSSEN.index(o.get("status"))
                                      if o.get("status") in helpers.ORG_STATUSSEN else 0)
                relatietype = st.selectbox("Relatietype", helpers.RELATIETYPES,
                                           index=helpers.RELATIETYPES.index(o.get("relatietype"))
                                           if o.get("relatietype") in helpers.RELATIETYPES else 0)
            sector = st.text_input("Sector", value=o.get("sector") or "")
            website = st.text_input("Website", value=o.get("website") or "")
            notities = st.text_area("Notities", value=o.get("notities") or "", height=80)
            k1, k2 = st.columns(2)
            opslaan = k1.form_submit_button("Opslaan", type="primary")
            weg = k2.form_submit_button("🗑️ Verwijder")
        if opslaan:
            db.werk_bij("organisaties", int(keuze), dict(
                naam=naam.strip(), type=otype, btw=btw, adres=adres, gemeente=gemeente,
                sector=sector, website=website, status=status,
                relatietype=relatietype, notities=notities))
            st.success("Organisatie bijgewerkt.")
            st.rerun()
        if weg:
            db.verwijder("organisaties", int(keuze))
            st.success("Organisatie verwijderd.")
            st.rerun()
