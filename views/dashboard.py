import pandas as pd
import streamlit as st

import db
import helpers


def toon():
    st.title("Dashboard")

    deals = db.query_df(
        "SELECT d.*, o.naam AS organisatie FROM deals d "
        "LEFT JOIN organisaties o ON o.id = d.organisatie_id")
    acties = db.query_df(
        "SELECT a.*, o.naam AS organisatie FROM acties a "
        "LEFT JOIN organisaties o ON o.id = a.organisatie_id")
    onderhoud = db.query_df(
        "SELECT c.*, o.naam AS organisatie FROM onderhoudscontracten c "
        "LEFT JOIN organisaties o ON o.id = c.organisatie_id")
    offertes = db.query_df("SELECT * FROM offertes WHERE status IN ('Verstuurd', 'Goedgekeurd')")

    open_deals = deals[~deals["stadium"].isin(["Afgerond", "Verloren"])] if not deals.empty else deals
    open_acties = acties[acties["status"].isin(["Open", "Bezig"])] if not acties.empty else acties
    telaat = open_acties[open_acties["datum"].apply(helpers.te_laat)] if not open_acties.empty else open_acties
    pipeline_waarde = open_deals["waarde"].fillna(0).sum() if not open_deals.empty else 0
    gewogen = (open_deals["waarde"].fillna(0) * open_deals["kans"].fillna(0) / 100).sum() if not open_deals.empty else 0
    actieve_contracten = onderhoud[onderhoud["status"] == "Actief"] if not onderhoud.empty else onderhoud
    materiaalkost_totaal = offertes["materiaalkost"].fillna(0).sum() if not offertes.empty else 0
    nettowinst_totaal = offertes["nettowinst"].fillna(0).sum() if not offertes.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    helpers.stat_tegel(k1, len(open_deals), "Open deals")
    helpers.stat_tegel(k2, helpers.euro(pipeline_waarde), "Pipelinewaarde")
    helpers.stat_tegel(k3, helpers.euro(gewogen), "Gewogen (kans %)")
    helpers.stat_tegel(k4, len(telaat), "Acties te laat", alert=len(telaat) > 0)
    helpers.stat_tegel(k5, len(actieve_contracten), "Actieve onderhoudscontracten")

    k6, k7 = st.columns(2)
    helpers.stat_tegel(k6, helpers.euro(materiaalkost_totaal), "Materiaalkost (verstuurd + goedgekeurd)")
    helpers.stat_tegel(k7, helpers.euro(nettowinst_totaal), "Nettowinst (verstuurd + goedgekeurd)")

    st.write("")
    links, rechts = st.columns([1.2, 1])

    with links:
        st.subheader("Pipeline per stadium")
        if open_deals.empty:
            st.info("Nog geen open deals.")
        else:
            per_stadium = (
                open_deals.groupby("stadium")
                .agg(aantal=("id", "count"), waarde=("waarde", "sum"))
                .reindex([s for s in helpers.STADIUM_NAMEN if s not in ("Afgerond", "Verloren")])
                .dropna(how="all").fillna(0)
            )
            per_stadium["waarde"] = per_stadium["waarde"].apply(helpers.euro)
            per_stadium["aantal"] = per_stadium["aantal"].astype(int)
            st.dataframe(per_stadium, use_container_width=True)

        st.subheader("Deals met hoge prioriteit")
        if open_deals.empty:
            st.caption("—")
        else:
            hoog = open_deals[open_deals["prioriteit"] == "Hoog"]
            if hoog.empty:
                st.caption("Geen deals met hoge prioriteit.")
            for _, d in hoog.iterrows():
                kleur = helpers.STADIUM_KLEUR.get(d["stadium"], "#2338B0")
                st.markdown(
                    f'<div class="kanban-kaart" style="--kaartkleur:{kleur}">'
                    f'<b>{d["titel"]}</b><br>'
                    f'<span class="kaart-meta">{d.get("organisatie") or ""} · {d["stadium"]}</span><br>'
                    f'<span class="kaart-waarde">{helpers.euro(d["waarde"])}</span></div>',
                    unsafe_allow_html=True)

    with rechts:
        st.subheader("Eerstvolgende acties")
        if open_acties.empty:
            st.info("Geen open acties. 👌")
        else:
            volgende = open_acties.sort_values("datum").head(8)
            for _, a in volgende.iterrows():
                laat = helpers.te_laat(a["datum"])
                datum_html = (f'<span class="telaat">{a["datum"]} — TE LAAT</span>'
                              if laat else a["datum"])
                st.markdown(
                    f'<div class="kanban-kaart" style="--kaartkleur:'
                    f'{"#B4443C" if laat else "#2338B0"}">'
                    f'<b>{a["actie"]}</b><br>'
                    f'<span class="kaart-meta">{a.get("organisatie") or "—"} · {datum_html} · '
                    f'{helpers.prioriteit_badge(a["prioriteit"])}</span></div>',
                    unsafe_allow_html=True)

        st.subheader("Onderhoud binnen 30 dagen")
        if onderhoud.empty:
            st.caption("—")
        else:
            import datetime as _dt
            grens = (_dt.date.today() + _dt.timedelta(days=30)).isoformat()
            binnenkort = onderhoud[
                (onderhoud["status"] == "Actief") &
                (onderhoud["volgende_beurt"].astype(str) != "") &
                (onderhoud["volgende_beurt"].astype(str) <= grens)
            ]
            if binnenkort.empty:
                st.caption("Geen onderhoudsbeurten gepland binnen 30 dagen.")
            for _, c in binnenkort.iterrows():
                st.markdown(
                    f'<div class="kanban-kaart" style="--kaartkleur:#C99E00">'
                    f'<b>{c.get("organisatie") or "Klant"}</b> — {c.get("toestel") or ""}<br>'
                    f'<span class="kaart-meta">Volgende beurt: {c["volgende_beurt"]} · '
                    f'{helpers.euro(c.get("prijs_per_beurt"))}/beurt</span></div>',
                    unsafe_allow_html=True)
