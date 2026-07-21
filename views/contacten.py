import streamlit as st

import db
import helpers


def toon():
    st.title("Contactpersonen")

    tab_lijst, tab_nieuw, tab_bewerk = st.tabs(["📋 Lijst", "➕ Nieuw", "✏️ Bewerken"])

    contacten = db.query_df(
        "SELECT c.*, o.naam AS organisatie FROM contacten c "
        "LEFT JOIN organisaties o ON o.id = c.organisatie_id ORDER BY c.naam")

    with tab_lijst:
        zoek = st.text_input("Zoeken", placeholder="naam, organisatie of e-mail")
        sub = contacten.copy()
        if not sub.empty and zoek.strip():
            z = zoek.lower()
            sub = sub[sub["naam"].astype(str).str.lower().str.contains(z)
                      | sub["organisatie"].astype(str).str.lower().str.contains(z)
                      | sub["email"].astype(str).str.lower().str.contains(z)]
        if sub.empty:
            st.info("Geen contacten gevonden.")
        else:
            st.dataframe(sub[["naam", "organisatie", "functie", "rol", "email", "telefoon", "notities"]],
                         use_container_width=True, hide_index=True)
            helpers.export_knop(sub, "contacten.xlsx")

    with tab_nieuw:
        orgs = db.organisatie_opties()
        with st.form("contact_nieuw"):
            naam = st.text_input("Naam*")
            c1, c2, c3 = st.columns(3)
            with c1:
                organisatie_id = st.selectbox("Organisatie", list(orgs), format_func=orgs.get)
                functie = st.text_input("Functie")
            with c2:
                email = st.text_input("E-mail")
                telefoon = st.text_input("Telefoon")
            with c3:
                rol = st.selectbox("Rol", helpers.CONTACT_ROLLEN)
                linkedin = st.text_input("LinkedIn")
            notities = st.text_area("Notities", height=70)
            if st.form_submit_button("Toevoegen", type="primary"):
                if not naam.strip():
                    st.error("Naam is verplicht.")
                else:
                    db.voeg_toe("contacten", dict(
                        organisatie_id=organisatie_id or None, naam=naam.strip(),
                        functie=functie, email=email, telefoon=telefoon,
                        linkedin=linkedin, rol=rol, notities=notities))
                    st.success("Contact toegevoegd.")
                    st.rerun()

    with tab_bewerk:
        if contacten.empty:
            st.info("Nog geen contacten.")
            return
        keuze = st.selectbox("Kies contact", contacten["id"].tolist(),
                             format_func=lambda i: contacten.set_index("id").loc[i, "naam"])
        c = db.haal_rij("contacten", int(keuze)) or {}
        orgs = db.organisatie_opties()
        with st.form("contact_bewerk"):
            naam = st.text_input("Naam*", value=c.get("naam") or "")
            c1, c2, c3 = st.columns(3)
            with c1:
                organisatie_id = st.selectbox("Organisatie", list(orgs), format_func=orgs.get,
                                              index=helpers.sleutel_uit_opties(orgs, c.get("organisatie_id")))
                functie = st.text_input("Functie", value=c.get("functie") or "")
            with c2:
                email = st.text_input("E-mail", value=c.get("email") or "")
                telefoon = st.text_input("Telefoon", value=c.get("telefoon") or "")
            with c3:
                rol = st.selectbox("Rol", helpers.CONTACT_ROLLEN,
                                   index=helpers.CONTACT_ROLLEN.index(c.get("rol"))
                                   if c.get("rol") in helpers.CONTACT_ROLLEN else 0)
                linkedin = st.text_input("LinkedIn", value=c.get("linkedin") or "")
            notities = st.text_area("Notities", value=c.get("notities") or "", height=70)
            k1, k2 = st.columns(2)
            opslaan = k1.form_submit_button("Opslaan", type="primary")
            weg = k2.form_submit_button("🗑️ Verwijder")
        if opslaan:
            db.werk_bij("contacten", int(keuze), dict(
                organisatie_id=organisatie_id or None, naam=naam.strip(), functie=functie,
                email=email, telefoon=telefoon, linkedin=linkedin, rol=rol, notities=notities))
            st.success("Contact bijgewerkt.")
            st.rerun()
        if weg:
            db.verwijder("contacten", int(keuze))
            st.success("Contact verwijderd.")
            st.rerun()
