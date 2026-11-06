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
    ("villarreal", "Villarreal", "ES", "Villarreal", "https://villarrealcf.es/es/venta-de-entradas/", parse_villarreal),
    ("chelsea", "Chelsea", "EN", "Chelsea", "https://www.chelseafc.com/en/tickets/mens-tickets", parse_chelsea),
    ("celta", "Celta de Vigo", "ES", "Celta de Vigo", "https://rccelta.es/en/rccelta-tickets/", parse_celta),
    ("frankfurt", "Eintracht Frankfurt", "DE", "Eintracht Frankfurt", "https://stores.eintracht.de/tickets/profis/", parse_frankfurt),
    ("freiburg", "SC Freiburg", "DE", "SC Freiburg", "https://www.scfreiburg.com/heimtickets/", parse_freiburg),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, parser):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)

    def haal_op():
        return parser(t.haal_tekst(pagina, test), sleutel, pagina)

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=haal_op)


ALLE = [_maak(*c) for c in CLUBS]
