"""Leesprogramma's voor Juventus, RB Leipzig, Villarreal, Chelsea, Celta de Vigo, Eintracht Frankfurt en SC Freiburg.

Alleen SC Freiburg toont echte startmomenten van de voorverkoop. De andere clubs tonen of de verkoop open is (nu)
of nog niet (info); dat leest dit bestand uit de zichtbare tekst van de pagina.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd

SPAANS = ("real madrid", "barcelona", "atlético", "atletico", "sevilla", "betis", "valencia", "villarreal", "athletic", "sociedad", "celta",
          "osasuna", "getafe", "espanyol", "alavés", "alaves", "rayo", "mallorca", "girona", "levante", "elche", "deportivo", "málaga", "malaga",
          "racing", "las palmas", "almería", "valladolid", "leganés", "oviedo")
COMP = {"serie a": "Serie A", "coppa italia": "Coppa Italia", "uefa europa league": "Europa League", "europa league": "Europa League",
        "uefa champions league": "Champions League", "champions league": "Champions League", "bundesliga": "Bundesliga",
        "dfb-pokal": "DFB-Pokal", "uefa conference league": "Conference League", "premier league": "Premier League"}
FOTER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def comp(naam):
    return COMP.get(naam.strip().lower(), naam.strip())


def naam(tekst):
    """Nette clubnaam uit hoofdletters; kent ook afkortingen als PSG en streepjes."""
    n = t.mooie_naam(tekst)
    n = re.sub(r"-(\w)", lambda m: "-" + m.group(1).upper(), n)
    return {"Psg": "PSG", "Afc Bournemouth": "AFC Bournemouth"}.get(n, n)


def spaans(club_naam):
    return any(k in club_naam.lower() for k in SPAANS)


def regels_van(tekst):
    return [r.strip() for r in tekst.splitlines() if r.strip()]


# ---------------------------------------------------------------- Juventus
JUVE = re.compile(r"^(\d{2})/(\d{2})(?:-(\d{1,2}):(\d{2}))?$")


def parse_juventus(tekst, club="juventus", bron=""):
    regels = regels_van(tekst)
    stop = next((i for i, r in enumerate(regels) if r == "VIP HOSPITALITY" and i > 20), len(regels))
    uit = []
    for i, r in enumerate(regels[:stop]):
        m = JUVE.match(r)
        if not m or i < 1 or i + 3 >= stop or regels[i + 1] != "JUVENTUS":
            continue
        dag, maand = int(m.group(1)), int(m.group(2))
        uur = int(m.group(3)) if m.group(3) else None
        d = t.jaar_voor_dag(dag, maand, uur or 0, int(m.group(4) or 0))
        if not d:
            continue
        aftrap = d if uur is not None else t.tekst_fmt(d, alleen_datum=True)
        status = regels[i + 3].upper()
        nu = "BUY" in status
        uit.append(wedstrijd(club, naam(regels[i + 2]), comp(regels[i - 1]), aftrap, nu=nu, info=not nu,
                             noot="Verkoop is open (startmoment niet getoond)." if nu else "Nog niet in de verkoop; je kunt je aanmelden voor een bericht.", bron=bron))
    return uit


# Elke wedstrijd heeft bij Juventus een eigen pagina met het blok TIMING: per groep de dag en het uur waarop de verkoop begint.
JUVE_KOP = re.compile(r"^\w+,\s+(\d{1,2})\s+([A-Z]{3})\s+(\d{4})\b")
JUVE_FASE = re.compile(r"^(MEMBER[^:]*|JUVENTUS CARD|EXTRA TICKET HOLDERS|SEASON TICKET HOLDERS|GENERAL SALE)\s*:\s*(.*)$")
JUVE_TIJD_A = re.compile(r"(\d{1,2}):(\d{2})\s*([AP]M)\s+on\s+\w+,?\s+([A-Za-z]+)\s+(\d{1,2})", re.I)
JUVE_TIJD_B = re.compile(r"\w+,\s+([A-Za-z]+)\s+(\d{1,2})\s+at\s+(\d{1,2}):(\d{2})\s*([AP]M)", re.I)
JUVE_GROEPEN = (("MEMBER", "lid", "Member (J1897 / Black&White)"), ("JUVENTUS CARD", "clubkaart", "Juventus Card"),
                ("EXTRA TICKET HOLDERS", "seizoen", "Seizoenkaarthouders (extra kaarten)"), ("SEASON TICKET HOLDERS", "seizoen", "Seizoenkaarthouders"),
                ("GENERAL SALE", "vrij", "Vrije verkoop"))


def parse_juventus_pagina(tekst):
    """Geef (datum 'JJJJ-MM-DD', fases) van een wedstrijdpagina, of None."""
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    kop = next((JUVE_KOP.match(r) for r in regels[:20] if JUVE_KOP.match(r)), None)
    if not kop or "TIMING" not in regels:
        return None
    maand = t.MAANDEN_EN.get(kop.group(2).lower())
    if not maand:
        return None
    datum = f"{int(kop.group(3)):04d}-{maand:02d}-{int(kop.group(1)):02d}"
    fases, gezien = [], set()
    for r in regels[regels.index("TIMING") + 1:]:
        if r.startswith(("BUY NOW", "PRICES")):
            break
        m = JUVE_FASE.match(r)
        if not m:
            continue
        groep = next(((g, l) for sleutel, g, l in JUVE_GROEPEN if m.group(1).upper().startswith(sleutel)), None)
        if not groep or groep[0] in gezien:
            continue
        rest = m.group(2)
        a, b = JUVE_TIJD_A.search(rest), JUVE_TIJD_B.search(rest)
        if a:
            uur, minuut, ap, mnd, dag = int(a.group(1)), int(a.group(2)), a.group(3), a.group(4), int(a.group(5))
        elif b:
            mnd, dag, uur, minuut, ap = b.group(1), int(b.group(2)), int(b.group(3)), int(b.group(4)), b.group(5)
        else:
            continue
        mnd_nr = t.MAANDEN_EN.get(mnd[:3].lower())
        if not mnd_nr:
            continue
        d = t.jaar_voor_dag(dag, mnd_nr, uur % 12 + (12 if ap.upper() == "PM" else 0), minuut, t.NL, terug=250)
        if d:
            gezien.add(groep[0])
            fases.append([groep[0], t.tekst_fmt(d), groep[1]])
    fases.sort(key=lambda f: f[1])
    return datum, fases


def haal_juventus(pagina, test, sleutel="juventus"):
    testmap = os.environ.get("JUVENTUS_DETAIL_MAP", "")
    uit = parse_juventus(t.haal_tekst(pagina, test), sleutel, pagina)
    try:
        paginas = t.haal_paginas(pagina, r"/tickets/standard/first-team-men/juventus-", 20, testmap)
    except Exception:  # noqa: BLE001
        paginas = []
    for _, tekst in paginas:
        res = parse_juventus_pagina(tekst)
        if not res or not res[1]:
            continue
        datum, fases = res
        for w in uit:
            if str(w["aftrap"])[:10] == datum:
                w["fases"] = fases
                w["info"] = False
                w["noot"] = "Verkoopmomenten volgens de club (Italiaanse tijd is gelijk aan Nederlandse tijd)."
    return uit


# ---------------------------------------------------------------- RB Leipzig
LEIPZIG_REGEL = re.compile(r"^HOME MATCH VS\.\s+(.+)$", re.I)
LEIPZIG_DATUM = re.compile(r"^\w{3},\s+([A-Za-z]{3})\s+(\d{1,2})\s+·\s+(?:(\d{1,2}):(\d{2})|TBA)$")


def parse_leipzig(tekst, club="leipzig", bron=""):
    """De pagina toont alleen de wedstrijden die nu in de voorverkoop zijn; andere wedstrijden staan er niet op."""
    regels = regels_van(tekst)
    uit = []
    for i, r in enumerate(regels):
        m = LEIPZIG_REGEL.match(r)
        if not m or i + 1 >= len(regels):
            continue
        dm = LEIPZIG_DATUM.match(regels[i + 1])
        maand = t.MAANDEN_EN.get(dm.group(1).lower()) if dm else None
        if not maand:
            continue
        uur = int(dm.group(3)) if dm.group(3) else None
        d = t.jaar_voor_dag(int(dm.group(2)), maand, uur or 0, int(dm.group(4) or 0))
        if not d:
            continue
        aftrap = d if uur is not None else t.tekst_fmt(d, alleen_datum=True)
        compnaam = regels[i - 3].split("·")[0] if i >= 3 and "·" in regels[i - 3] else ""
        beschikbaar = regels[i + 3] if i + 3 < len(regels) else ""
        uit.append(wedstrijd(club, naam(m.group(1)), comp(compnaam), aftrap, nu=True,
                             noot="In de voorverkoop (startmoment en doelgroep niet getoond)." + (f" Status: {beschikbaar}." if "ticket" in beschikbaar.lower() or "availab" in beschikbaar.lower() else ""),
                             bron=bron))
    return uit


def parse_leipzig_json(antwoorden, club="leipzig", bron=""):
    """De site van Leipzig stuurt de hele seizoenskalender mee, met per wedstrijd 'preSaleDate' (alleen een datum) en 'ticketInfo'."""
    import json as _json

    wedstrijden, gezien = [], set()
    nu_ = datetime.now(t.NL)
    for tekst in antwoorden:
        try:
            matches = _json.loads(tekst)["data"]["matchPlans"]["matches"]
        except Exception:  # noqa: BLE001
            continue
        for m in matches:
            try:
                if m.get("matchState") == "Played" or (m.get("homeTeam") or {}).get("name") != "RB Leipzig":
                    continue
                sleutel = (m["date"], m.get("description"))
                if sleutel in gezien:
                    continue
                gezien.add(sleutel)
                tegen = (m.get("awayTeam") or {}).get("name") or ""
                if m.get("time"):
                    aftrap = m["date"] + "T" + m["time"][:5]
                else:
                    aftrap = m["date"]
                fases, nu, info, noot = [], False, False, ""
                info_ticket = m.get("ticketInfo") or {}
                pre = m.get("preSaleDate")
                if pre and datetime.fromisoformat(pre).date() > nu_.date():
                    fases = [["lid", pre, "Voorverkoop (doelgroep niet vermeld)"]]
                    noot = "De club vermeldt alleen de dag waarop de voorverkoop begint."
                elif info_ticket:
                    nu = True
                    niveau = {"GOOD": "goed", "LIMITED": "beperkt", "SOLDOUT": "uitverkocht"}.get(str(info_ticket.get("availabilityLevel", "")).upper(), "")
                    noot = "Verkoop is open (startmoment niet getoond)." + (f" Beschikbaarheid: {niveau}." if niveau else "")
                else:
                    info, noot = True, "Nog niet in de verkoop."
                wedstrijden.append(wedstrijd(club, tegen, comp(m.get("competitionName", "")), aftrap, fases=fases, nu=nu, info=info, noot=noot, bron=bron))
            except Exception:  # noqa: BLE001
                continue
    return wedstrijden


def haal_leipzig(pagina, test, sleutel="leipzig"):
    testbestand = os.environ.get("LEIPZIG_JSON_BESTAND", "")
    try:
        uit = parse_leipzig_json(t.haal_json(pagina, "matchPlans", testbestand), sleutel, pagina)
    except Exception:  # noqa: BLE001
        uit = []
    return uit or parse_leipzig(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- Villarreal
VIL_DATUM = re.compile(r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{1,2}):(\d{2})$")


def parse_villarreal(tekst, club="villarreal", bron=""):
    regels = regels_van(tekst)
    uit = []
    for i, r in enumerate(regels):
        m = VIL_DATUM.match(r)
        if not m or i + 4 >= len(regels):
            continue
        if "CERÁMICA" not in regels[i + 1].upper() and "CERAMICA" not in regels[i + 1].upper():
            continue  # uitwedstrijd
        thuis, tegen, status = regels[i + 2], regels[i + 3], regels[i + 4].upper()
        if thuis.upper() != "VILLARREAL":
            continue
        aftrap = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4)), int(m.group(5)), tzinfo=t.NL)
        nu = "VENTA" in status
        uit.append(wedstrijd(club, naam(tegen), "La Liga" if spaans(tegen) else "Champions League", aftrap, nu=nu, info=not nu,
                             noot="Verkoop is open (startmoment niet getoond)." if nu else "Nog niet in de verkoop (\"próximamente\").", bron=bron))
    return uit


# ---------------------------------------------------------------- Chelsea
CHELSEA = re.compile(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s*\|\s*(.+?)\s*\|\s*(\d{1,2}(?::\d{2})?\s*[ap]m)")


def parse_chelsea(tekst, club="chelsea", bron=""):
    """Gewone kaarten voor Premier League-wedstrijden zijn alleen voor leden; de pagina toont geen startmomenten."""
    regels = regels_van(tekst)
    uit = []
    for i, r in enumerate(regels):
        m = CHELSEA.match(r)
        if not m or i < 2 or "stamford bridge" not in m.group(4).lower():
            continue
        maand = t.MAANDEN_EN.get(m.group(2).lower())
        if not maand:
            continue
        uur, minuut = t.klok(m.group(5))
        d = t.naar_nl(datetime(int(m.group(3)), maand, int(m.group(1)), uur, minuut), t.LONDEN)
        uit.append(wedstrijd(club, regels[i - 2], comp(regels[i - 1]), d, info=True,
                             noot="Kaarten voor leden; zie de ticketsite van Chelsea voor het verkoopmoment.", bron=bron))
    return uit


# Per thuiswedstrijd publiceert Chelsea een nieuwsbericht met het aanvraagvenster voor leden, ongeveer een maand van tevoren.
CHELSEA_ARTIKEL = "https://www.chelseafc.com/en/news/article/premier-league-ticket-news-{slug}-at-home-2026-27"
CHELSEA_VENSTER = re.compile(r"Ticket application window (opens|closes)\s*[\u2013\u2014-]\s*\w+\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.I)
CHELSEA_SUFFIX = ("united", "city", "town", "fc", "albion", "hotspur", "wanderers", "rovers", "county")


def chelsea_slugs(tegen):
    """Mogelijke adresdelen voor een tegenstander: volledige naam, zonder 'United/City/...' en alleen het eerste woord."""
    woorden = re.sub(r"[^a-z0-9 ]", "", tegen.lower().replace("&", "and")).split()
    kort = [w for w in woorden if w not in CHELSEA_SUFFIX] or woorden
    kandidaten = ["-".join(woorden), "-".join(kort), woorden[0] if woorden else "", woorden[-1] if woorden else ""]
    return [k for i, k in enumerate(kandidaten) if k and k not in kandidaten[:i]]


def parse_chelsea_artikel(tekst, tegen):
    """Geef (opent, sluit) als 'JJJJ-MM-DDTUU:MM' in Nederlandse tijd, of None als het bericht niet over deze wedstrijd gaat."""
    if tegen.split()[0].lower() not in tekst.lower():
        return None
    gevonden = {}
    for m in CHELSEA_VENSTER.finditer(tekst):
        soort = m.group(1).lower()
        maand = t.MAANDEN_EN.get(m.group(3)[:3].lower())
        if soort in gevonden or not maand:
            continue  # alleen het eerste venster (leden); het venster voor toegankelijkheid komt daarna
        uur = int(m.group(4)) % 12 + (12 if m.group(6).lower() == "pm" else 0)
        d = t.jaar_voor_dag(int(m.group(2)), maand, uur, int(m.group(5) or 0), t.LONDEN, terug=120)
        if d:
            gevonden[soort] = t.tekst_fmt(d)
    return (gevonden["opens"], gevonden.get("closes")) if "opens" in gevonden else None


def verrijk_chelsea(wedstrijden, haal=None, dagen_vooruit=50):
    """Zoek bij wedstrijden in de komende weken het nieuwsbericht met het aanvraagvenster voor leden."""
    haal = haal or (lambda adres: t.haal_tekst(adres))
    nu = datetime.now(t.NL)
    for w in wedstrijden:
        try:
            aftrap = w["aftrap"] if isinstance(w["aftrap"], datetime) else datetime.fromisoformat(w["aftrap"]).replace(tzinfo=t.NL)
        except (TypeError, ValueError):
            continue
        if not (0 <= (aftrap - nu).days <= dagen_vooruit):
            continue
        for slug in chelsea_slugs(w["tegen"]):
            try:
                tekst = haal(CHELSEA_ARTIKEL.format(slug=slug))
            except Exception:  # noqa: BLE001
                continue
            venster = parse_chelsea_artikel(tekst, w["tegen"])
            if venster:
                opent, sluit = venster
                w["fases"] = [["lid", opent, "Aanvraagvenster voor leden (True Blue+, True Blue, CFC Blue, Junior Blue)"]]
                w["info"] = False
                w["noot"] = "Leden vragen kaarten aan in een venster" + (f" dat sluit op {datetime.fromisoformat(sluit).strftime('%d-%m')} om {sluit[11:]} uur (NL-tijd)" if sluit else "") + "; je krijgt achteraf bericht of je kaarten hebt."
                break


# ---------------------------------------------------------------- Celta de Vigo
CELTA = re.compile(r"^\w{3}\.\s+(\d{1,2})\s+de\s+([A-Za-z]+)\s*\|\s*(\d{1,2}):(\d{2})h$")


def parse_celta(tekst, club="celta", bron=""):
    """Wedstrijden zonder vaste datum ('pendiente de confirmar') laten we weg."""
    regels = regels_van(tekst)
    uit = []
    for i, r in enumerate(regels):
        m = CELTA.match(r)
        if not m or i < 2:
            continue
        maand = t.MAANDEN_EN.get(m.group(2)[:3].lower())
        if not maand or regels[i - 2] != "CELTA":
            continue
        d = t.jaar_voor_dag(int(m.group(1)), maand, int(m.group(3)), int(m.group(4)))
        if not d:
            continue
        tegen = regels[i - 1]
        status = " ".join(regels[i + 1:i + 4]).upper()
        nu = "COMPRAR" in status
        uit.append(wedstrijd(club, naam(tegen), "La Liga" if spaans(tegen) else "Europa League", d, nu=nu, info=not nu,
                             noot="Verkoop is open (startmoment niet getoond)." if nu else "Nog niet in de verkoop; je kunt je aanmelden voor een bericht.", bron=bron))
    return uit


# ---------------------------------------------------------------- Eintracht Frankfurt
FRA_WEDSTRIJD = re.compile(r"^Eintracht Männer - (.+)$")
FRA_DATUM = re.compile(r"\|\s*(?:\w{2,}\.?,?\s*)?(\d{2})\.(\d{2})(?:\.\d{4})?(?:-(\d{2})\.(\d{2})\.(\d{4}))?\.?(\d{4})?\s*(?:\|\s*(\d{1,2})[.:](\d{2}) Uhr)?")


def parse_frankfurt(tekst, club="frankfurt", bron=""):
    """Alleen de thuiswedstrijden van het eerste herenelftal; 'Hier Tickets sichern!' betekent dat de verkoop open is."""
    regels = regels_van(tekst)
    start = next((i for i, r in enumerate(regels) if r.startswith("Heimspiele der Männer")), 0)
    einde = next((i for i, r in enumerate(regels) if r.startswith("Auswärtsspiele")), len(regels))
    uit = []
    for i in range(start, einde):
        m = FRA_WEDSTRIJD.match(regels[i])
        if not m or i + 3 >= len(regels):
            continue
        info_regel = regels[i + 2]
        dm = re.search(r"\|\s*(?:\w+\.?,?\s*)?(\d{2})\.(\d{2})\.(?:-\d{2}\.\d{2}\.)?(\d{4})(?:\s*\|\s*(\d{1,2})[.:](\d{2}) Uhr)?", info_regel)
        bereik = re.search(r"\|\s*(\d{2})\.-\d{2}\.(\d{2})\.(\d{4})", info_regel)  # '04.-06.12.2026': eerste dag van het weekend
        if bereik:
            dm = re.match(r"(\d{2})(\d{2})(\d{4})()()", bereik.group(1) + bereik.group(2) + bereik.group(3))
        if not dm:
            continue
        dag, maand, jaar = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        if dm.group(4):
            aftrap = t.tekst_fmt(datetime(jaar, maand, dag, int(dm.group(4)), int(dm.group(5))))
        else:
            aftrap = datetime(jaar, maand, dag).strftime("%Y-%m-%d")
        blok = " ".join(regels[i + 3:i + 5]).lower()
        nu = "tickets sichern" in blok
        compnaam = regels[i + 3] if regels[i + 3] and "Tickets" not in regels[i + 3] else "Bundesliga"
        uit.append(wedstrijd(club, naam(m.group(1)) if m.group(1).isupper() else m.group(1), comp(compnaam), aftrap, nu=nu, info=not nu,
                             noot="Verkoop is open (startmoment niet getoond)." if nu else "Nog niet in de verkoop.", bron=bron))
    return uit


# ---------------------------------------------------------------- SC Freiburg
FRE_DATUM = re.compile(r"^\w+\s*//\s*(\d{2})\.(\d{2})\.(\d{4})\s*//\s*(\d{1,2}):(\d{2})$")
FRE_FASE = re.compile(r"^(.*?)\s*-\s*(.*?)\s*\n?\s*Mitgliedervorverkauf ab dem (\d{2})\.(\d{2})\.(\d{2})")


def parse_freiburg(tekst, club="freiburg", bron=""):
    regels = regels_van(tekst)
    uit = []
    for i, r in enumerate(regels):
        if r != "SC FREIBURG" or i + 4 >= len(regels) or regels[i + 1] != "VS":
            continue
        dm = FRE_DATUM.match(regels[i + 3])
        if not dm:
            continue
        tegen = regels[i + 2]
        aftrap = datetime(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)), int(dm.group(4)), int(dm.group(5)), tzinfo=t.NL)
        compnaam = regels[i - 1].split(" - ")[0]
        uit.append({"tegen": tegen, "comp": compnaam, "aftrap": aftrap,
                    "blok": " ".join(regels[i + 4:i + 9]).upper()})
    # verkoopfases staan in een tabel verderop: 'SC Freiburg - FC Twente Enschede ... Mitgliedervorverkauf ab dem 08.10.26'
    tabel = tekst[tekst.find("VERKAUFSPHASEN"):]
    rijen = re.findall(r"SC Freiburg - ([^\n]+?)\s*\n+\s*(Freier Vorverkauf|Mitgliedervorverkauf(?: ab dem (\d{2})\.(\d{2})\.(\d{2}))?)", tabel)
    resultaat = []
    for w in uit:
        sleutels = [s for s in re.split(r"[\s.]+", w["tegen"].lower()) if len(s) >= 4]
        fases, nu = [], False
        rij = next((x for x in rijen if any(s in x[0].lower() for s in sleutels)), None)
        if rij and rij[2]:
            d = datetime(2000 + int(rij[4]), int(rij[3]), int(rij[2]))
            fases = [["lid", d.strftime("%Y-%m-%d") + "T09:30", "Mitglieder-Vorverkauf: Joker-Phase (90 Min.)"],
                     ["lid", d.strftime("%Y-%m-%d") + "T12:00", "Mitglieder-Vorverkauf (regulär)"]]
        elif rij:
            nu = True  # 'Freier Vorverkauf': de vrije verkoop is al begonnen
        elif "FREIER VORVERKAUF" in w["blok"]:
            nu = True
        # een wedstrijd met een eindstand (bijv. '3:2') is al gespeeld
        if re.search(r"\b\d:\d\b", w["blok"]):
            continue
        resultaat.append(wedstrijd(club, w["tegen"] if not w["tegen"].isupper() else naam(w["tegen"]), comp(w["comp"]), w["aftrap"], fases=fases, nu=nu,
                                   info=not nu and not fases, noot="Daarna volgt vrije verkoop zolang er kaarten zijn." if fases else ("Vrije voorverkoop is gestart." if nu else ""), bron=bron))
    return resultaat


CLUBS = [
    ("juventus", "Juventus", "IT", "Juventus", "https://www.juventus.com/en/tickets/", parse_juventus),
    ("leipzig", "RB Leipzig", "DE", "RB Leipzig", "https://rbleipzig.com/en/matches-tickets", parse_leipzig),
    ("villarreal", "Villarreal CF", "ES", "Villarreal", "https://villarrealcf.es/es/venta-de-entradas/", parse_villarreal),
    ("chelsea", "Chelsea", "EN", "Chelsea", "https://www.chelseafc.com/en/tickets/mens-tickets", parse_chelsea),
    ("celta", "Celta de Vigo", "ES", "Celta de Vigo", "https://rccelta.es/en/rccelta-tickets/", parse_celta),
    ("frankfurt", "Eintracht Frankfurt", "DE", "Eintracht Frankfurt", "https://stores.eintracht.de/tickets/profis/", parse_frankfurt),
    ("freiburg", "SC Freiburg", "DE", "SC Freiburg", "https://www.scfreiburg.com/heimtickets/", parse_freiburg),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, parser):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)

    def haal_op():
        if sleutel in EIGEN_HALER:
            return EIGEN_HALER[sleutel](pagina, test, sleutel)
        uit = parser(t.haal_tekst(pagina, test), sleutel, pagina)
        if sleutel == "chelsea" and not test:
            verrijk_chelsea(uit)
        return uit

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=haal_op)


EIGEN_HALER = {"juventus": haal_juventus, "leipzig": haal_leipzig}
ALLE = [_maak(*c) for c in CLUBS]
