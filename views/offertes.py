import streamlit as st

import db
import helpers
import offerte_koppeling


def toon():
    st.title("Offertes")

    url = offerte_koppeling.offerte_app_url()
    if url:
        st.link_button("📄 Nieuwe offerte maken in de offertegenerator ↗", url)

    tab_crm, tab_bewerk, tab_generator, tab_nieuw = st.tabs(
        ["📋 Offertes in CRM", "✏️ Bewerken / verwijderen", "🔗 Uit de offertegenerator", "➕ Handmatig toevoegen"])

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
                st.subheader("Status snel aanpassen")
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

    # ---------------- bewerken / verwijderen ----------------
    with tab_bewerk:
        if offertes.empty:
            st.info("Nog geen offertes.")
        else:
            st.caption("Hier kan je o.a. een fout bedrag corrigeren (bv. bij een offerte die "
                      "geïmporteerd werd vóór een fix in de koppeling) of een offerte verwijderen.")
            keuze = st.selectbox(
                "Kies offerte", offertes["id"].tolist(),
                format_func=lambda i: str(offertes.set_index("id").loc[i, "nummer"]), key="off_bewerk_keuze")
            f = db.haal_rij("offertes", int(keuze)) or {}
            deals = db.deal_opties()
            installaties = db.installatie_opties()
            with st.form("offerte_bewerk"):
                c1, c2 = st.columns(2)
                with c1:
                    nummer = st.text_input("Offertenummer", value=f.get("nummer") or "")
                    otype = st.selectbox("Type", helpers.DEAL_TYPES,
                                         index=helpers.DEAL_TYPES.index(f.get("type"))
                                         if f.get("type") in helpers.DEAL_TYPES else 0)
                    deal_id = st.selectbox("Deal", list(deals), format_func=deals.get,
                                           index=helpers.sleutel_uit_opties(deals, f.get("deal_id")))
                with c2:
                    totaalprijs = st.number_input("Totaal incl. BTW (EUR)", min_value=0.0, step=10.0,
                                                  value=float(f.get("totaalprijs") or 0))
                    btw_tarief = st.selectbox("BTW-tarief", helpers.BTW_TARIEVEN,
                                              index=helpers.BTW_TARIEVEN.index(f.get("btw_tarief"))
                                              if f.get("btw_tarief") in helpers.BTW_TARIEVEN else 0)
                    installatie_id = st.selectbox("Installatie-adres", list(installaties),
                                                  format_func=installaties.get,
                                                  index=helpers.sleutel_uit_opties(installaties, f.get("installatie_id")))
                status = st.selectbox("Status", helpers.OFFERTE_STATUSSEN,
                                      index=helpers.OFFERTE_STATUSSEN.index(f.get("status"))
                                      if f.get("status") in helpers.OFFERTE_STATUSSEN else 0)
                opmerkingen = st.text_area("Opmerkingen", value=f.get("opmerkingen") or "", height=60)
                k1, k2 = st.columns(2)
                opslaan = k1.form_submit_button("Opslaan", type="primary")
                weg = k2.form_submit_button("🗑️ Verwijder offerte")
            if opslaan:
                db.werk_bij("offertes", int(keuze), dict(
                    nummer=nummer, type=otype, deal_id=deal_id or None,
                    installatie_id=installatie_id or None, totaalprijs=totaalprijs,
                    btw_tarief=btw_tarief, status=status, opmerkingen=opmerkingen))
                st.success("Offerte bijgewerkt.")
                st.rerun()
            if weg:
                db.verwijder("offertes", int(keuze))
                st.success("Offerte verwijderd.")
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
                        f"{p.get('klant')} — {helpers.euro(offerte_koppeling.bedrag_van(p))}"
                    ):
                        if geimporteerd:
                            reeds = offertes[offertes["generator_id"].astype(str) == pid]
                            huidig_bedrag = reeds.iloc[0]["totaalprijs"] if not reeds.empty else 0
                            st.info(f"Al geïmporteerd in het CRM als offerte met bedrag "
                                   f"**{helpers.euro(huidig_bedrag)}**.")
                            if abs(float(huidig_bedrag or 0) - offerte_koppeling.bedrag_van(p)) > 0.01:
                                st.warning("⚠️ Dit bedrag wijkt af van wat de generator nu toont "
                                          f"({helpers.euro(offerte_koppeling.bedrag_van(p))}) — "
                                          "waarschijnlijk geïmporteerd vóór een eerdere fix.")
                            if st.button("🗑️ Verwijder deze offerte uit CRM (zodat je opnieuw kan importeren)",
                                        key=f"gen_verwijder_reimport_{pid}"):
                                if not reeds.empty:
                                    db.verwijder("offertes", int(reeds.iloc[0]["id"]))
                                    st.success("Verwijderd — je kan dit project nu hieronder opnieuw importeren.")
                                    st.rerun()
                            continue

                        payload = offerte_koppeling.payload_van(p)

                        with st.expander("⚡ Nieuwe klant + deal in 1 klik aanmaken "
                                         "(handig — de meeste HVAC-klanten bestaan nog niet in het CRM)"):
                            st.caption("Naam/adres/e-mail/telefoon worden overgenomen uit de offerte "
                                      "zelf. Klantnummer wordt automatisch voorgesteld.")
                            sc1, sc2 = st.columns([1, 3])
                            with sc1:
                                snel_nr = st.text_input("Klantnummer", value=helpers.volgend_klantnummer(),
                                                        key=f"gen_snelnr_{pid}")
                            with sc2:
                                snel_naam = st.text_input("Klantnaam", value=str(p.get("klant") or ""),
                                                          key=f"gen_snelnaam_{pid}")
                            sc3, sc4 = st.columns(2)
                            with sc3:
                                snel_adres = st.text_input("Adres", value=str(payload.get("adres") or ""),
                                                           key=f"gen_sneladres_{pid}")
                                snel_email = st.text_input("E-mail", value=str(payload.get("email") or ""),
                                                           key=f"gen_snelemail_{pid}")
                            with sc4:
                                snel_tel = st.text_input("Telefoon", value=str(payload.get("tel") or ""),
                                                         key=f"gen_sneltel_{pid}")
                            if st.button("➕ Klant + deal aanmaken", key=f"gen_snelmaak_{pid}"):
                                if not snel_naam.strip():
                                    st.error("Vul een klantnaam in.")
                                else:
                                    nieuw_org_id = db.voeg_toe("organisaties", dict(
                                        klantnummer=snel_nr.strip(), naam=snel_naam.strip(),
                                        type="Eindklant", adres=snel_adres, email=snel_email,
                                        telefoon=snel_tel, status="Actief", relatietype="Eenmalige klant"))
                                    nieuwe_deal_id = db.voeg_toe("deals", dict(
                                        titel=f"{p.get('type') or 'Offerte'} — {snel_naam.strip()}",
                                        type_installatie=p.get("type") or "Airco",
                                        organisatie_id=nieuw_org_id,
                                        waarde=offerte_koppeling.bedrag_van(p),
                                        kans=70, stadium="Offerte verstuurd", prioriteit="Normaal",
                                        bron="Offertegenerator"))
                                    st.session_state[f"gen_deal_{pid}"] = nieuwe_deal_id
                                    st.success(f"Klant {snel_nr.strip()} en deal aangemaakt — automatisch gekoppeld.")
                                    st.rerun()

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
                                totaalprijs=offerte_koppeling.bedrag_van(p),
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
