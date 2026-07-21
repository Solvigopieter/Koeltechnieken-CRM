"""
Solvigo Koeltechnieken CRM – voorbeelddata
Wordt eenmalig geladen als de database leeg is (enkel lokaal/SQLite standaard).
"""
from datetime import date, timedelta

import db


def _d(dagen: int) -> str:
    return (date.today() + timedelta(days=dagen)).isoformat()


def seed_indien_leeg():
    if not db.moet_seed_demo_data():
        return
    if not db.query_df("SELECT id FROM organisaties LIMIT 1").empty:
        return

    # --- organisaties ---
    org = {}
    org["janssens"] = db.voeg_toe("organisaties", dict(
        naam="Familie Janssens", type="Eindklant",
        adres="Lindelaan 3", gemeente="Herentals", sector="Particulier",
        status="Prospect", relatietype="Prospect",
        notities="Airco gevraagd voor 2 slaapkamers, via website."))
    org["peeters"] = db.voeg_toe("organisaties", dict(
        naam="Familie Peeters-Claes", type="Eindklant",
        adres="Kerkstraat 41", gemeente="Westerlo", sector="Particulier",
        status="Actief", relatietype="Eenmalige klant",
        notities="Warmtepomp ter vervanging van stookolieketel. Woning 1998 -> 6% BTW ok."))
    org["bakkerij"] = db.voeg_toe("organisaties", dict(
        naam="Bakkerij De Zoete Inval", type="Eindklant", btw="BE 0678.123.456",
        adres="Markt 12", gemeente="Geel", sector="Horeca / retail",
        status="Prospect", relatietype="Prospect",
        notities="Koeling winkelruimte + atelier. Vraagt onderhoud bestaande units mee."))
    org["bouwteam"] = db.voeg_toe("organisaties", dict(
        naam="Bouwteam Verlinden", type="Aannemer", btw="BE 0555.222.111",
        adres="Nijverheidsstraat 20", gemeente="Turnhout", sector="Bouw",
        website="https://www.bouwteamverlinden.be", status="Partner", relatietype="Strategische partner",
        notities="Geeft nieuwbouw- en renovatieprojecten door. Vaste samenwerking besproken."))

    # --- contacten ---
    con = {}
    con["janssens"] = db.voeg_toe("contacten", dict(
        organisatie_id=org["janssens"], naam="Tom Janssens", functie="Eigenaar",
        email="tom.janssens@telenet.be", telefoon="0475 12 34 56", rol="Beslisser",
        notities="Bellen na 17u."))
    con["peeters"] = db.voeg_toe("contacten", dict(
        organisatie_id=org["peeters"], naam="An Claes", functie="Eigenaar",
        email="an.claes@gmail.com", telefoon="0498 11 22 33", rol="Beslisser"))
    con["bakker"] = db.voeg_toe("contacten", dict(
        organisatie_id=org["bakkerij"], naam="Karel Mertens", functie="Zaakvoerder",
        email="info@dezoeteinval.be", telefoon="014 55 66 77", rol="Beslisser",
        notities="Enkel bereikbaar in de namiddag (bakker)."))
    con["verlinden"] = db.voeg_toe("contacten", dict(
        organisatie_id=org["bouwteam"], naam="Els Verlinden", functie="Projectleider",
        email="els@bouwteamverlinden.be", telefoon="0468 44 55 66", rol="Werfleider"))

    # --- installatie-adressen ---
    inst = {}
    inst["janssens"] = db.voeg_toe("installaties", dict(
        naam="Woning Janssens", adres="Lindelaan 3", gemeente="Herentals",
        organisatie_id=org["janssens"], type_gebouw="Woning", bouwjaar=2005, btw_6_ok=1,
        elektrisch="Mono 230V", gewenste_ruimtes="2 slaapkamers (verdieping)",
        bereikbaarheid="Buitenunit achteraan, ladder volstaat",
        notities="Leidingtracé via zolder mogelijk."))
    inst["peeters"] = db.voeg_toe("installaties", dict(
        naam="Woning Peeters-Claes", adres="Kerkstraat 41", gemeente="Westerlo",
        organisatie_id=org["peeters"], type_gebouw="Woning", bouwjaar=1998, btw_6_ok=1,
        elektrisch="Tri 3x400V+N", gewenste_ruimtes="Volledige woning (radiatoren)",
        bestaand_toestel=1, toestel_type="Andere", merk_model="Stookolieketel Viessmann",
        plaatsingsjaar=2001,
        bereikbaarheid="Technische ruimte kelder, goede toegang",
        notities="Lucht-water WP wordt enige centrale verwarming -> premie mogelijk."))
    inst["bakkerij"] = db.voeg_toe("installaties", dict(
        naam="Bakkerij Markt Geel", adres="Markt 12", gemeente="Geel",
        organisatie_id=org["bakkerij"], type_gebouw="Handelspand", bouwjaar=1985, btw_6_ok=0,
        elektrisch="Tri 3x230V", gewenste_ruimtes="Winkel + atelier",
        bestaand_toestel=1, toestel_type="Mono-split airco", merk_model="Daikin FTX 2016",
        vermogen_kw=5.0, plaatsingsjaar=2016, koelmiddel="R410A",
        bereikbaarheid="Buitenunit op plat dak, via luik",
        notities="Bestaande unit slecht onderhouden — onderhoudscontract voorstellen."))

    # --- deals ---
    deal = {}
    deal["janssens"] = db.voeg_toe("deals", dict(
        titel="Airco 2 slaapkamers Janssens (multi-split)",
        type_installatie="Airco",
        organisatie_id=org["janssens"], installatie_id=inst["janssens"], contact_id=con["janssens"],
        waarde=4200, kans=60, bron="Website", deadline=_d(21),
        stadium="Plaatsbezoek gepland", prioriteit="Hoog"))
    deal["peeters"] = db.voeg_toe("deals", dict(
        titel="Lucht-water warmtepomp Peeters-Claes",
        type_installatie="Warmtepomp",
        organisatie_id=org["peeters"], installatie_id=inst["peeters"], contact_id=con["peeters"],
        waarde=13500, kans=75, bron="Doorverwijzing", deadline=_d(30),
        stadium="Offerte verstuurd", prioriteit="Hoog"))
    deal["bakkerij"] = db.voeg_toe("deals", dict(
        titel="Koeling winkel + onderhoud Bakkerij De Zoete Inval",
        type_installatie="Airco",
        organisatie_id=org["bakkerij"], installatie_id=inst["bakkerij"], contact_id=con["bakker"],
        waarde=6800, kans=40, bron="Eigen prospectie", deadline=_d(45),
        stadium="Te kwalificeren", prioriteit="Normaal"))

    # --- acties ---
    db.voeg_toe("acties", dict(
        datum=_d(1), prioriteit="Hoog", organisatie_id=org["janssens"],
        installatie_id=inst["janssens"], deal_id=deal["janssens"],
        actie="Plaatsbezoek uitvoeren + verslag invullen", status="Open"))
    db.voeg_toe("acties", dict(
        datum=_d(-2), prioriteit="Normaal", organisatie_id=org["peeters"],
        deal_id=deal["peeters"], actie="Offerte opvolgen (verstuurd " + _d(-8) + ")",
        status="Open"))
    db.voeg_toe("acties", dict(
        datum=_d(5), prioriteit="Normaal", organisatie_id=org["bakkerij"],
        deal_id=deal["bakkerij"], actie="Karel bellen: behoefte + budget aftoetsen",
        status="Open"))

    # --- plaatsbezoek ---
    db.voeg_toe("plaatsbezoeken", dict(
        deal_id=deal["peeters"], installatie_id=inst["peeters"], datum=_d(-12),
        aanwezigen="Pieter, An Claes",
        gewenste_ruimtes="Volledige woning via bestaande radiatoren",
        vermogen_inschatting="±10 kW bij -7°C (warmteverliesberekening te verfijnen)",
        plaats_binnenunit="Technische ruimte kelder (hydromodule + boiler 200l)",
        plaats_buitenunit="Zijgevel, op sokkel, >3m van slaapkamerraam buren",
        leidingtrace="Kelderdoorvoer, 6m tot buitenunit",
        leidinglengte_m=6, elektrische_aansluiting="Tri 400V aanwezig, aparte kring te trekken",
        condensafvoer="Afloop naar regenput-overloop",
        boorwerk="1 doorvoer 52mm door kelderwand (beton)",
        bereikbaarheid="Goede toegang, geen hoogtewerker nodig",
        hoogtewerker=0,
        technische_opmerkingen="Radiatoren volstaan op 45°C vertrek, geen vloerverwarming.",
        conclusie="Lucht-water WP 10-11 kW, stookolieketel + tank te verwijderen.",
        advies="Offerte met 6% BTW en Mijn VerbouwPremie-voorwaarden meesturen."))

    # --- offertes ---
    db.voeg_toe("offertes", dict(
        deal_id=deal["peeters"], installatie_id=inst["peeters"],
        nummer="SLV-" + date.today().strftime("%Y%m%d") + "-PEETE",
        type="Warmtepomp", totaalprijs=13500, btw_tarief="6%",
        status="Verstuurd", datum=_d(-8), bron="Generator",
        opmerkingen="Opgemaakt in de offertegenerator, incl. premievermelding."))

    # --- jobs ---
    db.voeg_toe("jobs", dict(
        deal_id=deal["peeters"], installatie_id=inst["peeters"], datum=_d(20),
        team="Pieter + hulp", toestellen="Panasonic Aquarea 9kW + boiler 200l (onder voorbehoud)",
        werkzaamheden="Afbraak ketel, plaatsing WP + hydromodule, aansluiting radiatoren, indienststelling",
        status="Gepland",
        indienststelling="Vacumeren, lektest, wateraflaat testen, parameters instellen, uitleg klant"))

    # --- onderhoudscontract ---
    db.voeg_toe("onderhoudscontracten", dict(
        organisatie_id=org["bakkerij"], installatie_id=inst["bakkerij"],
        toestel="Daikin FTX 5kW (2016)", frequentie="Jaarlijks", prijs_per_beurt=145,
        laatste_beurt="", volgende_beurt=_d(25), status="Voorstel",
        notities="Voorstel meegenomen in offertetraject — sterk vervuilde filters gezien."))

    # --- communicatie ---
    db.voeg_toe("communicatie", dict(
        datum=_d(-3), type="Telefoongesprek", organisatie_id=org["janssens"],
        deal_id=deal["janssens"], contact_id=con["janssens"],
        samenvatting="Tom bevestigt interesse, plaatsbezoek ingepland.",
        volgende_stap="Plaatsbezoek uitvoeren en verslag maken."))
    db.voeg_toe("communicatie", dict(
        datum=_d(-8), type="Offerte", organisatie_id=org["peeters"], deal_id=deal["peeters"],
        contact_id=con["peeters"], samenvatting="Offerte warmtepomp verstuurd per e-mail (uit generator).",
        volgende_stap="Opvolgen binnen 7 dagen."))
