from datetime import date, timedelta

import streamlit as st

import db
import helpers

_FREQ_MAANDEN = {"Jaarlijks": 12, "Halfjaarlijks": 6, "Tweejaarlijks": 24, "Na oproep": None}


def toon():
    st.title("Onderhoudscontracten")
    st.caption("Terugkerend werk = stabiele omzet. Volg hier wie wanneer een beurt moet krijgen.")

    tab_lijst, tab_nieuw, tab_bewerk = st.tabs(["📋 Contracten", "➕ Nieuw", "✏️ Bewerken / beurt registreren"])

    contracten = db.query_df(
        "SELECT c.*, o.naam AS organisatie, i.naam AS installatie "
        "FROM onderhoudscontracten c "
        "LEFT JOIN organisaties o ON o.id = c.organisatie_id "
        "LEFT JOIN installaties i ON i.id = c.installatie_id "
        "ORDER BY c.volgende_beurt")

    with tab_lijst:
        status_filter = st.multiselect("Status", helpers.ONDERHOUD_STATUSSEN, default=["Actief", "Voorstel"])
        sub = contracten.copy()
        if not sub.empty and status_filter:
            sub = sub[sub["status"].isin(status_filter)]
        if sub.empty:
            st.info("Geen contracten met deze filters.")
        else:
            vandaag = date.today().isoformat()
            grens30 = (date.today() + timedelta(days=30)).isoformat()
            def _label(rij):
                vb = str(rij.get("volgende_beurt") or "")
                if not vb:
                    return "—"
                if vb < vandaag:
                    return f"🔴 {vb} (te laat)"
                if vb <= grens30:
                    return f"🟡 {vb} (binnen 30 d.)"
                return f"🟢 {vb}"
            toon_df = sub[["organisatie", "installatie", "toestel", "frequentie",
                           "prijs_per_beurt", "laatste_beurt", "volgende_beurt", "status"]].copy()
            toon_df["volgende_beurt"] = sub.apply(_label, axis=1)
            toon_df["prijs_per_beurt"] = toon_df["prijs_per_beurt"].apply(helpers.euro)
            st.dataframe(toon_df, use_container_width=True, hide_index=True)
            jaaromzet = 0.0
            for _, c in sub[sub["status"] == "Actief"].iterrows():
                maanden = _FREQ_MAANDEN.get(str(c.get("frequentie")), None)
                if maanden:
                    jaaromzet += float(c.get("prijs_per_beurt") or 0) * (12 / maanden)
            st.metric("Geschatte jaaromzet actieve contracten", helpers.euro(jaaromzet))
            helpers.export_knop(sub, "onderhoudscontracten.xlsx")

    with tab_nieuw:
        orgs = db.organisatie_opties()
        installaties = db.installatie_opties()
        with st.form("contract_nieuw"):
            c1, c2, c3 = st.columns(3)
            with c1:
                organisatie_id = st.selectbox("Klant", list(orgs), format_func=orgs.get)
                installatie_id = st.selectbox("Installatie-adres", list(installaties),
                                              format_func=installaties.get)
            with c2:
                toestel = st.text_input("Toestel", placeholder="bv. Panasonic TZ 3,5 kW (2026)")
                frequentie = st.selectbox("Frequentie", helpers.FREQUENTIES)
            with c3:
                prijs = st.number_input("Prijs per beurt (EUR excl.)", min_value=0.0, step=5.0, value=145.0)
                volgende = st.date_input("Eerste/volgende beurt", value=date.today() + timedelta(days=365))
            status = st.selectbox("Status", helpers.ONDERHOUD_STATUSSEN, index=0)
            notities = st.text_area("Notities", height=60)
            if st.form_submit_button("Contract toevoegen", type="primary"):
                db.voeg_toe("onderhoudscontracten", dict(
                    organisatie_id=organisatie_id or None, installatie_id=installatie_id or None,
                    toestel=toestel, frequentie=frequentie, prijs_per_beurt=prijs,
                    volgende_beurt=volgende.isoformat(), status=status, notities=notities))
                st.success("Onderhoudscontract toegevoegd.")
                st.rerun()

    with tab_bewerk:
        if contracten.empty:
            st.info("Nog geen contracten.")
            return
        keuze = st.selectbox(
            "Kies contract", contracten["id"].tolist(),
            format_func=lambda i: f"{contracten.set_index('id').loc[i, 'organisatie'] or 'Klant'} — "
                                  f"{contracten.set_index('id').loc[i, 'toestel'] or ''}")
        c = db.haal_rij("onderhoudscontracten", int(keuze)) or {}

        st.markdown("#### ✅ Beurt uitgevoerd?")
        st.caption("Registreer de beurt: 'laatste beurt' wordt vandaag, 'volgende beurt' schuift op volgens de frequentie.")
        if st.button("Beurt vandaag registreren", type="primary"):
            maanden = _FREQ_MAANDEN.get(str(c.get("frequentie")), 12) or 12
            volgende = date.today() + timedelta(days=int(maanden * 30.4))
            db.werk_bij("onderhoudscontracten", int(keuze), dict(
                laatste_beurt=date.today().isoformat(),
                volgende_beurt=volgende.isoformat()))
            st.success(f"Beurt geregistreerd — volgende beurt: {volgende.isoformat()}")
            st.rerun()

        st.divider()
        with st.form("contract_bewerk"):
            c1, c2, c3 = st.columns(3)
            with c1:
                toestel = st.text_input("Toestel", value=c.get("toestel") or "")
                frequentie = st.selectbox("Frequentie", helpers.FREQUENTIES,
                                          index=helpers.FREQUENTIES.index(c.get("frequentie"))
                                          if c.get("frequentie") in helpers.FREQUENTIES else 0)
            with c2:
                prijs = st.number_input("Prijs per beurt (EUR excl.)", min_value=0.0, step=5.0,
                                        value=float(c.get("prijs_per_beurt") or 0))
                status = st.selectbox("Status", helpers.ONDERHOUD_STATUSSEN,
                                      index=helpers.ONDERHOUD_STATUSSEN.index(c.get("status"))
                                      if c.get("status") in helpers.ONDERHOUD_STATUSSEN else 0)
            with c3:
                try:
                    vb = date.fromisoformat(str(c.get("volgende_beurt")))
                except (ValueError, TypeError):
                    vb = date.today()
                volgende = st.date_input("Volgende beurt", value=vb)
            notities = st.text_area("Notities", value=c.get("notities") or "", height=60)
            k1, k2 = st.columns(2)
            opslaan = k1.form_submit_button("Opslaan", type="primary")
            weg = k2.form_submit_button("🗑️ Verwijder contract")
        if opslaan:
            db.werk_bij("onderhoudscontracten", int(keuze), dict(
                toestel=toestel, frequentie=frequentie, prijs_per_beurt=prijs,
                volgende_beurt=volgende.isoformat(), status=status, notities=notities))
            st.success("Contract bijgewerkt.")
            st.rerun()
        if weg:
            db.verwijder("onderhoudscontracten", int(keuze))
            st.success("Contract verwijderd.")
            st.rerun()
