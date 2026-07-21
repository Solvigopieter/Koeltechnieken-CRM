from datetime import date, timedelta

import streamlit as st

import db
import helpers

try:
    from streamlit_sortables import sort_items
    SLEPEN_BESCHIKBAAR = True
except ImportError:
    SLEPEN_BESCHIKBAAR = False


def _sort_style(kolommen_namen):
    """Bouwt CSS die elke kolom in de huisstijl-kleur van dat stadium kleurt."""
    regels = ["""
.sortable-component { font-family: 'Inter', sans-serif; gap: 10px; }
.sortable-container {
    background: #FFFFFF;
    border: 1px solid #E8EAEE;
    border-radius: 8px;
    min-height: 90px;
}
.sortable-container-header {
    font-size: 0.72rem;
    font-weight: 700;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    background: #F1F3F6;
    padding: 8px 10px;
    border-radius: 7px 7px 0 0;
    border-bottom: 1px solid #E8EAEE;
    text-align: center;
}
.sortable-container-body { padding: 6px; }
.sortable-item {
    background: #FFFFFF;
    border: 1px solid #E8EAEE;
    border-left-width: 3px;
    border-radius: 6px;
    padding: 8px 10px;
    margin-bottom: 6px;
    font-size: 0.8rem;
    color: #16204E;
    line-height: 1.4;
    cursor: grab;
    box-shadow: 0 1px 2px rgba(22,32,78,0.04);
}
.sortable-item:hover { box-shadow: 0 2px 6px rgba(22,32,78,0.10); }
"""]
    for i, stadium in enumerate(kolommen_namen, start=1):
        kleur = helpers.STADIUM_KLEUR.get(stadium, "#2338B0")
        regels.append(
            f".sortable-container:nth-of-type({i}) .sortable-container-header "
            f"{{ border-top: 3px solid {kleur}; }}\n"
            f".sortable-container:nth-of-type({i}) .sortable-item {{ border-left-color: {kleur}; }}"
        )
    return "\n".join(regels)


def toon():
    st.title("Pipeline")

    if "pipeline_sectie" not in st.session_state:
        st.session_state["pipeline_sectie"] = "📋 Bord"

    sectie = st.radio("Sectie", ["📋 Bord", "➕ Nieuwe deal", "✏️ Bewerken & taken"],
                      key="pipeline_sectie", horizontal=True, label_visibility="collapsed")
    st.divider()

    deals = db.query_df(
        "SELECT d.*, o.naam AS organisatie FROM deals d "
        "LEFT JOIN organisaties o ON o.id = d.organisatie_id ORDER BY d.gewijzigd DESC")

    # ---------------- bord ----------------
    if sectie == "📋 Bord":
        actief = [s for s in helpers.STADIUM_NAMEN if s not in ("Afgerond", "Verloren")]
        toon_afgerond = st.toggle("Toon ook Afgerond / Verloren", value=False)
        kolommen_namen = helpers.STADIUM_NAMEN if toon_afgerond else actief

        if SLEPEN_BESCHIKBAAR:
            st.caption("🖱️ Sleep een kaart naar een andere kolom om het stadium meteen te wijzigen. "
                      "Gebruik 'Open taken van deze deal' hieronder om de taken van een deal te bekijken "
                      "(een kaart zelf aanklikken kan niet, dat zou het slepen verstoren).")
            label_naar_id = {}
            containers = []
            for stadium in kolommen_namen:
                sub = deals[deals["stadium"] == stadium] if not deals.empty else deals
                som = sub["waarde"].fillna(0).sum() if not sub.empty else 0
                labels = []
                for _, d in sub.iterrows():
                    label = f"{d['titel']}  ·  {helpers.euro(d['waarde'])}   [#{int(d['id'])}]"
                    labels.append(label)
                    label_naar_id[label] = int(d["id"])
                containers.append({"header": f"{stadium}   ({len(sub)} · {helpers.euro(som)})",
                                   "items": labels})

            resultaat = sort_items(containers, multi_containers=True,
                                   custom_style=_sort_style(kolommen_namen), key="pipeline_bord")

            if resultaat:
                huidig_stadium = {}
                if not deals.empty:
                    huidig_stadium = dict(zip(deals["id"].astype(int), deals["stadium"]))
                gewijzigd = []
                for stadium, kolom in zip(kolommen_namen, resultaat):
                    for label in kolom.get("items", []):
                        deal_id = label_naar_id.get(label)
                        if deal_id is not None and huidig_stadium.get(deal_id) != stadium:
                            gewijzigd.append((deal_id, stadium))
                if gewijzigd:
                    for deal_id, nieuw_stadium in gewijzigd:
                        helpers.wijzig_stadium(deal_id, nieuw_stadium)
                    st.rerun()
        else:
            st.info("Sleepfunctie tijdelijk niet geladen (package installeert bij de eerstvolgende "
                    "herstart). Gebruik ondertussen 'Deal verplaatsen' hieronder.")
            for start in range(0, len(kolommen_namen), 4):
                rij = kolommen_namen[start:start + 4]
                cols = st.columns(len(rij))
                for col, stadium in zip(cols, rij):
                    sub = deals[deals["stadium"] == stadium] if not deals.empty else deals
                    kleur = helpers.STADIUM_KLEUR.get(stadium, "#2338B0")
                    som = sub["waarde"].fillna(0).sum() if not sub.empty else 0
                    col.markdown(
                        f'<div class="kolomkop" style="--kaartkleur:{kleur}">{stadium}'
                        f'<br><span class="kolom-som">{len(sub)} · {helpers.euro(som)}</span></div>',
                        unsafe_allow_html=True)
                    for _, d in sub.iterrows():
                        col.markdown(
                            f'<div class="kanban-kaart" style="--kaartkleur:{kleur}">'
                            f'<b>{d["titel"]}</b><br>'
                            f'<span class="kaart-meta">{d.get("organisatie") or "—"} · '
                            f'{d.get("type_installatie") or ""}</span><br>'
                            f'<span class="kaart-waarde">{helpers.euro(d["waarde"])}</span> '
                            f'<span class="kaart-meta">· kans {int(d.get("kans") or 0)}%</span></div>',
                            unsafe_allow_html=True)

        st.divider()
        st.subheader("Deal verplaatsen, openen of verwijderen")
        st.caption("Werkt ook zonder slepen — bv. handig op mobiel, of om snel een test-deal op te ruimen.")
        if deals.empty:
            st.info("Nog geen deals.")
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 1.6, 1, 1, 1])
            with c1:
                keuze = st.selectbox(
                    "Deal", deals["id"].tolist(),
                    format_func=lambda i: deals.set_index("id").loc[i, "titel"])
            with c2:
                huidig = deals.set_index("id").loc[keuze, "stadium"]
                nieuw = st.selectbox(
                    "Nieuw stadium", helpers.STADIUM_NAMEN,
                    index=helpers.STADIUM_NAMEN.index(huidig) if huidig in helpers.STADIUM_NAMEN else 0)
            with c3:
                st.write("")
                st.write("")
                if st.button("Verplaats", type="primary", use_container_width=True):
                    actie = helpers.wijzig_stadium(int(keuze), nieuw)
                    st.success(f"Verplaatst naar **{nieuw}**."
                               + (f" Vervolgactie aangemaakt: *{actie}*" if actie else ""))
                    st.rerun()
            with c4:
                st.write("")
                st.write("")
                if st.button("🗒️ Open taken", use_container_width=True,
                            help="Springt naar 'Bewerken & taken' voor deze deal, met het sjabloon meteen open."):
                    st.session_state["deal_bewerk_keuze"] = int(keuze)
                    st.session_state["pipe_sj_open_vanuit_bord"] = True
                    st.session_state["pipeline_sectie"] = "✏️ Bewerken & taken"
                    st.rerun()
            with c5:
                st.write("")
                st.write("")
                if st.button("🗑️ Verwijder", use_container_width=True,
                            help="Verwijdert deze deal meteen — handig om test-deals op te ruimen."):
                    db.verwijder("deals", int(keuze))
                    st.success("Deal verwijderd.")
                    st.rerun()

    # ---------------- nieuw ----------------
    elif sectie == "➕ Nieuwe deal":
        orgs = db.organisatie_opties()
        installaties = db.installatie_opties()
        with st.form("deal_nieuw"):
            titel = st.text_input("Titel*", placeholder="bv. Airco 2 slaapkamers Janssens")
            c1, c2, c3 = st.columns(3)
            with c1:
                type_installatie = st.selectbox("Type", helpers.DEAL_TYPES)
                organisatie_id = st.selectbox("Organisatie", list(orgs), format_func=orgs.get)
            with c2:
                installatie_id = st.selectbox("Installatie-adres", list(installaties), format_func=installaties.get)
                waarde = st.number_input("Waarde (EUR excl.)", min_value=0.0, step=100.0)
            with c3:
                kans = st.slider("Kans (%)", 0, 100, 50, step=5)
                prioriteit = st.selectbox("Prioriteit", helpers.PRIORITEITEN, index=1)
            c4, c5, c6 = st.columns(3)
            with c4:
                bron = st.selectbox("Bron", helpers.BRONNEN)
            with c5:
                deadline = st.date_input("Deadline", value=None)
            with c6:
                stadium = st.selectbox("Startstadium", helpers.STADIUM_NAMEN, index=0)
            sj_direct = st.multiselect(
                "Meteen ook taken aanmaken voor deze deal (optioneel)",
                [naam for naam, _ in helpers.TAAK_SJABLONEN],
                help="Wordt aangemaakt met de standaard-datums uit het sjabloon (aanpasbaar later op het Actieblad).")
            if st.form_submit_button("Deal aanmaken", type="primary"):
                if not titel.strip():
                    st.error("Titel is verplicht.")
                else:
                    deal_id = db.voeg_toe("deals", dict(
                        titel=titel.strip(), type_installatie=type_installatie,
                        organisatie_id=organisatie_id or None,
                        installatie_id=installatie_id or None,
                        waarde=waarde, kans=kans, bron=bron,
                        deadline=deadline.isoformat() if deadline else "",
                        stadium=stadium, prioriteit=prioriteit))
                    helpers.maak_vervolgactie(deal_id, stadium)
                    if sj_direct:
                        cumulatief = date.today()
                        for naam, dagen in helpers.TAAK_SJABLONEN:
                            cumulatief += timedelta(days=dagen)
                            if naam in sj_direct:
                                db.voeg_toe("acties", dict(
                                    datum=cumulatief.isoformat(),
                                    prioriteit="Normaal", organisatie_id=organisatie_id or None,
                                    deal_id=deal_id, actie=naam, status="Open"))
                    st.success("Deal aangemaakt (met automatische vervolgactie)"
                              + (f" + {len(sj_direct)} taken." if sj_direct else "."))
                    st.rerun()

    # ---------------- bewerken & taken ----------------
    else:
        if deals.empty:
            st.info("Nog geen deals.")
            return
        keuze = st.selectbox(
            "Kies deal", deals["id"].tolist(),
            format_func=lambda i: deals.set_index("id").loc[i, "titel"], key="deal_bewerk_keuze")
        d = db.haal_rij("deals", int(keuze)) or {}
        orgs = db.organisatie_opties()
        installaties = db.installatie_opties()

        with st.form("deal_bewerk"):
            titel = st.text_input("Titel*", value=d.get("titel") or "")
            c1, c2, c3 = st.columns(3)
            with c1:
                type_installatie = st.selectbox(
                    "Type", helpers.DEAL_TYPES,
                    index=helpers.DEAL_TYPES.index(d.get("type_installatie"))
                    if d.get("type_installatie") in helpers.DEAL_TYPES else 0)
                organisatie_id = st.selectbox(
                    "Organisatie", list(orgs), format_func=orgs.get,
                    index=helpers.sleutel_uit_opties(orgs, d.get("organisatie_id")))
            with c2:
                installatie_id = st.selectbox(
                    "Installatie-adres", list(installaties), format_func=installaties.get,
                    index=helpers.sleutel_uit_opties(installaties, d.get("installatie_id")))
                waarde = st.number_input("Waarde (EUR excl.)", min_value=0.0, step=100.0,
                                         value=float(d.get("waarde") or 0))
            with c3:
                kans = st.slider("Kans (%)", 0, 100, int(d.get("kans") or 50), step=5)
                prioriteit = st.selectbox(
                    "Prioriteit", helpers.PRIORITEITEN,
                    index=helpers.PRIORITEITEN.index(d.get("prioriteit"))
                    if d.get("prioriteit") in helpers.PRIORITEITEN else 1)
            c4, c5 = st.columns(2)
            with c4:
                bron = st.selectbox(
                    "Bron", helpers.BRONNEN,
                    index=helpers.BRONNEN.index(d.get("bron")) if d.get("bron") in helpers.BRONNEN else 0)
            with c5:
                stadium = st.selectbox(
                    "Stadium", helpers.STADIUM_NAMEN,
                    index=helpers.STADIUM_NAMEN.index(d.get("stadium"))
                    if d.get("stadium") in helpers.STADIUM_NAMEN else 0)
            k1, k2 = st.columns(2)
            opslaan = k1.form_submit_button("Opslaan", type="primary")
            weg = k2.form_submit_button("🗑️ Verwijder deal")
        if opslaan:
            oud_stadium = d.get("stadium")
            db.werk_bij("deals", int(keuze), dict(
                titel=titel.strip(), type_installatie=type_installatie,
                organisatie_id=organisatie_id or None, installatie_id=installatie_id or None,
                waarde=waarde, kans=kans, bron=bron, prioriteit=prioriteit,
                stadium=stadium, gewijzigd=date.today().isoformat()))
            if stadium != oud_stadium:
                helpers.maak_vervolgactie(int(keuze), stadium)
            st.success("Deal bijgewerkt.")
            st.rerun()
        if weg:
            db.verwijder("deals", int(keuze))
            st.success("Deal verwijderd.")
            st.rerun()

        # ---- Taken voor deze deal, rechtstreeks hier ----
        st.divider()
        st.subheader(f"🗒️ Taken voor '{d.get('titel', '')}'")

        acties_deal = db.query_df(
            "SELECT * FROM acties WHERE deal_id = ? ORDER BY datum", (int(keuze),))
        if acties_deal.empty:
            st.caption("Nog geen taken voor deze deal.")
        else:
            for _, a in acties_deal.iterrows():
                laat = helpers.te_laat(a["datum"]) and a["status"] in ("Open", "Bezig")
                ac1, ac2 = st.columns([4, 1.3])
                with ac1:
                    datum_html = (f'<span class="telaat">{a["datum"]} — TE LAAT</span>'
                                  if laat else str(a["datum"]))
                    st.markdown(
                        f'<div class="kanban-kaart" style="--kaartkleur:'
                        f'{"#B4443C" if laat else "#2338B0"}">'
                        f'<b>{a["actie"]}</b><br>'
                        f'<span class="kaart-meta">{datum_html} · {a["status"]}</span></div>',
                        unsafe_allow_html=True)
                with ac2:
                    nieuw_status = st.selectbox(
                        "Status", helpers.ACTIE_STATUSSEN,
                        index=helpers.ACTIE_STATUSSEN.index(a["status"])
                        if a["status"] in helpers.ACTIE_STATUSSEN else 0,
                        key=f"pipe_actie_status_{a['id']}", label_visibility="collapsed")
                    if nieuw_status != a["status"]:
                        db.werk_bij("acties", int(a["id"]), {"status": nieuw_status})
                        st.rerun()

        open_vanuit_bord = st.session_state.pop("pipe_sj_open_vanuit_bord", False)
        with st.expander("⚡ Taken uit sjabloon toevoegen aan deze deal", expanded=open_vanuit_bord):
            gekozen = helpers.sjabloon_keten_ui("pipe_sj", key_suffix=f"_{keuze}")
            if st.button("➕ Toevoegen aan deze deal", key=f"pipe_sj_toevoegen_{keuze}"):
                if not gekozen:
                    st.error("Vink minstens één taak aan.")
                else:
                    for naam, datum_veld in gekozen.items():
                        db.voeg_toe("acties", dict(
                            datum=datum_veld.isoformat(), prioriteit="Normaal",
                            organisatie_id=d.get("organisatie_id"), deal_id=int(keuze),
                            actie=naam, status="Open"))
                    st.success(f"{len(gekozen)} taken toegevoegd aan deze deal.")
                    st.rerun()
