"""Leesprogramma's voor Inter, Cagliari en AC Monza (Serie A). Italiaanse tijd = Nederlandse tijd.
- Inter: lijst met thuiswedstrijden, overal een koopknop (geen startmoment).
- Cagliari: Milan 'verkoop volgt binnenkort'; de rest 'tickets not available'.
- Monza: alleen de wedstrijdlijst (de clubpagina toont geen verkoopstatus)."""
import os
import re
from datetime import datetime, timedelta
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs6 import MAANDEN_IT, maand_en, toekomst
from .tekstclubs7 import NOOT_OPEN, SERIE_A, naam

NOOT_BINNENKORT = "Verkoop start binnenkort; datum nog niet bekend."
NOOT_NIET_BESCHIKBAAR = "Kaartverkoop nog niet gestart."
NOOT_MONZA = "Verkoopstatus niet getoond op de clubpagina."

# ---------------------------------------------------------------- Inter
IN_RIJ = re.compile(r"INTER\s*\n\s*VS\s*\n\s*([^\n]+?)\s*\n(?:[^\n]*\n){0,8}?\s*\w+day, (\d{1,2}) ([A-Za-z]+) (\d{4}) - (\d{1,2}):(\d{2})([^\n]*\n[^\n]*\n[^\n]*)")


def parse_inter(tekst, club="inter", bron=""):
    uit, gezien = [], {}
    for m in IN_RIJ.finditer(tekst):
        mnd = maand_en(m.group(3))
        if not mnd:
            continue
        datum = f"{m.group(4)}-{mnd:02d}-{int(m.group(2)):02d}"
        onzeker = "not confirmed" in m.group(7).lower()
        aftrap = datum if onzeker else f"{datum}T{int(m.group(5)):02d}:{m.group(6)}"
        tegen = naam(m.group(1))
        if not toekomst(aftrap):
            continue
        if tegen in SERIE_A:
            eerder = gezien.get(tegen)
            if eerder and abs((datetime.fromisoformat(datum) - eerder).days) <= 30:
                comp = "Coppa Italia"
            else:
                comp = "Serie A"
            gezien[tegen] = datetime.fromisoformat(datum)
        elif tegen.upper() == "AC MILAN":
            comp = "Serie A"
        else:
            comp = "Champions League"
        uit.append(wedstrijd(club, tegen, comp, aftrap, nu=True, noot=NOOT_OPEN, bron=bron))
    return uit


def haal_inter(pagina, test, sleutel="inter"):
    return parse_inter(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- Cagliari
CA_MILAN = re.compile(r"\n(\d{1,2})\s*\n\s*NOV\s*\n\s*Cagliari\s*\n\s*vs\s*\n\s*([^\n]+?)\s*\n\s*(Serie A|Coppa Italia)[^\n]*\n(?:[^\n]*\n){0,6}?\s*(\d{1,2}):(\d{2})\s*\n", re.I)
CA_RIJ = re.compile(r"(\d{1,2}) ([A-Za-z]+) \(\w{3}\)\s*\n\s*[^\n]+\n\s*(\d{1,2}):(\d{2})\s*\n\s*(Serie A|Coppa Italia)[^\n]*\n(?:[^\n]*\n){0,8}?\s*Cagliari\s*\n\s*([^\n]+?)\s*\n\s*(Tickets not available|Info|Buy[^\n]*)", re.I)


def parse_cagliari(tekst, club="cagliari", bron=""):
    uit = []
    m = CA_MILAN.search(tekst)
    if m:
        d = t.jaar_voor_dag(int(m.group(1)), 11, int(m.group(4)), int(m.group(5)), t.NL, terug=20)
        if d:
            uit.append(wedstrijd(club, naam(m.group(2)), m.group(3).title(), t.tekst_fmt(d), nu=False, info=True, noot=NOOT_BINNENKORT, bron=bron))
    for m in CA_RIJ.finditer(tekst):
        mnd = maand_en(m.group(2))
        if not mnd:
            continue
        d = t.jaar_voor_dag(int(m.group(1)), mnd, int(m.group(3)), int(m.group(4)), t.NL, terug=20)
        if not d:
            continue
        uit.append(wedstrijd(club, naam(m.group(6)), m.group(5).title(), t.tekst_fmt(d), nu=False, info=True, noot=NOOT_NIET_BESCHIKBAAR, bron=bron))
    return uit


def haal_cagliari(pagina, test, sleutel="cagliari"):
    return parse_cagliari(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- Monza
MO_RIJ = re.compile(r"^([^\n]+)\n(\d{1,2}):(\d{2})\n(\d{1,2}) ([A-Z]+) (\d{4})\n\n([^\n]+)\n([^\n]+)$", re.M)


def parse_monza(tekst, club="monza", bron=""):
    uit, gezien = [], set()
    for m in MO_RIJ.finditer(tekst):
        if m.group(1).strip().upper() != "AC MONZA":
            continue
        mnd = MAANDEN_IT.get(m.group(5).lower())
        if not mnd:
            continue
        datum = f"{m.group(6)}-{mnd:02d}-{int(m.group(4)):02d}"
        onzeker = "DA DEFINIRE" in m.group(7).upper()
        aftrap = datum if onzeker else f"{datum}T{int(m.group(2)):02d}:{m.group(3)}"
        tegen = naam(m.group(8))
        if (tegen, aftrap) in gezien or not toekomst(aftrap):
            continue
        gezien.add((tegen, aftrap))
        uit.append(wedstrijd(club, tegen, "Serie A", aftrap, nu=False, info=True, noot=NOOT_MONZA, bron=bron))
    return uit


def haal_monza(pagina, test, sleutel="monza"):
    return parse_monza(t.haal_tekst(pagina, test), sleutel, pagina)


CLUBS = [
    ("inter", "Inter", "IT", "Inter (tickets)", "https://www.inter.it/en/tickets", haal_inter),
    ("cagliari", "Cagliari Calcio", "IT", "Cagliari (tickets)", "https://cagliaricalcio.com/en/tickets/", haal_cagliari),
    ("monza", "AC Monza", "IT", "Monza (biglietti)", "https://www.acmonza.com/it/ticketing/", haal_monza),
]


def _maak(sleutel, naam_, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam_, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
