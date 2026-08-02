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
                               "materiaalkost", "nettowinst",
                               "btw_tarief", "status", "datum", "bron"]].copy()
                toon_df["totaalprijs"] = toon_df["totaalprijs"].apply(helpers.euro)
                toon_df["materiaalkost"] = toon_df["materiaalkost"].apply(helpers.euro)
                toon_df["nettowinst"] = toon_df["nettowinst"].apply(helpers.euro)
                st.dataframe(toon_df, use_container_width=True, hide_index=True)
                helpers.export_knop(sub, "offertes.xlsx")
                totaal_materiaal = sub["materiaalkost"].fillna(0).sum()
                totaal_netto = sub["nettowinst"].fillna(0).sum()
                m1, m2 = st.columns(2)
                m1.metric("Totale materiaalkost (getoonde offertes)", helpers.euro(totaal_materiaal))
                m2.metric("Totale nettowinst (getoonde offertes)", helpers.euro(totaal_netto))

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
                    installatie_id = st.selectbox("Installatie-adres", list(installaties),
                                                  format_func=installaties.get,
                                                  index=helpers.sleutel_uit_opties(installaties, f.get("installatie_id")))
                with c2:
                    totaalprijs = st.number_input("Totaal incl. BTW (EUR)", min_value=0.0, step=10.0,
                                                  value=float(f.get("totaalprijs") or 0))
                    materiaalkost = st.number_input("Materiaalkost (inkoop, EUR)", min_value=0.0, step=10.0,
                                                    value=float(f.get("materiaalkost") or 0))
                    nettowinst = st.number_input("Nettowinst (EUR)", min_value=0.0, step=10.0,
                                                 value=float(f.get("nettowinst") or 0))
                    btw_tarief = st.selectbox("BTW-tarief", helpers.BTW_TARIEVEN,
                                              index=helpers.BTW_TARIEVEN.index(f.get("btw_tarief"))
                                              if f.get("btw_tarief") in helpers.BTW_TARIEVEN else 0)
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
                    materiaalkost=materiaalkost, nettowinst=nettowinst,
                    btw_tarief=btw_tarief, status=status, opmerkingen=opmerkingen))
                if deal_id:
                    db.werk_bij("deals", int(deal_id), {"waarde": totaalprijs})
                st.success("Offerte bijgewerkt"
                          + (" — deal-waarde bijgewerkt naar dit bedrag." if deal_id else "."))
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
            st.caption("⚠️ Hier gebeurt **niets automatisch** — een project verschijnt hier onder "
                      "'nog niet geïmporteerd', maar komt pas in de Pipeline terecht als je zelf op "
                      "'Importeer' klikt. Zo blijven proef-/testoffertes gewoon hier staan zonder "
                      "ongewild in het CRM te belanden.")
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

                nog_niet = [p for p in projecten if str(p.get("id")) not in al_geimporteerd]
                al_wel = [p for p in projecten if str(p.get("id")) in al_geimporteerd]

                if nog_niet:
                    st.markdown(f"**{len(nog_niet)} nog niet geïmporteerd:**")
                for p in nog_niet[:30]:
                    pid = str(p.get("id"))
                    bedrag = offerte_koppeling.bedrag_van(p, "totaal_incl")
                    with st.expander(f"⬜ {p.get('datum')} — {p.get('type')} — {p.get('klant')} — "
                                    f"{helpers.euro(bedrag)}"):
                        if st.button("⬇️ Importeer naar CRM (klant + deal + offerte aanmaken)",
                                    key=f"gen_import_{pid}", type="primary"):
                            payload = offerte_koppeling.payload_van(p)
                            klantnaam = str(p.get("klant") or "").strip() or "(naamloos)"

                            orgs_alle = db.query_df("SELECT id, naam FROM organisaties")
                            org_id = None
                            if not orgs_alle.empty:
                                match = orgs_alle[orgs_alle["naam"].str.strip().str.lower() == klantnaam.lower()]
                                if not match.empty:
                                    org_id = int(match.iloc[0]["id"])
                            if org_id is None:
                                org_id = db.voeg_toe("organisaties", dict(
                                    klantnummer=helpers.volgend_klantnummer(), naam=klantnaam,
                                    type="Eindklant", adres=str(payload.get("adres") or ""),
                                    email=str(payload.get("email") or ""), telefoon=str(payload.get("tel") or ""),
                                    status="Actief", relatietype="Eenmalige klant"))

                            deal_id = db.voeg_toe("deals", dict(
                                titel=f"{p.get('type') or 'Offerte'} — {klantnaam}",
                                type_installatie=p.get("type") or "Airco",
                                organisatie_id=org_id, waarde=bedrag,
                                kans=70, stadium="Offerte verstuurd", prioriteit="Normaal",
                                bron="Offertegenerator"))

                            db.voeg_toe("offertes", dict(
                                deal_id=deal_id, nummer=f"GEN-{pid}", type=p.get("type"),
                                totaalprijs=bedrag,
                                materiaalkost=offerte_koppeling.bedrag_van(p, "mat_inkoop"),
                                nettowinst=offerte_koppeling.bedrag_van(p, "netto_winst"),
                                status="Verstuurd", datum=str(p.get("datum") or ""),
                                bron="Generator", generator_id=pid,
                                opmerkingen=f"Handmatig geïmporteerd uit offertegenerator (klant: {klantnaam})"))
                            st.success(f"✅ {klantnaam} geïmporteerd — staat nu in de Pipeline.")
                            st.rerun()

                if al_wel:
                    st.markdown(f"**{len(al_wel)} al geïmporteerd:**")
                for p in al_wel[:30]:
                    pid = str(p.get("id"))
                    bedrag = offerte_koppeling.bedrag_van(p, "totaal_incl")
                    reeds = offertes[offertes["generator_id"].astype(str) == pid] if not offertes.empty else offertes
                    huidig_bedrag = reeds.iloc[0]["totaalprijs"] if not reeds.empty else bedrag
                    gekoppelde_deal = reeds.iloc[0]["deal"] if (not reeds.empty and "deal" in reeds.columns) else None
                    with st.expander(f"✅ {p.get('datum')} — {p.get('type')} — {p.get('klant')} — "
                                    f"{helpers.euro(huidig_bedrag)}"):
                        st.write(f"Gekoppeld aan deal: **{gekoppelde_deal or '—'}**")
                        if abs(float(huidig_bedrag or 0) - bedrag) > 0.01:
                            st.warning("⚠️ Dit bedrag wijkt af van wat de generator nu toont "
                                      f"({helpers.euro(bedrag)}) — waarschijnlijk aangepast in de "
                                      "generator ná het importeren.")
                        if not reeds.empty and st.button("🗑️ Verwijderen uit CRM (zodat je opnieuw kan importeren)",
                                    key=f"gen_verwijder_reimport_{pid}"):
                            db.verwijder("offertes", int(reeds.iloc[0]["id"]))
                            st.success("Verwijderd — staat nu weer bij 'nog niet geïmporteerd'.")
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
                if deal_id:
                    db.werk_bij("deals", int(deal_id), {"waarde": totaalprijs})
                st.success("Offerte toegevoegd"
                          + (" — deal-waarde bijgewerkt naar dit bedrag." if deal_id else "."))
                st.rerun()
