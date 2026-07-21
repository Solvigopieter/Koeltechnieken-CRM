"""
Solvigo Koeltechnieken CRM – koppeling met de offertegenerator.

De offertegenerator (aparte Streamlit-app) bewaart zijn projecten in een eigen
Google Sheet (standaard "Koeltechnieken offerte") in het tabblad "Projecten"
met kolommen: id, datum, type, klant, totaal_incl, payload.

Deze module leest die projecten met hetzelfde service account, zodat je ze in
het CRM kan bekijken en met één klik kan importeren als offerte + deal.

Secrets (optioneel):
    offerte_sheet_name = "Koeltechnieken offerte"   # naam van de offerte-sheet
    offerte_app_url = "https://....streamlit.app"    # link naar de generator
"""
from __future__ import annotations

import json

import streamlit as st

PROJECT_HEADERS = ["id", "datum", "type", "klant", "totaal_incl", "payload"]


def offerte_app_url() -> str:
    try:
        return str(st.secrets.get("offerte_app_url", "")).strip()
    except Exception:
        return ""


def koppeling_beschikbaar() -> bool:
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


@st.cache_resource
def _offerte_sheet():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes
    )
    gc = gspread.authorize(creds)
    naam = st.secrets.get("offerte_sheet_name", st.secrets.get("PR_SHEET_NAME", "Koeltechnieken offerte"))
    return gc.open(str(naam))


@st.cache_data(ttl=60)
def haal_generator_projecten() -> list[dict]:
    """Alle projecten uit de offertegenerator, nieuwste eerst."""
    if not koppeling_beschikbaar():
        return []
    try:
        sh = _offerte_sheet()
        ws = sh.worksheet("Projecten")
        records = ws.get_all_records(expected_headers=PROJECT_HEADERS)
    except Exception:
        return []
    projecten = [r for r in records if str(r.get("id", "")).strip()]
    projecten.sort(key=lambda r: str(r.get("id", "")), reverse=True)
    return projecten


def payload_van(project: dict) -> dict:
    try:
        return json.loads(project.get("payload") or "{}")
    except Exception:
        return {}


def ververs_cache():
    haal_generator_projecten.clear()


def bedrag_van(project: dict) -> float:
    """Leest 'totaal_incl' robuust uit, ongeacht of Google Sheets dit als een
    echt getal, een Amerikaans-genoteerde tekst ('4789.72') of een
    Belgisch-genoteerde tekst ('4.789,72') teruggeeft. Zonder deze correctie
    kan '4.789,72' foutief als 478972 gelezen worden."""
    waarde = project.get("totaal_incl")
    if waarde is None or waarde == "":
        return 0.0
    if isinstance(waarde, (int, float)):
        return float(waarde)
    tekst = str(waarde).strip()
    try:
        return float(tekst)
    except ValueError:
        pass
    # Belgisch/Europees formaat: punt = duizendtal-scheiding, komma = decimaal
    try:
        return float(tekst.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0
