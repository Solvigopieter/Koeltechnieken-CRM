import streamlit as st

import db
import helpers
import offerte_koppeling


def toon():
    st.title("Offertes")

    url = offerte_koppeling.offerte_app_url()
    if url:
        st.link_button("📄 Nieuwe offerte maken in de offertegenerator ↗", url)

    tab_crm, tab_generator, tab_nieuw = st.tabs(
        ["📋 Offertes in CRM", "🔗 Uit de offertegenerator", "➕ Handmatig toevoegen"])

    offertes = db.query_df(
        "SELECT f.*, d.titel AS deal, i.naam AS installatie FROM offertes f "
        "LEFT JOIN deals d ON d.id = f.deal_id "
        "LEFT JOIN installaties i ON i.id = f.installatie_id ORDER BY f.datum DESC")

    # ---------------- CRM-offertes ----------------
    with tab_crm:
        if offertes.empty:
            st.info("Nog geen offertes in het CRM. Importeer ze via het tabblad "
                    "'Uit de offertegenerator' of voeg handmatig toe.")
        else:
            f1, f2 = st.columns(2)
            with f1:
                status_filter = st.multiselect("Status", helpers.OFFERTE_STATUSSEN, default=[])
            with f2:
                zoek = st.text_input("Zoeken", placeholder="nummer, deal of adres")
            sub = offertes.copy()
            if status_filter:
                sub = sub[sub["status"].isin(status_filter)]
            if zoek.strip():
                z = zoek.lower()
                sub = sub[sub["nummer"].astype(str).str.lower().str.contains(z)
                          | sub["deal"].astype(str).str.lower().str.contains(z)
                          | sub["installatie"].astype(str).str.lower().str.contains(z)]
            if sub.empty:
                st.info("Geen offertes met deze filters.")
            else:
                toon_df = sub[["nummer", "type", "deal", "installatie", "totaalprijs",
                               "btw_tarief", "status", "datum", "bron"]].copy()
                toon_df["totaalprijs"] = toon_df["totaalprijs"].apply(helpers.euro)
                st.dataframe(toon_df, use_container_width=True, hide_index=True)
                helpers.export_knop(sub, "offertes.xlsx")

                st.divider()
                st.subheader("Status aanpassen")
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    keuze = st.selectbox("Offerte", sub["id"].tolist(),
                                         format_func=lambda i: str(sub.set_index("id").loc[i, "nummer"]))
                with c2:
                    huidig = sub.set_index("id").loc[keuze, "status"]
                    nieuw = st.selectbox("Nieuwe status", helpers.OFFERTE_STATUSSEN,
                                         index=helpers.OFFERTE_STATUSSEN.index(huidig)
                                         if huidig in helpers.OFFERTE_STATUSSEN else 0)
                with c3:
                    st.write("")
                    st.write("")
                    if st.button("Opslaan", type="primary", use_container_width=True):
                        db.werk_bij("offertes", int(keuze), {"status": nieuw})
                        rij = db.haal_rij("offertes", int(keuze)) or {}
                        if rij.get("deal_id"):
                            if nieuw == "Verstuurd":
                                helpers.wijzig_stadium(int(rij["deal_id"]), "Offerte verstuurd")
                            elif nieuw == "Goedgekeurd":
                                helpers.wijzig_stadium(int(rij["deal_id"]), "Goedgekeurd / in te plannen")
                            elif nieuw == "Verloren":
                                helpers.wijzig_stadium(int(rij["deal_id"]), "Verloren")
                        st.success("Status bijgewerkt (deal-stadium mee aangepast waar logisch).")
                        st.rerun()

    # ---------------- generator-projecten ----------------
    with tab_generator:
        if not offerte_koppeling.koppeling_beschikbaar():
            st.warning("Google-koppeling niet geconfigureerd. Zet in de CRM-secrets hetzelfde "
                       "`[gcp_service_account]`-blok als in de offertegenerator, plus "
                       "`offerte_sheet_name = \"Koeltechnieken offerte\"`.")
        else:
            k1, k2 = st.columns([4, 1])
            with k2:
                if st.button("🔄 Vernieuwen"):
                    offerte_koppeling.ververs_cache()
                    st.rerun()
            projecten = offerte_koppeling.haal_generator_projecten()
            if not projecten:
                st.info("Geen projecten gevonden in de offertegenerator "
                        "(of de sheet is nog niet gedeeld met dit service account).")
            else:
                al_geimporteerd = set()
                if not offertes.empty:
                    al_geimporteerd = set(offertes["generator_id"].dropna().astype(str))
                deals = db.deal_opties()
                installaties = db.installatie_opties()
                st.caption(f"{len(projecten)} project(en) in de offertegenerator. "
                           "Importeer een project om het aan een klant/deal te koppelen.")
                for p in projecten[:30]:
                    pid = str(p.get("id"))
                    geimporteerd = pid in al_geimporteerd
                    with st.expander(
                        f"{'✅ ' if geimporteerd else ''}{p.get('datum')} — {p.get('type')} — "
                        f"{p.get('klant')} — {helpers.euro(p.get('totaal_incl'))}"
                    ):
                        if geimporteerd:
                            st.success("Al geïmporteerd in het CRM.")
                            continue
                        c1, c2 = st.columns(2)
                        with c1:
                            deal_id = st.selectbox("Koppel aan deal", list(deals),
                                                   format_func=deals.get, key=f"gen_deal_{pid}")
                        with c2:
                            installatie_id = st.selectbox("Koppel aan installatie-adres",
                                                          list(installaties),
                                                          format_func=installaties.get,
                                                          key=f"gen_inst_{pid}")
                        status = st.selectbox("Status in CRM", helpers.OFFERTE_STATUSSEN, index=1,
                                              key=f"gen_status_{pid}")
                        if st.button("⬇️ Importeer als offerte", key=f"gen_import_{pid}",
                                     type="primary"):
                            db.voeg_toe("offertes", dict(
                                deal_id=deal_id or None, installatie_id=installatie_id or None,
                                nummer=f"GEN-{pid}", type=p.get("type"),
                                totaalprijs=float(p.get("totaal_incl") or 0),
                                status=status, datum=str(p.get("datum") or ""),
                                bron="Generator", generator_id=pid,
                                opmerkingen=f"Geïmporteerd uit offertegenerator (klant: {p.get('klant')})"))
                            if deal_id and status == "Verstuurd":
                                helpers.wijzig_stadium(int(deal_id), "Offerte verstuurd")
                            st.success("Offerte geïmporteerd.")
                            st.rerun()

    # ---------------- handmatig ----------------
    with tab_nieuw:
        deals = db.deal_opties()
        installaties = db.installatie_opties()
        with st.form("offerte_nieuw"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nummer = st.text_input("Offertenummer", placeholder="bv. SLV-20260715-JANSS")
                otype = st.selectbox("Type", helpers.DEAL_TYPES)
            with c2:
                deal_id = st.selectbox("Deal", list(deals), format_func=deals.get)
                installatie_id = st.selectbox("Installatie-adres", list(installaties),
                                              format_func=installaties.get)
            with c3:
                totaalprijs = st.number_input("Totaal incl. BTW (EUR)", min_value=0.0, step=100.0)
                btw_tarief = st.selectbox("BTW-tarief", helpers.BTW_TARIEVEN)
            status = st.selectbox("Status", helpers.OFFERTE_STATUSSEN)
            opmerkingen = st.text_area("Opmerkingen", height=60)
            if st.form_submit_button("Offerte toevoegen", type="primary"):
                db.voeg_toe("offertes", dict(
                    deal_id=deal_id or None, installatie_id=installatie_id or None,
                    nummer=nummer, type=otype, totaalprijs=totaalprijs,
                    btw_tarief=btw_tarief, status=status, opmerkingen=opmerkingen, bron="CRM"))
                st.success("Offerte toegevoegd.")
                st.rerun()
