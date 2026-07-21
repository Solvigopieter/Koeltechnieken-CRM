from datetime import date

import streamlit as st

import db
import helpers


def toon():
    st.title("Pipeline")

    tab_bord, tab_nieuw, tab_bewerk = st.tabs(["📋 Bord", "➕ Nieuwe deal", "✏️ Bewerken"])

    deals = db.query_df(
        "SELECT d.*, o.naam AS organisatie FROM deals d "
        "LEFT JOIN organisaties o ON o.id = d.organisatie_id ORDER BY d.gewijzigd DESC")

    # ---------------- bord ----------------
    with tab_bord:
        actief = [s for s in helpers.STADIUM_NAMEN if s not in ("Afgerond", "Verloren")]
        toon_afgerond = st.toggle("Toon ook Afgerond / Verloren", value=False)
        kolommen_namen = helpers.STADIUM_NAMEN if toon_afgerond else actief

        # kolommen in rijen van 4 zodat het leesbaar blijft
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
                if sub.empty:
                    continue
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
        st.subheader("Deal verplaatsen")
        if deals.empty:
            st.info("Nog geen deals.")
        else:
            c1, c2, c3 = st.columns([2, 2, 1])
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

    # ---------------- nieuw ----------------
    with tab_nieuw:
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
                    st.success("Deal aangemaakt (met automatische vervolgactie).")
                    st.rerun()

    # ---------------- bewerken ----------------
    with tab_bewerk:
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
