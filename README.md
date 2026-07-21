# Solvigo Koeltechnieken CRM

CRM voor de airco/warmtepomp-tak van Solvigo BV. Zelfde opzet als de Solvigo
(PV-cleaning) CRM, aangepast aan koeltechniek:

- Pipeline met HVAC-stadia (lead → plaatsbezoek → offerte → uitvoering → nazorg)
  en automatische vervolgacties bij elke stadiumwissel
- Installatie-adressen met bouwjaar (6% BTW-check), elektrische aansluiting en
  bestaande toestellen
- Plaatsbezoek-verslagen op maat van airco/WP (leidingtracé, condensafvoer, boorwerk, ...)
- **Onderhoudscontracten** met automatische volgende-beurt-planning en jaaromzet-schatting
- **Koppeling met de offertegenerator**: projecten die je daar bewaart, verschijnen
  in het CRM en importeer je met één klik als offerte (gekoppeld aan deal + adres)

## Lokaal starten

```
pip install -r requirements.txt
streamlit run app.py
```

Lokaal draait alles op SQLite (kt_crm.db) met demodata.

## Streamlit Cloud + Google Sheets

1. Maak een NIEUWE lege Google Sheet aan (bv. "Koeltechnieken CRM") en deel ze
   met het service-account e-mailadres (Editor).
2. Zet in de app-secrets (Streamlit Cloud → app → Settings → Secrets):

```
crm_storage = "google_sheets"
google_sheet_id = "SHEET_ID_VAN_DE_CRM_SHEET"

# Koppeling met de offertegenerator (zelfde service account):
offerte_sheet_name = "Koeltechnieken offerte"
offerte_app_url = "https://JOUW-OFFERTE-APP.streamlit.app"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Let op: `google_sheet_id` = het ID van de **CRM-sheet** (uit de URL), en
`offerte_sheet_name` = de **naam** van de offerte-sheet (die de generator al gebruikt).
Gebruik gerust hetzelfde service account als de offertegenerator — deel dan beide
sheets met dat account.

De tabbladen (organisaties, deals, offertes, onderhoudscontracten, ...) worden
automatisch aangemaakt bij de eerste start.

## Koppeling offertegenerator — hoe werkt het

- De generator bewaart projecten in zijn eigen sheet, tabblad "Projecten"
  (kolommen: id, datum, type, klant, totaal_incl, payload).
- Het CRM leest dat tabblad (alleen-lezen) en toont de projecten onder
  **Offertes → Uit de offertegenerator**.
- Klik "Importeer als offerte": het project wordt een offerte in het CRM,
  gekoppeld aan een deal en installatie-adres. Zet je de status op "Verstuurd",
  dan schuift de deal automatisch mee naar "Offerte verstuurd" in de pipeline.
- Via de knop "Open offertegenerator" (sidebar + offertepagina) spring je direct
  naar de generator om een nieuwe offerte te maken.
