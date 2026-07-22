"""
Solvigo Koeltechnieken CRM – databasemodule.

Standaard lokaal SQLite. Voor Streamlit Cloud: Google Sheets via secrets:

crm_storage = "google_sheets"
google_sheet_id = "..."
[gcp_service_account]
# inhoud van je service-account JSON in TOML-vorm
"""
from __future__ import annotations

import sqlite3
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import streamlit as st
except ImportError:
    class _StreamlitFallback:
        secrets = {}
    st = _StreamlitFallback()

DB_PAD = Path(__file__).parent / "kt_crm.db"
UPLOAD_MAP = Path(__file__).parent / "uploads"
UPLOAD_MAP.mkdir(exist_ok=True)

TABEL_KOLOMMEN: dict[str, list[str]] = {
    "organisaties": [
        "id", "naam", "type", "btw", "adres", "gemeente", "sector", "website",
        "status", "relatietype", "notities", "aangemaakt",
        "klantnummer", "email", "telefoon",
    ],
    "contacten": [
        "id", "organisatie_id", "naam", "functie", "email", "telefoon", "linkedin",
        "rol", "notities",
    ],
    "installaties": [
        "id", "naam", "adres", "gemeente", "organisatie_id", "partner_id",
        "type_gebouw", "bouwjaar", "btw_6_ok", "elektrisch", "gewenste_ruimtes",
        "bestaand_toestel", "toestel_type", "merk_model", "vermogen_kw",
        "plaatsingsjaar", "koelmiddel", "bereikbaarheid", "notities",
    ],
    "deals": [
        "id", "titel", "type_installatie", "organisatie_id", "partner_id",
        "installatie_id", "contact_id", "waarde", "kans", "bron", "deadline",
        "verantwoordelijke", "stadium", "prioriteit", "aangemaakt", "gewijzigd",
    ],
    "acties": [
        "id", "datum", "prioriteit", "organisatie_id", "installatie_id", "partner_id",
        "deal_id", "actie", "verantwoordelijke", "status", "aangemaakt",
    ],
    "plaatsbezoeken": [
        "id", "deal_id", "installatie_id", "datum", "aanwezigen",
        "gewenste_ruimtes", "vermogen_inschatting", "plaats_binnenunit",
        "plaats_buitenunit", "leidingtrace", "leidinglengte_m", "elektrische_aansluiting",
        "condensafvoer", "boorwerk", "bereikbaarheid", "hoogtewerker",
        "technische_opmerkingen", "conclusie", "advies",
    ],
    "offertes": [
        "id", "deal_id", "installatie_id", "nummer", "type", "totaalprijs",
        "btw_tarief", "status", "datum", "opmerkingen", "bron", "generator_id",
        "pdf_bestandsnaam", "materiaalkost", "nettowinst",
    ],
    "jobs": [
        "id", "deal_id", "installatie_id", "datum", "team", "toestellen",
        "werkzaamheden", "status", "indienststelling", "werkverslag",
    ],
    "onderhoudscontracten": [
        "id", "organisatie_id", "installatie_id", "toestel", "frequentie",
        "prijs_per_beurt", "laatste_beurt", "volgende_beurt", "status", "notities",
    ],
    "communicatie": [
        "id", "datum", "type", "organisatie_id", "partner_id", "deal_id",
        "installatie_id", "contact_id", "samenvatting", "volgende_stap",
    ],
    "bestanden": [
        "id", "entiteit", "entiteit_id", "categorie", "bestandsnaam", "pad", "datum",
    ],
}

# Kolommen die ECHTE getallen bevatten (dus veilig om als getal in te lezen).
# Alle andere kolommen (telefoon, klantnummer, adres, ...) blijven altijd platte
# tekst — anders verliest bv. een telefoonnummer "0471234567" zijn voorloopnul.
NUMERIC_KOLOMMEN: dict[str, set[str]] = {
    "installaties": {"bouwjaar", "btw_6_ok", "vermogen_kw", "plaatsingsjaar", "bestaand_toestel"},
    "deals": {"waarde", "kans"},
    "plaatsbezoeken": {"leidinglengte_m", "hoogtewerker"},
    "offertes": {"totaalprijs", "materiaalkost", "nettowinst"},
    "onderhoudscontracten": {"prijs_per_beurt"},
}

STANDAARDEN: dict[str, dict[str, Any]] = {
    "organisaties": {
        "type": "Eindklant", "status": "Prospect", "relatietype": "Prospect",
        "aangemaakt": lambda: date.today().isoformat(),
    },
    "installaties": {"btw_6_ok": 0, "bestaand_toestel": 0},
    "deals": {
        "waarde": 0, "kans": 50, "verantwoordelijke": "Pieter", "stadium": "Nieuwe lead",
        "prioriteit": "Normaal", "type_installatie": "Airco",
        "aangemaakt": lambda: date.today().isoformat(),
        "gewijzigd": lambda: date.today().isoformat(),
    },
    "acties": {
        "prioriteit": "Normaal", "verantwoordelijke": "Pieter", "status": "Open",
        "aangemaakt": lambda: date.today().isoformat(),
    },
    "plaatsbezoeken": {"hoogtewerker": 0},
    "offertes": {
        "status": "Concept", "btw_tarief": "6%", "bron": "CRM",
        "datum": lambda: date.today().isoformat(),
    },
    "jobs": {"status": "Gepland"},
    "onderhoudscontracten": {"frequentie": "Jaarlijks", "status": "Actief"},
    "communicatie": {"datum": lambda: date.today().isoformat()},
    "bestanden": {"categorie": "Document", "datum": lambda: date.today().isoformat()},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS organisaties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    klantnummer TEXT,
    naam TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'Eindklant',
    btw TEXT, adres TEXT, gemeente TEXT, sector TEXT, website TEXT,
    email TEXT, telefoon TEXT,
    status TEXT NOT NULL DEFAULT 'Prospect',
    relatietype TEXT NOT NULL DEFAULT 'Prospect',
    notities TEXT,
    aangemaakt TEXT DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS contacten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organisatie_id INTEGER REFERENCES organisaties(id) ON DELETE CASCADE,
    naam TEXT NOT NULL,
    functie TEXT, email TEXT, telefoon TEXT, linkedin TEXT,
    rol TEXT,
    notities TEXT
);

CREATE TABLE IF NOT EXISTS installaties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naam TEXT NOT NULL,
    adres TEXT, gemeente TEXT,
    organisatie_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    partner_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    type_gebouw TEXT, bouwjaar INTEGER, btw_6_ok INTEGER DEFAULT 0,
    elektrisch TEXT, gewenste_ruimtes TEXT,
    bestaand_toestel INTEGER DEFAULT 0, toestel_type TEXT, merk_model TEXT,
    vermogen_kw REAL, plaatsingsjaar INTEGER, koelmiddel TEXT,
    bereikbaarheid TEXT, notities TEXT
);

CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titel TEXT NOT NULL,
    type_installatie TEXT DEFAULT 'Airco',
    organisatie_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    partner_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    installatie_id INTEGER REFERENCES installaties(id) ON DELETE SET NULL,
    contact_id INTEGER REFERENCES contacten(id) ON DELETE SET NULL,
    waarde REAL DEFAULT 0, kans INTEGER DEFAULT 50,
    bron TEXT, deadline TEXT, verantwoordelijke TEXT DEFAULT 'Pieter',
    stadium TEXT NOT NULL DEFAULT 'Nieuwe lead',
    prioriteit TEXT DEFAULT 'Normaal',
    aangemaakt TEXT DEFAULT (date('now')),
    gewijzigd TEXT DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS acties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datum TEXT NOT NULL,
    prioriteit TEXT DEFAULT 'Normaal',
    organisatie_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    installatie_id INTEGER REFERENCES installaties(id) ON DELETE SET NULL,
    partner_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    deal_id INTEGER REFERENCES deals(id) ON DELETE SET NULL,
    actie TEXT NOT NULL,
    verantwoordelijke TEXT DEFAULT 'Pieter',
    status TEXT DEFAULT 'Open',
    aangemaakt TEXT DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS plaatsbezoeken (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER REFERENCES deals(id) ON DELETE SET NULL,
    installatie_id INTEGER REFERENCES installaties(id) ON DELETE SET NULL,
    datum TEXT,
    aanwezigen TEXT, gewenste_ruimtes TEXT, vermogen_inschatting TEXT,
    plaats_binnenunit TEXT, plaats_buitenunit TEXT, leidingtrace TEXT,
    leidinglengte_m REAL, elektrische_aansluiting TEXT, condensafvoer TEXT,
    boorwerk TEXT, bereikbaarheid TEXT, hoogtewerker INTEGER DEFAULT 0,
    technische_opmerkingen TEXT, conclusie TEXT, advies TEXT
);

CREATE TABLE IF NOT EXISTS offertes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER REFERENCES deals(id) ON DELETE SET NULL,
    installatie_id INTEGER REFERENCES installaties(id) ON DELETE SET NULL,
    nummer TEXT, type TEXT, totaalprijs REAL,
    btw_tarief TEXT DEFAULT '6%',
    status TEXT DEFAULT 'Concept',
    datum TEXT DEFAULT (date('now')),
    opmerkingen TEXT,
    bron TEXT DEFAULT 'CRM',
    generator_id TEXT,
    pdf_bestandsnaam TEXT,
    materiaalkost REAL, nettowinst REAL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER REFERENCES deals(id) ON DELETE SET NULL,
    installatie_id INTEGER REFERENCES installaties(id) ON DELETE SET NULL,
    datum TEXT, team TEXT, toestellen TEXT, werkzaamheden TEXT,
    status TEXT DEFAULT 'Gepland',
    indienststelling TEXT,
    werkverslag TEXT
);

CREATE TABLE IF NOT EXISTS onderhoudscontracten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organisatie_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    installatie_id INTEGER REFERENCES installaties(id) ON DELETE SET NULL,
    toestel TEXT, frequentie TEXT DEFAULT 'Jaarlijks',
    prijs_per_beurt REAL,
    laatste_beurt TEXT, volgende_beurt TEXT,
    status TEXT DEFAULT 'Actief',
    notities TEXT
);

CREATE TABLE IF NOT EXISTS communicatie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datum TEXT DEFAULT (date('now')),
    type TEXT,
    organisatie_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    partner_id INTEGER REFERENCES organisaties(id) ON DELETE SET NULL,
    deal_id INTEGER REFERENCES deals(id) ON DELETE SET NULL,
    installatie_id INTEGER REFERENCES installaties(id) ON DELETE SET NULL,
    contact_id INTEGER REFERENCES contacten(id) ON DELETE SET NULL,
    samenvatting TEXT, volgende_stap TEXT
);

CREATE TABLE IF NOT EXISTS bestanden (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entiteit TEXT NOT NULL,
    entiteit_id INTEGER NOT NULL,
    categorie TEXT DEFAULT 'Document',
    bestandsnaam TEXT, pad TEXT,
    datum TEXT DEFAULT (date('now'))
);
"""

# ---------- configuratie ----------

def _secret_get(naam: str, standaard: Any = None) -> Any:
    try:
        return st.secrets.get(naam, standaard)
    except Exception:
        return standaard


def gebruik_google_sheets() -> bool:
    opslag = str(_secret_get("crm_storage", "sqlite")).strip().lower()
    sheet_id = _secret_get("google_sheet_id") or _secret_get("gsheet_id")
    return opslag in {"google_sheets", "gsheets", "sheets", "google"} and bool(sheet_id)


def opslag_label() -> str:
    return "Google Sheets" if gebruik_google_sheets() else "SQLite lokaal"


def moet_seed_demo_data() -> bool:
    expliciet = _secret_get("seed_demo_data", None)
    if expliciet is not None:
        return bool(expliciet)
    return not gebruik_google_sheets()


# ---------- SQLite backend ----------

def verbind() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PAD, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _sqlite_init_db():
    con = verbind()
    con.executescript(SCHEMA)
    con.commit()
    con.close()


def _sqlite_query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    con = verbind()
    df = pd.read_sql_query(sql, con, params=params)
    con.close()
    return df


def _sqlite_voer_uit(sql: str, params: tuple = ()) -> int:
    con = verbind()
    cur = con.execute(sql, params)
    con.commit()
    rij_id = cur.lastrowid
    con.close()
    return rij_id


# ---------- Google Sheets backend ----------

_GS_CLIENT = None
_GS_SPREADSHEET = None
_GS_WORKSHEETS: dict[str, Any] = {}
_GS_RECORDS_CACHE: dict[str, list[dict]] | None = None
_GS_RECORDS_CACHE_TS = 0.0
_GS_CACHE_SECONDS = 30
_GS_INITIALIZED = False


def _invalidate_google_cache():
    global _GS_RECORDS_CACHE, _GS_RECORDS_CACHE_TS
    _GS_RECORDS_CACHE = None
    _GS_RECORDS_CACHE_TS = 0.0


def _worksheet_index() -> dict[str, Any]:
    global _GS_WORKSHEETS
    if not _GS_WORKSHEETS:
        ss = _spreadsheet()
        _GS_WORKSHEETS = {ws.title: ws for ws in ss.worksheets()}
    return _GS_WORKSHEETS


def _google_credentials_dict() -> dict:
    creds = _secret_get("gcp_service_account", None)
    if creds is None:
        creds = _secret_get("google_service_account", None)
    if creds is None:
        raise RuntimeError(
            "Google Sheets is gekozen, maar [gcp_service_account] ontbreekt in Streamlit secrets."
        )
    data = dict(creds)
    if "private_key" in data:
        data["private_key"] = str(data["private_key"]).replace("\\n", "\n")
    return data


def _spreadsheet():
    global _GS_CLIENT, _GS_SPREADSHEET
    if _GS_SPREADSHEET is not None:
        return _GS_SPREADSHEET
    try:
        import gspread
    except ImportError as exc:
        raise RuntimeError(
            "Python-package 'gspread' ontbreekt. Voeg gspread en google-auth toe aan requirements.txt."
        ) from exc

    sheet_id = _secret_get("google_sheet_id") or _secret_get("gsheet_id")
    if not sheet_id:
        raise RuntimeError("google_sheet_id ontbreekt in Streamlit secrets.")

    _GS_CLIENT = gspread.service_account_from_dict(_google_credentials_dict())
    _GS_SPREADSHEET = _GS_CLIENT.open_by_key(str(sheet_id))
    return _GS_SPREADSHEET


def _worksheet(tabel: str):
    if tabel not in TABEL_KOLOMMEN:
        raise ValueError(f"Onbekende tabel: {tabel}")

    ss = _spreadsheet()
    headers = TABEL_KOLOMMEN[tabel]
    werkbladen = _worksheet_index()
    ws = werkbladen.get(tabel)

    if ws is None:
        ws = ss.add_worksheet(title=tabel, rows=1000, cols=max(20, len(headers)))
        werkbladen[tabel] = ws
        ws.update(values=[headers], range_name="A1")

    return ws


def _sheet_records_direct(tabel: str) -> list[dict]:
    ws = _worksheet(tabel)
    headers = TABEL_KOLOMMEN[tabel]
    try:
        records = ws.get_all_records(expected_headers=headers)
    except Exception:
        try:
            records = ws.get_all_records()
        except Exception:
            return []

    opgeschoond: list[dict] = []
    for record in records:
        if not any(str(record.get(k, "")).strip() for k in headers):
            continue
        opgeschoond.append({k: record.get(k, "") for k in headers})
    return opgeschoond


def _google_all_records(force: bool = False) -> dict[str, list[dict]]:
    global _GS_RECORDS_CACHE, _GS_RECORDS_CACHE_TS
    nu = time.time()
    if (
        not force
        and _GS_RECORDS_CACHE is not None
        and (nu - _GS_RECORDS_CACHE_TS) < _GS_CACHE_SECONDS
    ):
        return _GS_RECORDS_CACHE

    data = {tabel: _sheet_records_direct(tabel) for tabel in TABEL_KOLOMMEN}
    _GS_RECORDS_CACHE = data
    _GS_RECORDS_CACHE_TS = nu
    return data


def _sheet_records(tabel: str) -> list[dict]:
    return list(_google_all_records().get(tabel, []))


def _als_sheet_waarde(waarde: Any) -> Any:
    """Zet een Python-waarde om naar wat naar Google Sheets geschreven wordt.

    Getallen met decimalen (float) worden bewust als LETTERLIJKE TEKST
    weggeschreven, met een apostrof-voorvoegsel. Zonder dat trucje kan Google
    Sheets (bij een Belgische/Nederlandse spreadsheet-locale, komma als
    decimaalteken) een kommagetal als 4789.72 verkeerd inlezen: het
    decimaalteken verdwijnt dan en er komt 478972 uit in plaats van 4789,72.
    Gehele getallen (int) zijn hier niet gevoelig voor en blijven gewoon
    een getal.
    """
    if waarde is None:
        return ""
    try:
        if pd.isna(waarde):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(waarde, bool):
        return int(waarde)
    if isinstance(waarde, float):
        return f"'{waarde:.2f}"
    return waarde


def _van_sheet_getal(waarde: Any) -> Any:
    """Leest een mogelijk forced-text/apostrof-genoteerd getal terug in als
    een echt getal (int of float). Niet-numerieke tekst blijft ongewijzigd."""
    if isinstance(waarde, (int, float)):
        return waarde
    if not isinstance(waarde, str):
        return waarde
    tekst = waarde.strip().lstrip("'")
    if tekst == "":
        return waarde
    try:
        getal = float(tekst)
        return int(getal) if getal.is_integer() else getal
    except ValueError:
        pass
    # Vangnet voor reeds foutief opgeslagen Belgisch-genoteerde tekst ("4.789,72")
    try:
        getal = float(tekst.replace(".", "").replace(",", "."))
        return int(getal) if getal.is_integer() else getal
    except ValueError:
        return waarde


def _met_standaarden(tabel: str, data: dict) -> dict:
    nieuw = dict(data)
    for sleutel, waarde in STANDAARDEN.get(tabel, {}).items():
        if sleutel not in nieuw or nieuw.get(sleutel) in (None, ""):
            nieuw[sleutel] = waarde() if callable(waarde) else waarde
    return nieuw


def _volgend_id(tabel: str) -> int:
    ids: list[int] = []
    for rij in _sheet_records(tabel):
        try:
            ids.append(int(rij.get("id") or 0))
        except (TypeError, ValueError):
            continue
    return (max(ids) + 1) if ids else 1


def _google_init_db():
    global _GS_INITIALIZED
    if _GS_INITIALIZED:
        return
    for tabel in TABEL_KOLOMMEN:
        ws = _worksheet(tabel)
        try:
            huidige_headers = ws.row_values(1)
            verwacht = TABEL_KOLOMMEN[tabel]
            ontbrekend = [h for h in verwacht if h not in huidige_headers]
            if ontbrekend:
                nieuwe_headers = huidige_headers + ontbrekend
                ws.update(values=[nieuwe_headers], range_name="A1")
        except Exception:
            pass
    _GS_INITIALIZED = True


def _google_temp_sqlite() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    alle_records = _google_all_records()
    for tabel, kolommen in TABEL_KOLOMMEN.items():
        records = alle_records.get(tabel, [])
        if not records:
            continue
        numeriek = NUMERIC_KOLOMMEN.get(tabel, set())
        plekken = ", ".join("?" for _ in kolommen)
        sql = f"INSERT INTO {tabel} ({', '.join(kolommen)}) VALUES ({plekken})"
        for record in records:
            waarden = []
            for k in kolommen:
                v = record.get(k, "")
                if v == "":
                    waarden.append(None)
                elif k == "id" or k in numeriek:
                    waarden.append(_van_sheet_getal(v))
                else:
                    waarden.append(v)
            try:
                con.execute(sql, waarden)
            except sqlite3.IntegrityError:
                # Eén onvolledige/kapotte rij (bv. een leeg verplicht veld zoals
                # 'datum' of 'actie') mag NOOIT de volledige app platleggen — alle
                # andere tabellen en rijen moeten gewoon blijven werken. Deze ene
                # rij wordt overgeslagen; de brondata in de Sheet blijft intact,
                # enkel deze rij verschijnt niet in de CRM-weergave tot ze
                # hersteld is (bv. het lege veld invullen in Google Sheets zelf).
                continue
    con.commit()
    return con


def _google_query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    con = _google_temp_sqlite()
    df = pd.read_sql_query(sql, con, params=params)
    con.close()
    return df


def _google_voeg_toe(tabel: str, data: dict) -> int:
    if tabel not in TABEL_KOLOMMEN:
        raise ValueError(f"Onbekende tabel: {tabel}")
    ws = _worksheet(tabel)
    rij_id = int(data.get("id") or _volgend_id(tabel))
    record = _met_standaarden(tabel, dict(data, id=rij_id))
    waarden = [_als_sheet_waarde(record.get(k, "")) for k in TABEL_KOLOMMEN[tabel]]
    ws.append_row(waarden, value_input_option="USER_ENTERED")
    _invalidate_google_cache()
    return rij_id


def _google_haal_rij(tabel: str, rij_id: int):
    try:
        rij_id_int = int(rij_id)
    except (TypeError, ValueError):
        return None
    numeriek = NUMERIC_KOLOMMEN.get(tabel, set())
    for record in _sheet_records(tabel):
        try:
            if int(record.get("id") or 0) == rij_id_int:
                return {
                    k: (None if v == "" else (_van_sheet_getal(v) if (k == "id" or k in numeriek) else v))
                    for k, v in record.items()
                }
        except (TypeError, ValueError):
            continue
    return None


def _google_werk_bij(tabel: str, rij_id: int, data: dict):
    ws = _worksheet(tabel)
    headers = TABEL_KOLOMMEN[tabel]
    waarden = ws.get_all_values()
    if not waarden:
        ws.update(values=[headers], range_name="A1")
        waarden = [headers]

    doelrij = None
    for idx, rij in enumerate(waarden[1:], start=2):
        if not rij:
            continue
        try:
            if int(rij[0]) == int(rij_id):
                doelrij = idx
                break
        except (TypeError, ValueError, IndexError):
            continue
    if doelrij is None:
        return

    bestaand = _google_haal_rij(tabel, rij_id) or {"id": rij_id}
    bestaand.update(data)
    rijwaarden = [_als_sheet_waarde(bestaand.get(k, "")) for k in headers]
    laatste_kolom = chr(ord("A") + len(headers) - 1) if len(headers) <= 26 else "ZZ"
    ws.update(values=[rijwaarden], range_name=f"A{doelrij}:{laatste_kolom}{doelrij}")
    _invalidate_google_cache()


def _google_verwijder(tabel: str, rij_id: int):
    ws = _worksheet(tabel)
    waarden = ws.get_all_values()
    for idx, rij in enumerate(waarden[1:], start=2):
        if not rij:
            continue
        try:
            if int(rij[0]) == int(rij_id):
                ws.delete_rows(idx)
                _invalidate_google_cache()
                return
        except (TypeError, ValueError, IndexError):
            continue


# ---------- publieke API ----------

def init_db():
    if gebruik_google_sheets():
        _google_init_db()
    else:
        _sqlite_init_db()


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    if gebruik_google_sheets():
        return _google_query_df(sql, params)
    return _sqlite_query_df(sql, params)


def haal_rij(tabel: str, rij_id: int):
    if gebruik_google_sheets():
        return _google_haal_rij(tabel, rij_id)
    con = verbind()
    rij = con.execute(f"SELECT * FROM {tabel} WHERE id = ?", (rij_id,)).fetchone()
    con.close()
    return dict(rij) if rij else None


def voeg_toe(tabel: str, data: dict) -> int:
    if gebruik_google_sheets():
        return _google_voeg_toe(tabel, data)
    kolommen = ", ".join(data.keys())
    plekken = ", ".join("?" for _ in data)
    return _sqlite_voer_uit(f"INSERT INTO {tabel} ({kolommen}) VALUES ({plekken})", tuple(data.values()))


def werk_bij(tabel: str, rij_id: int, data: dict):
    if gebruik_google_sheets():
        _google_werk_bij(tabel, rij_id, data)
        return
    zetten = ", ".join(f"{k} = ?" for k in data)
    _sqlite_voer_uit(f"UPDATE {tabel} SET {zetten} WHERE id = ?", (*data.values(), rij_id))


def verwijder(tabel: str, rij_id: int):
    if gebruik_google_sheets():
        _google_verwijder(tabel, rij_id)
        return
    _sqlite_voer_uit(f"DELETE FROM {tabel} WHERE id = ?", (rij_id,))


# ---------- keuzelijsten ----------

def opties(tabel: str, waar: str = "", params: tuple = ()) -> dict:
    sql = f"SELECT id, naam FROM {tabel}"
    if waar:
        sql += f" WHERE {waar}"
    sql += " ORDER BY naam"
    df = query_df(sql, params)
    d = {0: "— geen —"}
    if not df.empty:
        d.update(dict(zip(df["id"].astype(int), df["naam"])))
    return d


def organisatie_opties(alleen_partners: bool = False, alleen_klanten: bool = False) -> dict:
    if alleen_partners:
        return opties("organisaties", "type IN ('Installateur','Aannemer','Partner','Leverancier')")
    if alleen_klanten:
        return opties("organisaties", "type = 'Eindklant'")
    return opties("organisaties")


def contact_opties(organisatie_id: int | None = None) -> dict:
    if organisatie_id:
        return opties("contacten", "organisatie_id = ?", (organisatie_id,))
    return opties("contacten")


def installatie_opties() -> dict:
    return opties("installaties")


def deal_opties() -> dict:
    df = query_df("SELECT id, titel FROM deals ORDER BY id DESC")
    d = {0: "— geen —"}
    if not df.empty:
        d.update(dict(zip(df["id"].astype(int), df["titel"])))
    return d
