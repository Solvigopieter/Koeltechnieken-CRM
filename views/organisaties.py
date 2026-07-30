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
            zoek = st.text_input("Zoeken", placeholder="naam, klantnummer of gemeente")
        sub = orgs.copy()
        if not sub.empty:
            if type_filter:
                sub = sub[sub["type"].isin(type_filter)]
            if zoek.strip():
                z = zoek.lower()
                sub = sub[sub["naam"].astype(str).str.lower().str.contains(z)
                          | sub["gemeente"].astype(str).str.lower().str.contains(z)
                          | sub["klantnummer"].astype(str).str.lower().str.contains(z)]
        if sub.empty:
            st.info("Geen organisaties gevonden.")
        else:
            st.dataframe(
                sub[["klantnummer", "naam", "type", "gemeente", "email", "telefoon",
                    "status", "relatietype", "btw", "notities"]],
                use_container_width=True, hide_index=True)
            helpers.export_knop(sub, "organisaties.xlsx")

    def _formulier(o: dict, form_key: str, bewerken: bool = False):
        with st.form(form_key):
            c0a, c0b = st.columns([1, 3])
            with c0a:
                standaard_nr = o.get("klantnummer") or helpers.volgend_klantnummer()
                klantnummer = st.text_input("Klantnummer", value=standaard_nr,
                                            help="Automatisch voorgesteld (AC0001, AC0002, ...) — vrij aan te passen.")
            with c0b:
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
                                      if o.get("status") in helpers.ORG_STATUSSEN else 1)
                relatietype = st.selectbox("Relatietype", helpers.RELATIETYPES,
                                           index=helpers.RELATIETYPES.index(o.get("relatietype"))
                                           if o.get("relatietype") in helpers.RELATIETYPES else 0)
            c4, c5 = st.columns(2)
            with c4:
                email = st.text_input("E-mail", value=o.get("email") or "")
            with c5:
                telefoon = st.text_input("Telefoon", value=o.get("telefoon") or "")
            sector = st.text_input("Sector", value=o.get("sector") or "",
                                   placeholder="bv. Particulier, Horeca, Bouw")
            website = st.text_input("Website", value=o.get("website") or "")
            notities = st.text_area("Notities", value=o.get("notities") or "", height=80)
            if bewerken:
                k1, k2 = st.columns(2)
                opslaan = k1.form_submit_button("Opslaan", type="primary")
                weg = k2.form_submit_button("🗑️ Verwijder")
            else:
                opslaan = st.form_submit_button("Toevoegen", type="primary")
                weg = False
        data = dict(klantnummer=klantnummer.strip(), naam=naam.strip(), type=otype, btw=btw,
                    adres=adres, gemeente=gemeente, email=email, telefoon=telefoon,
                    sector=sector, website=website, status=status,
                    relatietype=relatietype, notities=notities)
        return opslaan, weg, data

    with tab_nieuw:
        opslaan, _, data = _formulier({}, "org_nieuw")
        if opslaan:
            if not data["naam"]:
                st.error("Naam is verplicht.")
            else:
                db.voeg_toe("organisaties", data)
                st.success(f"Organisatie {data['klantnummer']} toegevoegd.")
                st.rerun()

    with tab_bewerk:
        if orgs.empty:
            st.info("Nog geen organisaties.")
            return
        keuze = st.selectbox("Kies organisatie", orgs["id"].tolist(),
                             format_func=lambda i: orgs.set_index("id").loc[i, "naam"])
        o = db.haal_rij("organisaties", int(keuze)) or {}
        opslaan, weg, data = _formulier(o, "org_bewerk", bewerken=True)
        if opslaan:
            db.werk_bij("organisaties", int(keuze), data)
            st.success("Organisatie bijgewerkt.")
            st.rerun()
        if weg:
            db.verwijder("organisaties", int(keuze))
            st.success("Organisatie verwijderd.")
            st.rerun()
