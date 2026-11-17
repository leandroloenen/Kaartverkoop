"""Verkoopfases uit clubberichten voor ACF Fiorentina en Udinese (Engelstalige berichten per thuiswedstrijd).

- Fiorentina: 'Info biglietti Fiorentina vs X' en de ticketpagina per wedstrijd met 'Phase 1: InViola Premium Card', 'Phase 2: General sale', 'Phase 3: Matchday'.
- Udinese: bericht per wedstrijd met 'Phase 1' (leden van het 1896 Membership Programme) en 'Phase 2' (vrije verkoop).
Italiaanse tijden zijn gelijk aan Nederlandse tijden.
"""
import os
import re
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs12 import _jaar_voor_fase
from .tekstclubs14 import EN_MAAND, _toekomst

MND = "|".join(m.capitalize() for m in EN_MAAND)
DAG = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
# '10:00 on Tuesday, November 17, 2026' / '10:00 AM, 17 November 2026' / '16:00 on Friday 16 October'
TIJD = r"(\d{1,2})[:.](\d{2})\s*(AM|PM)?"
DATUM_A = r"(?:" + DAG + r",?\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(" + MND + r")(?:,?\s+(\d{4}))?"
DATUM_B = r"(?:" + DAG + r",?\s+)?(" + MND + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?"
MOMENT_1 = re.compile(TIJD + r"[,\s]*(?:on\s+)?" + DATUM_A, re.I)   # tijd eerst, dag-maand
MOMENT_2 = re.compile(TIJD + r"[,\s]*(?:on\s+)?" + DATUM_B, re.I)   # tijd eerst, maand-dag
MOMENT_3 = re.compile(DATUM_A + r"[,\s]+(?:kick-?off\s*)?(?:at\s+)?" + TIJD, re.I)   # dag-maand eerst
MOMENT_4 = re.compile(DATUM_B + r"[,\s]+(?:kick-?off\s*)?(?:at\s+)?" + TIJD, re.I)   # maand-dag eerst


def _moment_in(blok, aftrap):
    """Eerste 'tijd + datum' in de tekst als 'YYYY-MM-DDTHH:MM' (jaar via aftrap als het ontbreekt)."""
    kand = []
    for m in MOMENT_1.finditer(blok):
        kand.append((m.start(), m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
    for m in MOMENT_2.finditer(blok):
        kand.append((m.start(), m.group(1), m.group(2), m.group(3), m.group(5), m.group(4), m.group(6)))
    for m in MOMENT_3.finditer(blok):
        kand.append((m.start(), m.group(4), m.group(5), m.group(6), m.group(1), m.group(2), m.group(3)))
    if not kand:
        return None
    _, h, mi, ap, dag, mnd, jaar = sorted(kand)[0]
    h = int(h)
    if ap and ap.upper() == "PM" and h < 12:
        h += 12
    if ap and ap.upper() == "AM" and h == 12:
        h = 0
    m = EN_MAAND[mnd.lower()]
    j = int(jaar) if jaar else _jaar_voor_fase(int(dag), m, aftrap)
    return f"{j:04d}-{m:02d}-{int(dag):02d}T{h:02d}:{mi}"


def _aftrap(tekst, tegen_kop):
    """Aftrap uit 'Monday 7 December 2026, 20:45' of 'Monday, December 7, 2026 ... 20:45' vlak bij de kop met de wedstrijd."""
    start = tegen_kop.end()
    stuk = tekst[start:start + 600]
    fase = re.search(r"Phase\s*\d", stuk, re.I)
    if fase:
        stuk = stuk[:fase.start()]
    kand = []
    for patroon in (MOMENT_3, MOMENT_4):
        m = patroon.search(stuk)
        if m:
            kand.append((m.start(), patroon, m))
    for _, patroon, m in sorted(kand, key=lambda x: x[0])[:1]:
        if True:
            if patroon is MOMENT_3:
                d, mnd, jr, h, mi = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            else:
                mnd, d, jr, h, mi = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            mm = EN_MAAND[mnd.lower()]
            if jr:
                return f"{int(jr):04d}-{mm:02d}-{int(d):02d}T{int(h):02d}:{mi}"
            dt = t.jaar_voor_dag(int(d), mm, int(h), int(mi))
            return t.tekst_fmt(dt) if dt else None
    return None


def _blokken(tekst, kop_regex):
    delen = list(re.finditer(kop_regex, tekst, re.I))
    for n, m in enumerate(delen):
        yield m, tekst[m.end():delen[n + 1].start() if n + 1 < len(delen) else len(tekst)]


# ---------------------------------------------------------------- Fiorentina
FI_KOP = re.compile(r"Fiorentina\s+(?:vs\.?|v|-)\s+([A-Z][A-Za-z.' ]+?)\s*(?:,|\n|Serie A|\(|Coppa)", re.I)
FI_FASE = r"Phase\s*(\d)\s*[:\-–]?\s*([^\n]*)"


def parse_fiorentina(tekst, club="acf-fiorentina", bron=""):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    k = FI_KOP.search(tekst)
    if not k:
        return None
    aftrap = _aftrap(tekst, k)
    if not aftrap or not _toekomst(aftrap):
        return None
    fases = []
    for m, blok in _blokken(tekst, FI_FASE):
        titel = m.group(2).lower()
        blok = blok[:700]
        start = _moment_in(blok, aftrap)
        if not start:
            continue
        if "inviola" in titel or "premium" in titel:
            fases.append(["clubkaart", start, "InViola Premium Card-houders"])
        elif "general" in titel or "public" in titel:
            fases.append(["vrij", start, "Vrije verkoop"])
        elif "matchday" in titel:
            fases.append(["vrij", start, "Wedstrijddag (tarief op de dag zelf)"])
    if not fases:
        return None
    comp = "Coppa Italia" if re.search(r"coppa italia", tekst[:1500], re.I) else "Serie A"
    return wedstrijd(club, k.group(1).strip().title(), comp, aftrap, fases=sorted(fases, key=lambda f: f[1]), bron=bron)


def haal_fiorentina(pagina, test, sleutel="acf-fiorentina"):
    testmap = os.environ.get("FIORENTINA_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/en/news/info-biglietti-fiorentina-vs-[a-z0-9-]+$|/en/ticketing/[0-9a-f]{8}-[0-9a-f]{4}-", 10, testmap):
        w = parse_fiorentina(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- Udinese
UD_KOP = re.compile(r"Udinese\s+(?:v|vs\.?|-)\s+([A-Z][A-Za-z.' ]+?)\s+(?:at|,|\n|Bluenergy)", re.I)
UD_FASE = r"Phase\s*(\d)\s*[:\-–]?\s*([^\n]*)"


def parse_udinese(tekst, club="udinese-calcio", bron=""):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    k = UD_KOP.search(tekst)
    if not k:
        return None
    aftrap = _aftrap(tekst, k)
    if not aftrap or not _toekomst(aftrap):
        return None
    fases = []
    for m, blok in _blokken(tekst, UD_FASE):
        blok = blok[:600]
        start = _moment_in(blok, aftrap)
        if not start:
            continue
        laag = (m.group(2) + " " + blok).lower()
        if "member" in laag or "1896" in laag:
            fases.append(["lid", start, "Leden (1896 Membership Programme)"])
        elif "general" in laag or "public" in laag:
            fases.append(["vrij", start, "Vrije verkoop"])
    if not fases:
        return None
    return wedstrijd(club, k.group(1).strip(), "Serie A", aftrap, fases=sorted(fases, key=lambda f: f[1]), bron=bron)


def haal_udinese(pagina, test, sleutel="udinese-calcio"):
    testmap = os.environ.get("UDINESE_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"viewSection\?id=\d+", 10, testmap):
        w = parse_udinese(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
            uit.append(w)
    return uit


CLUBS = [
    ("acf-fiorentina", "ACF Fiorentina", "IT", "Fiorentina (artikelen)", "https://www.acffiorentina.com/en/news", haal_fiorentina),
    ("udinese-calcio", "Udinese Calcio", "IT", "Udinese (artikelen)", "https://www.udinese.it/Apps/WebObjects/Udinese.woa/wa/viewSection?id=93200&lang=eng", haal_udinese),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper().replace('-', '_')}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
