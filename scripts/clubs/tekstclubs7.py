"""Leesprogramma's voor Atalanta, Torino, AS Roma en Como (Serie A).

- Atalanta: een lijst met thuiswedstrijden en per wedstrijd een artikel 'ticket info' met het startmoment van de verkoop.
- Torino en Como: een lijst met thuiswedstrijden; de club toont voor alle wedstrijden een koopknop (geen startmoment).
- AS Roma: een lijst met per wedstrijd de status (koopknop, 'notify availability' of alleen hospitality).
Italiaanse tijd is gelijk aan Nederlandse tijd.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs6 import MAANDEN_IT, maand_en, toekomst

HOOFD = {"US", "SSC", "SS", "BC", "CFC", "ACF", "AC", "FC", "AS", "AFC", "PSV", "RB", "SC", "FK", "AEK"}
SERIE_A = {"Atalanta", "Bologna", "Cagliari", "Como", "Fiorentina", "Frosinone", "Genoa", "Inter", "Juventus", "Lazio", "Lecce",
           "Milan", "Roma", "AS Roma", "Monza", "Napoli", "Parma", "Sassuolo", "Torino", "Udinese", "Venezia", "Cremonese", "Verona", "Pisa"}
NOOT_OPEN = "Verkoop is open (startmoment niet getoond)."
NOOT_NU = "Nu in de verkoop; startmoment onbekend."
NOOT_AANMELDEN = "Nog niet in de verkoop; je kunt je aanmelden voor een bericht."


def naam(tekst):
    uit = []
    for w in tekst.strip().split():
        if w.upper() in HOOFD:
            uit.append(w.upper())
        elif "." in w and len(w) <= 5:
            uit.append(w.upper())
        elif "-" in w:
            uit.append("-".join(t.mooie_naam(x) for x in w.split("-")))
        elif w.isupper() or w.islower():
            uit.append(t.mooie_naam(w))
        else:
            uit.append(w)
    return " ".join(uit)


def comp_naam(tekst):
    laag = tekst.lower()
    if "champions" in laag:
        return "Champions League"
    if "conference" in laag:
        return "Conference League"
    if "europa league" in laag:
        return "Europa League"
    if "coppa" in laag:
        return "Coppa Italia"
    return "Serie A"


def regels_van(tekst):
    return [r.strip() for r in tekst.splitlines() if r.strip()]


# ---------------------------------------------------------------- Atalanta
AT_BLOK = re.compile(r"^(.+)\n(.+)\n((?:SERIE A|UEFA|COPPA)[^\n]*)\n\w+day (\d{1,2}), ([A-Za-z]+)\n(TICKET INFO|COMING SOON)\s*$", re.M)
AT_TITEL = re.compile(r"ATALANTA V\s+([A-Z][A-Z .'’-]+?):\s*TICKET INFO", re.I)
AT_AFTRAP = re.compile(r"scheduled for\s+\w+day\s+(\d{1,2})\s+([A-Za-z]+)\s+at\s+(\d{1,2}):(\d{2})", re.I)
AT_VERKOOP = re.compile(r"go on sale at\s+(\d{1,2}):(\d{2})\s*CET\s+on\s+\w+day\s+(\d{1,2})\s+([A-Za-z]+)", re.I)


def parse_atalanta_lijst(tekst, club="atalanta", bron=""):
    uit, gezien = [], set()
    for m in AT_BLOK.finditer(tekst):
        if m.group(1).strip().upper() != "ATALANTA":
            continue
        mnd = maand_en(m.group(5))
        if not mnd:
            continue
        d = t.jaar_voor_dag(int(m.group(4)), mnd, 12, 0, t.NL, terug=20)
        if not d:
            continue
        aftrap = t.tekst_fmt(d, alleen_datum=True)
        tegen = naam(m.group(2))
        if (tegen, aftrap) in gezien or not toekomst(aftrap):
            continue
        gezien.add((tegen, aftrap))
        uit.append(wedstrijd(club, tegen, comp_naam(m.group(3)), aftrap, nu=False, info=True,
                             noot="Verkoopmomenten nog niet bekendgemaakt.", bron=bron))
    return uit


def parse_atalanta_artikel(tekst):
    kop, af, vk = AT_TITEL.search(tekst), AT_AFTRAP.search(tekst), AT_VERKOOP.search(tekst)
    if not (kop and af and vk):
        return None
    ma, mv = maand_en(af.group(2)), maand_en(vk.group(4))
    if not ma or not mv:
        return None
    d = t.jaar_voor_dag(int(af.group(1)), ma, int(af.group(3)), int(af.group(4)), t.NL, terug=20)
    if not d:
        return None
    verkoop = t.jaar_voor(int(vk.group(3)), mv, int(vk.group(1)), int(vk.group(2)), d, t.NL)
    if not verkoop:
        return None
    return naam(kop.group(1)), t.tekst_fmt(d), t.tekst_fmt(d, alleen_datum=True), [["vrij", t.tekst_fmt(verkoop), "Vrije verkoop"]]


def haal_atalanta(pagina, test, sleutel="atalanta"):
    testmap = os.environ.get("ATALANTA_DETAIL_MAP", "")
    uit = parse_atalanta_lijst(t.haal_tekst(pagina, test), sleutel, pagina)
    try:
        paginas = t.haal_paginas(pagina, r"/news/atalanta-[a-z0-9-]*ticket-info", 10, testmap)
    except Exception:  # noqa: BLE001
        paginas = []
    for adres, tekst in paginas:
        res = parse_atalanta_artikel(tekst)
        if not res:
            continue
        tegen, aftrap, datum, fases = res
        for w in uit:
            if w["tegen"].lower() == tegen.lower() and str(w["aftrap"])[:10] == datum:
                w["aftrap"], w["fases"], w["info"], w["noot"], w["bron"] = aftrap, fases, False, "Voor de Curva-vakken is een Dea Card (clubkaart) nodig.", adres
    return uit


# ---------------------------------------------------------------- Torino
TO_RIJ = re.compile(r"TORINO\s*\nvs\s*\n([^\n]+)\n(DATA E ORA DA CONFERMARE\s+)?(\d{2})/(\d{2})/(\d{2})\s*-\s*(\d{2}):(\d{2})")


def parse_torino(tekst, club="torino", bron=""):
    uit, gezien = [], set()
    for m in TO_RIJ.finditer(tekst):
        datum = f"20{m.group(5)}-{m.group(4)}-{m.group(3)}"
        aftrap = datum if m.group(2) else f"{datum}T{m.group(6)}:{m.group(7)}"
        tegen = naam(m.group(1))
        if (tegen, aftrap) in gezien or not toekomst(aftrap):
            continue
        gezien.add((tegen, aftrap))
        uit.append(wedstrijd(club, tegen, "Serie A", aftrap, nu=True, noot=NOOT_OPEN, bron=bron))
    return uit


def haal_torino(pagina, test, sleutel="torino"):
    return parse_torino(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- AS Roma
RO_KOP = re.compile(r"^MEN\s*\n\w+,\s*([A-Z]{3})[A-Z]*\s+(\d{1,2})\s*\n(?:(\d{1,2}):(\d{2})\s*CET|DATE AND TIME TBC)\s*\n[^\n]+\n(.+)\nVS\n(.+)$", re.M)


def parse_roma(tekst, club="roma", bron=""):
    koppen = list(RO_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        if m.group(5).strip().upper() != "ROMA":
            continue
        mnd = t.MAANDEN_EN.get(m.group(1).lower())
        if not mnd:
            continue
        mu = (int(m.group(3)), int(m.group(4))) if m.group(3) else (0, 0)
        d = t.jaar_voor_dag(int(m.group(2)), mnd, mu[0], mu[1], t.NL, terug=20)
        if not d:
            continue
        aftrap = t.tekst_fmt(d) if m.group(3) else t.tekst_fmt(d, alleen_datum=True)
        if not toekomst(aftrap):
            continue
        eind = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = re.split(r"\n(?:[A-Z]+ 20\d\d)\n", tekst[m.end():eind])[0]
        regels = regels_van(blok)
        tegen = naam(m.group(6))
        comp = "Serie A" if tegen in SERIE_A else "UEFA"
        if "NOTIFY AVAILABILITY" in blok:
            uit.append(wedstrijd(club, tegen, comp, aftrap, nu=False, info=True, noot=NOOT_AANMELDEN, bron=bron))
        elif len(regels) > 1 and regels[0] == "MATCH DETAILS" and regels[1] == "BUY TICKETS":
            uit.append(wedstrijd(club, tegen, comp, aftrap, nu=True, noot=NOOT_NU, bron=bron))
        else:
            uit.append(wedstrijd(club, tegen, comp, aftrap, nu=False, info=True, noot="Kaarten zijn niet vrij beschikbaar (alleen hospitality).", bron=bron))
    return uit


def haal_roma(pagina, test, sleutel="roma"):
    return parse_roma(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- Como
CO_MAAND = re.compile(r"^(GENNAIO|FEBBRAIO|MARZO|APRILE|MAGGIO|GIUGNO|LUGLIO|AGOSTO|SETTEMBRE|OTTOBRE|NOVEMBRE|DICEMBRE)\s+(\d{4})$")
CO_DAG = re.compile(r"^(LUN|MAR|MER|GIO|VEN|SAB|DOM)$")


def parse_como(tekst, club="como", bron=""):
    regels = regels_van(tekst)
    uit, gezien = [], set()
    jaar = mnd = None
    i = 0
    while i < len(regels):
        m = CO_MAAND.match(regels[i])
        if m:
            mnd, jaar = MAANDEN_IT[m.group(1).lower()], int(m.group(2))
            i += 1
            continue
        if CO_DAG.match(regels[i]) and mnd and i + 2 < len(regels) and regels[i + 1].isdigit():
            dag = int(regels[i + 1])
            tm = re.match(r"(\d{1,2}):(\d{2})\s*CET", regels[i + 2])
            j = i + 3
            blok = []
            while j < len(regels) and regels[j] != "ACQUISTA ORA" and len(blok) < 8:
                blok.append(regels[j])
                j += 1
            if j < len(regels) and "COMO 1907" in blok:
                tegen = naam(blok[blok.index("COMO 1907") + 1]) if blok.index("COMO 1907") + 1 < len(blok) else None
                comp = next((comp_naam(b) for b in blok if b.upper().startswith(("UEFA", "COPPA"))), "Serie A")
                try:
                    datum = datetime(jaar, mnd, dag)
                except ValueError:
                    datum = None
                if tegen and datum:
                    aftrap = f"{jaar}-{mnd:02d}-{dag:02d}" + (f"T{int(tm.group(1)):02d}:{tm.group(2)}" if tm else "")
                    if toekomst(aftrap) and (tegen, aftrap) not in gezien:
                        gezien.add((tegen, aftrap))
                        uit.append(wedstrijd(club, tegen, comp, aftrap, nu=True, noot=NOOT_OPEN, bron=bron))
            i = j
        i += 1
    return uit


def haal_como(pagina, test, sleutel="como"):
    return parse_como(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- aansluiting
CLUBS = [
    ("atalanta", "Atalanta", "IT", "Atalanta (tickets)", "https://en.atalanta.it/ticket", haal_atalanta),
    ("torino", "Torino FC", "IT", "Torino (biglietteria)", "https://www.torinofc.it/biglietteria", haal_torino),
    ("roma", "AS Roma", "IT", "AS Roma (tickets)", "https://www.asroma.com/en/tickets/men", haal_roma),
    ("como", "Como 1907", "IT", "Como (tickets)", "https://tickets.comofootball.com/", haal_como),
]


def _maak(sleutel, naam_, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam_, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
