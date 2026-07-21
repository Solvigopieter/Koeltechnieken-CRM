import streamlit as st

import db
import helpers


def toon():
    st.title("Installatie-adressen")
    st.caption("Per adres: gebouwinfo (bouwjaar → 6% BTW), elektrische aansluiting en bestaande toestellen.")

    tab_lijst, tab_nieuw, tab_bewerk = st.tabs(["📋 Lijst", "➕ Nieuw", "✏️ Bewerken"])

    installaties = db.query_df(
        "SELECT i.*, o.naam AS organisatie FROM installaties i "
        "LEFT JOIN organisaties o ON o.id = i.organisatie_id ORDER BY i.naam")

    with tab_lijst:
        zoek = st.text_input("Zoeken", placeholder="naam, gemeente of klant")
        sub = installaties.copy()
        if not sub.empty and zoek.strip():
            z = zoek.lower()
            sub = sub[sub["naam"].astype(str).str.lower().str.contains(z)
                      | sub["gemeente"].astype(str).str.lower().str.contains(z)
                      | sub["organisatie"].astype(str).str.lower().str.contains(z)]
        if sub.empty:
            st.info("Geen installatie-adressen gevonden.")
        else:
            toon_df = sub[["naam", "organisatie", "gemeente", "type_gebouw", "bouwjaar",
                           "btw_6_ok", "elektrisch", "toestel_type", "merk_model"]].copy()
            toon_df["btw_6_ok"] = toon_df["btw_6_ok"].apply(lambda v: "✅ 6%" if v in (1, "1", True) else "21%")
            toon_df = toon_df.rename(columns={"btw_6_ok": "BTW"})
            st.dataframe(toon_df, use_container_width=True, hide_index=True)
            helpers.export_knop(sub, "installaties.xlsx")

    def _formulier(i: dict, form_key: str, bewerken: bool = False):
        orgs = db.organisatie_opties()
        with st.form(form_key):
            naam = st.text_input("Naam*", value=i.get("naam") or "",
                                 placeholder="bv. Woning Janssens")
            c1, c2, c3 = st.columns(3)
            with c1:
                organisatie_id = st.selectbox("Klant/organisatie", list(orgs), format_func=orgs.get,
                                              index=helpers.sleutel_uit_opties(orgs, i.get("organisatie_id")))
                adres = st.text_input("Adres", value=i.get("adres") or "")
                gemeente = st.text_input("Gemeente", value=i.get("gemeente") or "")
            with c2:
                type_gebouw = st.selectbox("Type gebouw", helpers.GEBOUW_TYPES,
                                           index=helpers.GEBOUW_TYPES.index(i.get("type_gebouw"))
                                           if i.get("type_gebouw") in helpers.GEBOUW_TYPES else 0)
                bouwjaar = st.number_input("Bouwjaar woning", min_value=1850, max_value=2035,
                                           value=int(i.get("bouwjaar") or 2000))
                btw_6_ok = st.checkbox("Ouder dan 10 jaar → 6% BTW mogelijk",
                                       value=bool(int(i.get("btw_6_ok") or 0)))
            with c3:
                elektrisch = st.selectbox("Elektrische aansluiting", helpers.ELEKTRISCH_TYPES,
                                          index=helpers.ELEKTRISCH_TYPES.index(i.get("elektrisch"))
                                          if i.get("elektrisch") in helpers.ELEKTRISCH_TYPES else 3)
                bereikbaarheid = st.text_input("Bereikbaarheid buitenunit",
                                               value=i.get("bereikbaarheid") or "",
                                               placeholder="bv. plat dak via luik / ladder volstaat")
            gewenste_ruimtes = st.text_input("Gewenste ruimtes / scope",
                                             value=i.get("gewenste_ruimtes") or "",
                                             placeholder="bv. 2 slaapkamers + bureau")
            st.markdown("**Bestaand toestel (indien aanwezig)**")
            b1, b2, b3 = st.columns(3)
            with b1:
                bestaand_toestel = st.checkbox("Bestaand toestel aanwezig",
                                               value=bool(int(i.get("bestaand_toestel") or 0)))
                toestel_type = st.selectbox("Type toestel", helpers.TOESTEL_TYPES,
                                            index=helpers.TOESTEL_TYPES.index(i.get("toestel_type"))
                                            if i.get("toestel_type") in helpers.TOESTEL_TYPES else 0)
            with b2:
                merk_model = st.text_input("Merk & model", value=i.get("merk_model") or "")
                vermogen_kw = st.number_input("Vermogen (kW)", min_value=0.0, step=0.5,
                                              value=float(i.get("vermogen_kw") or 0))
            with b3:
                plaatsingsjaar = st.number_input("Plaatsingsjaar", min_value=1990, max_value=2035,
                                                 value=int(i.get("plaatsingsjaar") or 2020))
                koelmiddel = st.text_input("Koelmiddel", value=i.get("koelmiddel") or "",
                                           placeholder="bv. R32, R410A")
            notities = st.text_area("Notities", value=i.get("notities") or "", height=70)
            if bewerken:
                k1, k2 = st.columns(2)
                opslaan = k1.form_submit_button("Opslaan", type="primary")
                weg = k2.form_submit_button("🗑️ Verwijder")
            else:
                opslaan = st.form_submit_button("Toevoegen", type="primary")
                weg = False
        data = dict(naam=naam.strip(), adres=adres, gemeente=gemeente,
                    organisatie_id=organisatie_id or None, type_gebouw=type_gebouw,
                    bouwjaar=int(bouwjaar), btw_6_ok=int(btw_6_ok), elektrisch=elektrisch,
                    gewenste_ruimtes=gewenste_ruimtes, bestaand_toestel=int(bestaand_toestel),
                    toestel_type=toestel_type, merk_model=merk_model,
                    vermogen_kw=vermogen_kw, plaatsingsjaar=int(plaatsingsjaar),
                    koelmiddel=koelmiddel, bereikbaarheid=bereikbaarheid, notities=notities)
        return opslaan, weg, data

    with tab_nieuw:
        opslaan, _, data = _formulier({}, "inst_nieuw")
        if opslaan:
            if not data["naam"]:
                st.error("Naam is verplicht.")
            else:
                db.voeg_toe("installaties", data)
                st.success("Installatie-adres toegevoegd.")
                st.rerun()

    with tab_bewerk:
        if installaties.empty:
            st.info("Nog geen installatie-adressen.")
            return
        keuze = st.selectbox("Kies adres", installaties["id"].tolist(),
                             format_func=lambda i: installaties.set_index("id").loc[i, "naam"])
        i = db.haal_rij("installaties", int(keuze)) or {}
        opslaan, weg, data = _formulier(i, "inst_bewerk", bewerken=True)
        if opslaan:
            db.werk_bij("installaties", int(keuze), data)
            st.success("Installatie-adres bijgewerkt.")
            st.rerun()
        if weg:
            db.verwijder("installaties", int(keuze))
            st.success("Installatie-adres verwijderd.")
            st.rerun()
