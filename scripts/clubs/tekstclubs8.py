"""Leesprogramma voor SS Lazio (Serie A): lijst met thuiswedstrijden + nieuwsartikelen met de verkoopmomenten.
De aftraptijd komt altijd uit de lijst (die is actueler dan de artikelen). Italiaanse tijd = Nederlandse tijd."""
import os
import re
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs6 import MAANDEN_IT, aftrap_dt, fase_moment, toekomst
from .tekstclubs7 import naam

LZ_RIJ = re.compile(r"^LAZIO\n([^\n]+)\n\n(?:GIORNATA \d+|[A-Z ]+)\n\n\w{3} (\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d)\n\n([^\n]+)", re.M)
LZ_TITEL = re.compile(r"SERIE A ENILIVE \| LAZIO-([A-Z .'’-]+?), (LA VENDITA DEI TAGLIANDI|TERZA FASE|VENDITA RISERVATA AGLI ABBONATI)", re.I)
LZ_MOMENT = re.compile(r"dalle (?:ore )?(\d{1,2}):(\d{2}) di \w+ (\d{1,2}) ([a-z]+)", re.I)
LZ_MOMENT3 = re.compile(r"a partire dalle ore (\d{1,2}):(\d{2}) di \w+ (\d{1,2}) ([a-z]+)", re.I)
NOOT_PRELAZIONE = "Tussenfase voor abonnees 2025/26 en Fidelity Card-houders: tijden niet getoond."
NOOT_TEVERE = "Voor Tribuna Tevere is een Fidelity Card (Eagle of Millenovecento) nodig."


def comp_naam(tekst):
    laag = tekst.lower()
    if "supercup" in laag:
        return "Supercoppa"
    if "coppa" in laag:
        return "Coppa Italia"
    return "Serie A"


def parse_lijst(tekst, club="lazio", bron=""):
    uit, gezien = [], set()
    for m in LZ_RIJ.finditer(tekst):
        tegen_ruw = m.group(1).strip()
        if tegen_ruw.upper() == "LAZIO":
            continue
        aftrap = f"{m.group(4)}-{m.group(3)}-{m.group(2)}T{m.group(5)}:{m.group(6)}"
        tegen = naam(tegen_ruw)
        if (tegen, aftrap) in gezien or not toekomst(aftrap):
            continue
        gezien.add((tegen, aftrap))
        comp = comp_naam(m.group(7))
        if comp == "Supercoppa":
            continue  # finale op neutraal terrein, geen thuiswedstrijd
        uit.append(wedstrijd(club, tegen, comp, aftrap, nu=False, info=True, noot="Verkoopmomenten nog niet bekendgemaakt.", bron=bron))
    return uit


def parse_artikel(tekst, aftrap):
    """Geeft (tegen, fase) of None. Het artikel hoort bij de wedstrijd met aftrap 'aftrap' (datum+tijd uit de lijst)."""
    k = LZ_TITEL.search(tekst)
    if not k:
        return None
    soort = k.group(2).upper()
    zoek = LZ_MOMENT3 if soort == "TERZA FASE" else LZ_MOMENT
    m = zoek.search(tekst[k.end():])
    if not m:
        return None
    mnd = MAANDEN_IT.get(m.group(4).lower())
    if not mnd:
        return None
    moment = fase_moment(m.group(3), mnd, int(m.group(1)), int(m.group(2)), aftrap_dt(aftrap))
    if not moment:
        return None
    if soort.startswith("VENDITA RISERVATA"):
        fase = ["seizoen", moment, "Abonnees Sud en Aquilotti (voorrang)"]
    else:
        fase = ["vrij", moment, "Vrije verkoop"]
    return naam(k.group(1)), fase


def haal_lazio(pagina, test, sleutel="lazio"):
    testmap = os.environ.get("LAZIO_DETAIL_MAP", "")
    uit = parse_lijst(t.haal_tekst(pagina, test), sleutel, pagina)
    try:
        paginas = t.haal_paginas(pagina, r"/news/biglietteria/serie-a-enilive-or-lazio-", 12, testmap)
    except Exception:  # noqa: BLE001
        paginas = []
    for adres, tekst in paginas:
        k = LZ_TITEL.search(tekst)
        if not k:
            continue
        tegen = naam(k.group(1))
        for w in uit:
            if w["tegen"].lower() != tegen.lower():
                continue
            res = parse_artikel(tekst, w["aftrap"])
            if not res:
                continue
            fase = res[1]
            if not any(f[0] == fase[0] and f[1] == fase[1] for f in w["fases"]):
                w["fases"].append(fase)
            w["fases"].sort(key=lambda f: f[1])
            w["info"], w["bron"] = False, adres
            w["noot"] = NOOT_TEVERE if tegen.lower() == "roma" else ""
    for w in uit:
        if w["tegen"].lower() == "roma" and w["fases"]:
            w["noot"] = NOOT_PRELAZIONE + " " + NOOT_TEVERE
    return uit


CLUBS = [("lazio", "SS Lazio", "IT", "Lazio (biglietteria)", "https://www.sslazio.it/it/biglietteria/matches", haal_lazio)]


def _maak(sleutel, naam_, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam_, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
