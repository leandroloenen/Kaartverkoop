"""Leesprogramma's voor Venezia en Parma (Serie A).

- Venezia: een overzichtspagina met alle thuiswedstrijden en per wedstrijd een nieuwsbericht met drie verkoopfases.
- Parma: de ticketpagina toont per wedstrijd de verkoopfases met datum en tijd.
Italiaanse tijd is gelijk aan Nederlandse tijd.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd

MAANDEN_IT = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
              "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12}
MAANDEN_EN_LANG = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
                   "september": 9, "october": 10, "november": 11, "december": 12}
MAAND_ENGELS = {**t.MAANDEN_EN, **MAANDEN_EN_LANG}
NOOT_INFO = "Verkoopmomenten nog niet bekendgemaakt."


def toekomst(aftrap):
    return datetime.fromisoformat(aftrap).date() >= datetime.now(t.NL).date()


def maand_en(woord):
    w = woord.strip().lower()
    return MAANDEN_EN_LANG.get(w) or t.MAANDEN_EN.get(w[:3])


def uur24(u, m, ap=None):
    h = int(u)
    if ap:
        h = h % 12 + (12 if ap.lower() == "pm" else 0)
    return h, int(m or 0)


def fase_moment(dag, mnd, h, mi, aftrap_dt):
    """Verkoopmoment (Nederlandse tijd) in het jaar waarin het voor de aftrap valt."""
    d = t.jaar_voor(int(dag), mnd, h, mi, aftrap_dt, t.NL)
    return t.tekst_fmt(d) if d else None


def aftrap_dt(aftrap):
    if len(aftrap) > 10:
        return datetime.fromisoformat(aftrap).replace(tzinfo=t.NL)
    return datetime.fromisoformat(aftrap + "T23:59").replace(tzinfo=t.NL)


# ---------------------------------------------------------------- Venezia
VE_RIJ = re.compile(r"VENEZIA\s*\n\s*([A-Z][A-Z .'’-]+?)\s*\n\s*(SERIE A|COPPA ITALIA)\s*\n\s*\w{3},\s*(\d{1,2})\s+([A-Za-z]+)\s*\|\s*(?:(\d{1,2}):(\d{2})|TBD)")
VE_TITEL = re.compile(r"TICKET SALES FOR VENEZIA\s*[-–]\s*([A-Z][A-Z .'’-]+?)\s*\n", re.I)
VE_FASE = re.compile(r"PHASE\s*(\d)\s*[–-][^\n]*\n(.*?)(?=PHASE\s*\d\s*[–-]|HOSPITALITY|AWAY SECTION|$)", re.S | re.I)
VE_TIJD = re.compile(r"(\d{1,2}):(\d{2})\s+on\s+\w+,\s+([A-Za-z]+)\s+(\d{1,2})")
VE_LABELS = {"1": ("seizoen", "Seizoenkaarthouders (voorrang)"), "2": ("clubkaart", "Supporter Card-houders (met korting)"),
             "3": ("vrij", "Vrije verkoop")}


def comp_it(naam):
    return "Coppa Italia" if "COPPA" in naam.upper() else "Serie A"


def parse_venezia_lijst(tekst, club="venezia", bron=""):
    uit, gezien = [], set()
    for m in VE_RIJ.finditer(tekst):
        mnd = MAANDEN_IT.get(m.group(4).lower())
        if not mnd:
            continue
        h, mi = (int(m.group(5)), int(m.group(6))) if m.group(5) else (0, 0)
        d = t.jaar_voor_dag(int(m.group(3)), mnd, h, mi, t.NL, terug=20)
        if not d:
            continue
        aftrap = t.tekst_fmt(d) if m.group(5) else t.tekst_fmt(d, alleen_datum=True)
        tegen = t.mooie_naam(m.group(1))
        if (tegen, aftrap) in gezien or not toekomst(aftrap):
            continue
        gezien.add((tegen, aftrap))
        uit.append(wedstrijd(club, tegen, comp_it(m.group(2)), aftrap, nu=False, info=True, noot=NOOT_INFO, bron=bron))
    return uit


def parse_venezia_artikel(tekst):
    """Geeft (tegenstander, fases) of None."""
    kop = VE_TITEL.search(tekst)
    if not kop:
        return None
    tegen = t.mooie_naam(kop.group(1))
    kick = re.search(r"scheduled for\s+\w+,\s+([A-Za-z]+)\s+(\d{1,2})\s+at\s+(\d{1,2}):(\d{2})", tekst)
    if not kick:
        return None
    mk = maand_en(kick.group(1))
    d = t.jaar_voor_dag(int(kick.group(2)), mk, int(kick.group(3)), int(kick.group(4)), t.NL, terug=20)
    if not d:
        return None
    adt = d
    fases = []
    for f in VE_FASE.finditer(tekst):
        groep_label = VE_LABELS.get(f.group(1))
        tm = VE_TIJD.search(f.group(2))
        if not groep_label or not tm:
            continue
        mnd = maand_en(tm.group(3))
        moment = fase_moment(tm.group(4), mnd, int(tm.group(1)), int(tm.group(2)), adt) if mnd else None
        if moment:
            fases.append([groep_label[0], moment, groep_label[1]])
    return tegen, t.tekst_fmt(adt, alleen_datum=True), fases


def haal_venezia(pagina, test, sleutel="venezia"):
    testmap = os.environ.get("VENEZIA_DETAIL_MAP", "")
    uit = parse_venezia_lijst(t.haal_tekst(pagina, test), sleutel, pagina)
    try:
        paginas = t.haal_paginas("https://en.veneziafc.it/", r"/news/serie-a-enilive-[a-z0-9-]*ticket-sales-for-venezia-", 8, testmap)
    except Exception:  # noqa: BLE001
        paginas = []
    for adres, tekst in paginas:
        res = parse_venezia_artikel(tekst)
        if not res or not res[2]:
            continue
        tegen, datum, fases = res
        for w in uit:
            if w["tegen"].lower() == tegen.lower() and str(w["aftrap"])[:10] == datum:
                w["fases"] = fases
                w["info"] = False
                w["noot"] = "Kaarten uit de voorverkoop zijn inclusief de waterbus naar Sant'Elena."
                w["bron"] = adres
    return uit


# ---------------------------------------------------------------- Parma
PA_KOP = re.compile(r"^\s*(SERIE A|COPPA ITALIA[^\n]*)\s*\n+\s*PARMA\s*[-–]\s*([^\n]+?)\s*\n\s*[A-Z]{3}\s+(\d{1,2})\s+([A-Z]{3})\s*[-–]\s*AT\s+(\d{1,2}):(\d{2})", re.M)
PA_FASE = re.compile(r"PHASE\s*(\d)\s*\|\s*[“\"]?([^\n]*?)\s+From\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s+on\s+\w+,\s+(\d{1,2})\s+([A-Za-z]+)", re.I)


def parse_parma(tekst, club="parma", bron=""):
    koppen = list(PA_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        mnd = t.MAANDEN_EN.get(m.group(4).lower())
        if not mnd:
            continue
        d = t.jaar_voor_dag(int(m.group(3)), mnd, int(m.group(5)), int(m.group(6)), t.NL, terug=20)
        if not d:
            continue
        aftrap = t.tekst_fmt(d)
        if not toekomst(aftrap):
            continue
        blok = tekst[m.end(): koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)]
        fases = []
        for f in PA_FASE.finditer(blok):
            naam = f.group(2).upper()
            if "GENERAL" in naam:
                groep, label = "vrij", "Vrije verkoop"
            elif "TARDINI CARD" in naam:
                groep, label = "clubkaart", "Tardini Card-houders (geen seizoenkaart)"
            else:
                continue
            h, mi = uur24(f.group(3), f.group(4), f.group(5))
            mm = maand_en(f.group(7))
            moment = fase_moment(f.group(6), mm, h, mi, d) if mm else None
            if moment:
                fases.append([groep, moment, label])
        tegen = t.mooie_naam(m.group(2))
        uit.append(wedstrijd(club, tegen, comp_it(m.group(1)), aftrap, fases=fases, nu=False, info=not fases,
                             noot="" if fases else NOOT_INFO, bron=bron))
    return uit


def haal_parma(pagina, test, sleutel="parma"):
    return parse_parma(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- aansluiting
CLUBS = [
    ("venezia", "Venezia FC", "IT", "Venezia (tickets)", "https://en.veneziafc.it/tickets/biglietteria", haal_venezia),
    ("parma", "Parma Calcio 1913", "IT", "Parma (tickets)", "https://www.parmacalcio1913.com/en/tickets/", haal_parma),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
