"""Fulham: een nieuwsbericht per thuiswedstrijd ('Brighton (H) tickets') met de verkoopmomenten.

De tijden staan in Engelse tijd; wij rekenen ze om naar Nederlandse tijd.
"""
import os
import re
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs5 import DAGEN, ORD, maand, moment, regels_van, toekomst, uur

FU_TITEL = re.compile(r"^(.+?)\s*\(H\)\s*tickets$", re.I)
FU_AFTRAP = re.compile(DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+),?\s*kick-off\s*(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)
FU_MOMENT = re.compile(r"from\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)\s+on\s+" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)(?:\s*\(([^)]*)\))?", re.I)
FU_AANTAL = re.compile(r"\b(one|two|three|four|five|six|\d+)\s+tickets?\b", re.I)
GETAL = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
FU_NAMEN = {"Brighton": "Brighton & Hove Albion", "Spurs": "Tottenham Hotspur", "Man Utd": "Manchester United", "Man City": "Manchester City",
            "Newcastle": "Newcastle United", "Forest": "Nottingham Forest", "West Ham": "West Ham United", "Wolves": "Wolverhampton Wanderers",
            "Leeds": "Leeds United", "Palace": "Crystal Palace", "Villa": "Aston Villa", "Bournemouth": "AFC Bournemouth", "Leicester": "Leicester City"}


def _aantal(tekst):
    m = FU_AANTAL.search(tekst or "")
    if not m:
        return ""
    n = GETAL.get(m.group(1).lower()) or int(m.group(1))
    return f" (max. {n} ticket{'s' if n != 1 else ''})"


def parse_fulham_artikel(tekst, club="fulham", bron=""):
    regels = regels_van(tekst)
    kop = next((FU_TITEL.match(r) for r in regels[:60] if FU_TITEL.match(r)), None)
    if not kop:
        return None
    af = FU_AFTRAP.search(tekst)
    if not af:
        return None
    h, mi = uur(af.group(3), af.group(4), af.group(5))
    aftrap = moment(af.group(1), af.group(2), h, mi, terug=20)
    if not aftrap or not toekomst(aftrap):
        return None
    fases, vorige = [], 0
    for m in FU_MOMENT.finditer(tekst):
        venster = tekst[max(vorige, m.start() - 110):m.start()]
        vorige = m.end()
        extra = _aantal(m.group(6))
        if re.search(r"general sale", venster, re.I):
            groep, label = "vrij", "Vrije verkoop" + extra
        elif re.search(r"booking history", venster, re.I):
            groep, label = "vrij", "Supporters met boekingsgeschiedenis" + extra
        elif re.search(r"season ticket", venster, re.I):
            groep, label = "seizoen", "Seizoenkaarthouders (extra kaarten)"
        elif re.search(r"member", venster, re.I):
            groep, label = "lid", "Leden" + extra
        else:
            continue
        h2, m2 = uur(m.group(1), m.group(2), m.group(3))
        d = moment(m.group(4), m.group(5), h2, m2)
        if d and not any(f[1] == d and f[0] == groep for f in fases):
            fases.append([groep, d, label])
    if not fases:
        return None
    fases.sort(key=lambda f: f[1])
    naam = kop.group(1).strip()
    tegen = FU_NAMEN.get(naam, naam)
    comp = "Premier League"
    for sleutel_c, naam_c in (("FA Cup", "FA Cup"), ("Carabao", "EFL Cup"), ("EFL Cup", "EFL Cup"), ("League Cup", "EFL Cup")):
        if sleutel_c.lower() in tekst.lower()[:1500]:
            comp = naam_c
            break
    return wedstrijd(club, tegen, comp, aftrap, fases=fases, nu=False, info=False,
                     noot="Tijden in Nederlandse tijd (omgerekend uit Brits).", bron=bron)


def haal_fulham(pagina, test, sleutel="fulham"):
    testmap = os.environ.get("FULHAM_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/news/\d{4}/[a-z]+/\d+/[a-z0-9-]*(?:home-tickets|h-tickets)/?$", 10, testmap):
        w = parse_fulham_artikel(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
            uit.append(w)
    return uit


CLUBS = [
    ("fulham", "Fulham", "EN", "Fulham (artikelen)", "https://www.fulhamfc.com/news/", haal_fulham),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, BEHOUD=True, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
