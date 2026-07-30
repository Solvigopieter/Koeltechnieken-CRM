from datetime import date

import streamlit as st

import db
import helpers


def toon():
    st.title("Plaatsbezoeken")
    st.caption("Technisch verslag per bezoek — de basis voor een correcte offerte in de generator.")

    tab_lijst, tab_nieuw = st.tabs(["📋 Verslagen", "➕ Nieuw verslag"])

    bezoeken = db.query_df(
        "SELECT p.*, d.titel AS deal, i.naam AS installatie FROM plaatsbezoeken p "
        "LEFT JOIN deals d ON d.id = p.deal_id "
        "LEFT JOIN installaties i ON i.id = p.installatie_id ORDER BY p.datum DESC")

    with tab_lijst:
        if bezoeken.empty:
            st.info("Nog geen plaatsbezoeken geregistreerd.")
        else:
            for _, b in bezoeken.iterrows():
                with st.expander(f"{b['datum']} — {b.get('installatie') or b.get('deal') or 'Bezoek'}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Aanwezigen:** {b.get('aanwezigen') or '—'}")
                        st.markdown(f"**Gewenste ruimtes:** {b.get('gewenste_ruimtes') or '—'}")
                        st.markdown(f"**Vermogen (inschatting):** {b.get('vermogen_inschatting') or '—'}")
                        st.markdown(f"**Binnenunit:** {b.get('plaats_binnenunit') or '—'}")
                        st.markdown(f"**Buitenunit:** {b.get('plaats_buitenunit') or '—'}")
                        st.markdown(f"**Leidingtracé:** {b.get('leidingtrace') or '—'} "
                                    f"({b.get('leidinglengte_m') or '?'} m)")
                    with c2:
                        st.markdown(f"**Elektrisch:** {b.get('elektrische_aansluiting') or '—'}")
                        st.markdown(f"**Condensafvoer:** {b.get('condensafvoer') or '—'}")
                        st.markdown(f"**Boorwerk:** {b.get('boorwerk') or '—'}")
                        st.markdown(f"**Bereikbaarheid:** {b.get('bereikbaarheid') or '—'}")
                        st.markdown(f"**Hoogtewerker:** {'Ja' if int(b.get('hoogtewerker') or 0) else 'Nee'}")
                    if b.get("technische_opmerkingen"):
                        st.markdown(f"**Technische opmerkingen:** {b['technische_opmerkingen']}")
                    if b.get("conclusie"):
                        st.success(f"**Conclusie:** {b['conclusie']}")
                    if b.get("advies"):
                        st.info(f"**Advies:** {b['advies']}")
            helpers.export_knop(bezoeken, "plaatsbezoeken.xlsx")

    with tab_nieuw:
        deals = db.deal_opties()
        installaties = db.installatie_opties()
        with st.form("bezoek_nieuw"):
            c1, c2, c3 = st.columns(3)
            with c1:
                datum = st.date_input("Datum", value=date.today())
            with c2:
                deal_id = st.selectbox("Deal", list(deals), format_func=deals.get)
            with c3:
                installatie_id = st.selectbox("Installatie-adres", list(installaties),
                                              format_func=installaties.get)
            aanwezigen = st.text_input("Aanwezigen", placeholder="bv. Pieter, klant")
            gewenste_ruimtes = st.text_input("Gewenste ruimtes / scope")
            vermogen_inschatting = st.text_input("Vermogen-inschatting",
                                                 placeholder="bv. 2x 2,5 kW slaapkamers")
            c4, c5 = st.columns(2)
            with c4:
                plaats_binnenunit = st.text_input("Plaats binnenunit(s)")
                leidingtrace = st.text_input("Leidingtracé", placeholder="bv. via zolder + gevel")
                elektrische_aansluiting = st.text_input("Elektrische aansluiting",
                                                        placeholder="bv. mono 230V, kring vrij in kast")
                boorwerk = st.text_input("Boorwerk", placeholder="bv. 2x doorvoer 52mm baksteen")
            with c5:
                plaats_buitenunit = st.text_input("Plaats buitenunit")
                leidinglengte_m = st.number_input("Leidinglengte (m)", min_value=0.0, step=0.5)
                condensafvoer = st.text_input("Condensafvoer", placeholder="bv. gravitair naar afloop / pomp nodig")
                bereikbaarheid = st.text_input("Bereikbaarheid")
            hoogtewerker = st.checkbox("Hoogtewerker nodig")
            technische_opmerkingen = st.text_area("Technische opmerkingen", height=70)
            conclusie = st.text_area("Conclusie", height=60,
                                     placeholder="bv. multi-split 2x2,5kW haalbaar, tracé ok")
            advies = st.text_area("Advies / volgende stap", height=60,
                                  placeholder="bv. offerte opmaken met 6% BTW")
            if st.form_submit_button("Verslag opslaan", type="primary"):
                db.voeg_toe("plaatsbezoeken", dict(
                    deal_id=deal_id or None, installatie_id=installatie_id or None,
                    datum=datum.isoformat(), aanwezigen=aanwezigen,
                    gewenste_ruimtes=gewenste_ruimtes, vermogen_inschatting=vermogen_inschatting,
                    plaats_binnenunit=plaats_binnenunit, plaats_buitenunit=plaats_buitenunit,
                    leidingtrace=leidingtrace, leidinglengte_m=leidinglengte_m,
                    elektrische_aansluiting=elektrische_aansluiting, condensafvoer=condensafvoer,
                    boorwerk=boorwerk, bereikbaarheid=bereikbaarheid,
                    hoogtewerker=int(hoogtewerker),
                    technische_opmerkingen=technische_opmerkingen,
                    conclusie=conclusie, advies=advies))
                if deal_id:
                    helpers.wijzig_stadium(int(deal_id), "Plaatsbezoek uitgevoerd")
                st.success("Verslag opgeslagen"
                           + (" — deal verplaatst naar 'Plaatsbezoek uitgevoerd'." if deal_id else "."))
                st.rerun()
