"""
Solvigo Koeltechnieken CRM - koppeling met Solvigo Balans.

Balans is een aparte Streamlit-app die de onderlinge verdeling van geld
tussen de twee vennoten bijhoudt (zie het project "balans"). Deze module
stuurt vanuit het CRM, met één klik, een inkomst (omzet van een
goedgekeurde offerte) en optioneel een uitgave (materiaalkost) door naar
het tabblad "transacties" van diezelfde Google Sheet die Balans gebruikt.

Vereist in de secrets van kt-crm (naast de bestaande gcp_service_account):
    balans_sheet_id = "..."   # zelfde sheet-ID als in de Balans-app

Belangrijk: we schrijven in exact hetzelfde kolomformaat als
storage.py (TRANSACTIE_KOLOMMEN) in de Balans-app, inclusief de
'-prefix-fix voor floats tegen de Sheets-locale-bug, zodat Balans de
rijen gewoon kan inlezen.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid
from pathlib import Path

import streamlit as st

TRANSACTIE_KOLOMMEN = [
    "id", "datum", "richting", "bedrag", "wie", "categorie",
    "omschrijving", "bijlage_id", "bijlage_naam", "vereffend",
    "aangemaakt_op",
]

# Lokaal bijhouden welke offertes al verstuurd zijn, zodat je niet twee keer
# per ongeluk dezelfde omzet doorstuurt. Losse SQLite-tabel, onafhankelijk
# van het CRM-schema zelf.
_LINKS_DB = Path(__file__).parent / "balans_koppelingen.db"


def _links_conn():
    conn = sqlite3.connect(_LINKS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verstuurd (
            offerte_id INTEGER PRIMARY KEY,
            transactie_ids TEXT,
            verstuurd_op TEXT
        )
    """)
    return conn


def is_verstuurd(offerte_id: int) -> bool:
    conn = _links_conn()
    row = conn.execute(
        "SELECT 1 FROM verstuurd WHERE offerte_id=?", (offerte_id,)
    ).fetchone()
    conn.close()
    return row is not None


def _markeer_verstuurd(offerte_id: int, transactie_ids: list[str]):
    conn = _links_conn()
    conn.execute(
        "INSERT INTO verstuurd (offerte_id, transactie_ids, verstuurd_op) "
        "VALUES (?, ?, ?) ON CONFLICT(offerte_id) DO UPDATE SET "
        "transactie_ids=excluded.transactie_ids, verstuurd_op=excluded.verstuurd_op",
        (offerte_id, ",".join(transactie_ids), dt.datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def koppeling_beschikbaar() -> bool:
    try:
        return "gcp_service_account" in st.secrets and bool(st.secrets.get("balans_sheet_id"))
    except Exception:
        return False


@st.cache_resource
def _balans_sheet():
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
    return gc.open_by_key(str(st.secrets["balans_sheet_id"]))


@st.cache_data(ttl=60)
def haal_namen() -> tuple[str, str]:
    """Leest de persoonsnamen uit de Balans-instellingen, met fallback."""
    try:
        book = _balans_sheet()
        ws = book.worksheet("instellingen")
        records = ws.get_all_records()
        waarden = {r["sleutel"]: r["waarde"] for r in records}
        return waarden.get("persoon_a_naam", "Persoon A"), waarden.get("persoon_b_naam", "Persoon B")
    except Exception:
        return "Persoon A", "Persoon B"


def _transacties_worksheet():
    book = _balans_sheet()
    try:
        return book.worksheet("transacties")
    except Exception:
        ws = book.add_worksheet(title="transacties", rows=1000, cols=len(TRANSACTIE_KOLOMMEN) + 2)
        ws.append_row(TRANSACTIE_KOLOMMEN)
        return ws


def _float_naar_tekst(bedrag: float) -> str:
    """Zelfde locale-fix als in Balans/storage.py: als tekst met '-prefix
    wegschrijven, anders verknoeit de Belgische Sheets-locale het getal."""
    return "'" + repr(float(bedrag))


def _nieuwe_rij(richting: str, bedrag: float, wie: str, categorie: str, omschrijving: str) -> tuple[str, list]:
    id_ = str(uuid.uuid4())
    rij = [
        id_, dt.date.today().isoformat(), richting, _float_naar_tekst(bedrag),
        wie, categorie, omschrijving, "", "", "0",
        dt.datetime.now().isoformat(timespec="seconds"),
    ]
    return id_, rij


def verstuur_offerte_naar_balans(offerte: dict, wie: str, materiaalkost_bedrag: float | None = None) -> list[str]:
    """Stuurt de omzet van een offerte naar Balans, en optioneel een
    materiaalkost-uitgave. materiaalkost_bedrag is het bedrag dat je zelf
    invult (standaard voorgevuld met de schatting uit de offerte, maar vaak
    afwijkend van de echte aankoopprijs) - None of 0 = niet versturen.
    Geeft de lijst met aangemaakte transactie-id's terug en markeert de
    offerte lokaal als verstuurd."""
    ws = _transacties_worksheet()
    omschrijving_basis = f"Offerte {offerte.get('nummer', '')}".strip()
    if offerte.get("deal"):
        omschrijving_basis += f" - {offerte['deal']}"

    nieuwe_rijen = []
    ids = []

    totaalprijs = float(offerte.get("totaalprijs") or 0)
    if totaalprijs > 0:
        id_, rij = _nieuwe_rij("inkomst", totaalprijs, wie, "Klant-inkomsten", omschrijving_basis)
        nieuwe_rijen.append(rij)
        ids.append(id_)

    if materiaalkost_bedrag and materiaalkost_bedrag > 0:
        id_, rij = _nieuwe_rij(
            "uitgave", materiaalkost_bedrag, "samen", "Materiaal",
            f"{omschrijving_basis} (materiaalkost, geschat - pas aan zodra de echte factuur binnen is)",
        )
        nieuwe_rijen.append(rij)
        ids.append(id_)

    if nieuwe_rijen:
        ws.append_rows(nieuwe_rijen)
        _markeer_verstuurd(int(offerte["id"]), ids)

    return ids
