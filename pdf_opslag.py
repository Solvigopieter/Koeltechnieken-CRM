"""
Solvigo CRM – PDF-opslag via Google Sheets

Slaat offerte-PDF's op als base64 in een apart tabblad 'pdf_opslag' in je Sheet.
Dit tabblad zit NIET in TABEL_KOLOMMEN en wordt dus niet bij elke paginalading
meegelezen — alleen wanneer je een PDF opent of uploadt.

Werkt zonder Google Drive, dus geen quota-problemen met gratis Gmail.
"""
from __future__ import annotations

import base64

import streamlit as st

# Max bestandsgrootte: ~4 MB (base64 = ~5.3 MB, past in een Google Sheets-cel via API)
MAX_PDF_BYTES = 4 * 1024 * 1024

TAB_NAAM = "pdf_opslag"
KOLOMMEN = ["offerte_id", "bestandsnaam", "data"]


def _worksheet():
    """Haal of maak het pdf_opslag-tabblad."""
    # Importeer db hier om circulaire import te vermijden.
    import db
    ss = db._spreadsheet()
    try:
        return ss.worksheet(TAB_NAAM)
    except Exception:
        ws = ss.add_worksheet(title=TAB_NAAM, rows=100, cols=3)
        ws.update(values=[KOLOMMEN], range_name="A1")
        return ws


def sla_op(offerte_id: int, bestandsnaam: str, pdf_bytes: bytes) -> bool:
    """
    Sla een PDF op voor een offerte. Vervangt een eventueel bestaand bestand.

    Returns True bij succes, False bij fout (bv. te groot).
    """
    if len(pdf_bytes) > MAX_PDF_BYTES:
        return False

    # Verwijder bestaande PDF voor deze offerte
    verwijder(offerte_id)

    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    ws = _worksheet()
    ws.append_row(
        [str(offerte_id), bestandsnaam, b64],
        value_input_option="RAW",
    )
    return True


def haal_op(offerte_id: int) -> tuple[str, bytes] | None:
    """
    Haal de PDF op voor een offerte.

    Returns (bestandsnaam, pdf_bytes) of None als er geen PDF is.
    """
    ws = _worksheet()
    records = ws.get_all_records()
    for record in records:
        try:
            if str(record.get("offerte_id", "")) == str(offerte_id):
                naam = record.get("bestandsnaam", "offerte.pdf")
                data = record.get("data", "")
                if data:
                    return naam, base64.b64decode(data)
        except Exception:
            continue
    return None


def verwijder(offerte_id: int):
    """Verwijder de PDF voor een offerte."""
    ws = _worksheet()
    try:
        waarden = ws.get_all_values()
    except Exception:
        return
    for idx, rij in enumerate(waarden[1:], start=2):
        if rij and str(rij[0]) == str(offerte_id):
            try:
                ws.delete_rows(idx)
            except Exception:
                pass
            return


def heeft_pdf(offerte_id: int) -> bool:
    """Check of er een PDF is zonder de hele data op te halen."""
    ws = _worksheet()
    try:
        waarden = ws.get_all_values()
    except Exception:
        return False
    for rij in waarden[1:]:
        if rij and str(rij[0]) == str(offerte_id):
            return True
    return False
