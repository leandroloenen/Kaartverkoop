"""Leesprogramma's voor Hamburger SV, Schalke 04 en Borussia Mönchengladbach.

- HSV: een tabel met alle wedstrijden en per wedstrijd de voorverkoop en vrije verkoop (soms met datum en tijd).
- Schalke: de wedstrijdlijst in de ticketshop (vivenu) met beschikbaarheid; de verkoopdata zelf staan daar niet.
- Gladbach: een nieuwsartikel per wedstrijd met de data voor de voorverkoop en de vrije verkoop.
Duitse tijden zijn gelijk aan Nederlandse tijden.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd


def _toekomst(aftrap):
    return datetime.fromisoformat(aftrap[:10]).date() >= datetime.now(t.NL).date()


def _jaar_voor_fase(dag, maand, aftrap_datum):
    """Het jaar waarin een verkoopmoment valt: hoogstens op de wedstrijddag zelf."""
    jaar = int(aftrap_datum[:4])
    if datetime(jaar, maand, dag).date() > datetime.fromisoformat(aftrap_datum[:10]).date():
        jaar -= 1
    return jaar


# ---------------------------------------------------------------- Hamburger SV
HSV_DAG = re.compile(r"^(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,\s*(\d{2})\.(\d{2})\.(\d{2})$")
HSV_TIJD = re.compile(r"^kickoff:\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.", re.I)
HSV_BEGIN = re.compile(r"^(\d{2})\.(\d{2})\.\s*-$")
HSV_EIND = re.compile(r"^-?\s*(\d{2})\.(\d{2})\.(\d{2})$")
HSV_LID = re.compile(r"Members presale:\s*(\d{1,2})\.(\d{1,2})\.\s*(?:starting|staring)\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.", re.I)
HSV_VRIJ = re.compile(r"General sale:\s*(\d{1,2})\.(\d{1,2})\.\s*(?:starting|staring)\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.", re.I)
NAMEN = {"BVB": "Borussia Dortmund", "SV Werder Bremen": "Werder Bremen"}
HSV_VREEMD = ("Split",)  # tegenstanders die duidelijk geen competitiewedstrijd zijn


def _uur12(u, m, ap):
    return int(u) % 12 + (12 if ap.lower() == "p" else 0), int(m)


def parse_hsv(tekst, club="hsv", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    i = 0
    n = len(regels)
    while i < n:
        datum = tijd = None
        weekend = False
        if HSV_DAG.match(regels[i]) and i + 1 < n and HSV_TIJD.match(regels[i + 1]):
            m = HSV_DAG.match(regels[i])
            k = HSV_TIJD.match(regels[i + 1])
            h, mi = _uur12(k.group(1), k.group(2), k.group(3))
            datum = f"20{m.group(3)}-{m.group(2)}-{m.group(1)}"
            tijd = f"{h:02d}:{mi:02d}"
            i += 2
        elif HSV_BEGIN.match(regels[i]) and i + 1 < n and HSV_EIND.match(regels[i + 1]):
            b = HSV_BEGIN.match(regels[i])
            e = HSV_EIND.match(regels[i + 1])
            datum = f"20{e.group(3)}-{b.group(2)}-{b.group(1)}"  # eerste dag van het speelweekend
            einde = f"{e.group(1)}-{e.group(2)}"
            weekend = True
            i += 2
        else:
            i += 1
            continue
        if i + 2 >= n or regels[i + 1] != "-":
            continue
        thuis, tegen = regels[i], regels[i + 2]
        i += 3
        verkoop = []
        while i < n and not (HSV_DAG.match(regels[i]) or HSV_BEGIN.match(regels[i])) and not regels[i].upper().startswith("CLICK HERE"):
            verkoop.append(regels[i])
            i += 1
        if thuis.strip().upper() != "HSV" or not _toekomst(datum):
            continue
        aftrap = f"{datum}T{tijd}" if tijd else datum
        fases, nu, noot, info = [], False, "", False
        for r in verkoop:
            lid, vrij = HSV_LID.search(r), HSV_VRIJ.search(r)
            if lid:
                h, mi = _uur12(lid.group(3), lid.group(4), lid.group(5))
                j = _jaar_voor_fase(int(lid.group(1)), int(lid.group(2)), datum)
                fases.append(["lid", f"{j}-{int(lid.group(2)):02d}-{int(lid.group(1)):02d}T{h:02d}:{mi:02d}", "Ledenvoorverkoop"])
            elif vrij:
                h, mi = _uur12(vrij.group(3), vrij.group(4), vrij.group(5))
                j = _jaar_voor_fase(int(vrij.group(1)), int(vrij.group(2)), datum)
                fases.append(["vrij", f"{j}-{int(vrij.group(2)):02d}-{int(vrij.group(1)):02d}T{h:02d}:{mi:02d}", "Vrije verkoop"])
            elif r.lower().startswith("members presale: book here"):
                nu = True
                noot = "De ledenvoorverkoop is nu open."
            elif r.lower().startswith("general sale: book here"):
                nu = True
                noot = "Vrije verkoop is nu open."
            elif "sold out" in r.lower():
                noot = "Uitverkocht."
            elif r.strip().upper() == "TBA":
                info = True
        if weekend:
            noot = noot or "Dag en tijd van de wedstrijd zijn nog niet bekend; dit is de eerste dag van het speelweekend."
        tegen = NAMEN.get(tegen, tegen)
        uit.append(wedstrijd(club, tegen, "Friendly" if any(x in tegen for x in HSV_VREEMD) else "Bundesliga", aftrap,
                             fases=fases, nu=nu, info=info and not fases and not nu, noot=noot, bron=bron))
    return uit


def haal_hsv(pagina, test, sleutel="hsv"):
    return parse_hsv(t.haal_tekst(pagina, test, locale="en-GB"), sleutel, pagina)


# ---------------------------------------------------------------- Schalke 04
SC_BLOK = re.compile(r"FC Schalke 04 - ([^\n]+)\n([A-Za-z]+) (\d{1,2})(?:, (\d{4}))? (\d{1,2}):(\d{2})\s*([AP]M)\nLocation:\n[^\n]+\n((?:€[^\n]*\n)?(?:[A-Z][A-Z ]+\n)?)")


def parse_schalke(tekst, club="schalke", bron=""):
    tekst = tekst.replace("\xa0", " ").replace("\u202f", " ")
    uit, gezien = [], set()
    for m in SC_BLOK.finditer(tekst):
        mnd = t.MAANDEN_EN.get(m.group(2).lower()[:3])
        if not mnd:
            continue
        h = int(m.group(5)) % 12 + (12 if m.group(7) == "PM" else 0)
        mi = int(m.group(6))
        if m.group(4):
            d = datetime(int(m.group(4)), mnd, int(m.group(3)), h, mi)
        else:
            d = t.jaar_voor_dag(int(m.group(3)), mnd, h, mi, t.NL, terug=20)
            if not d:
                continue
        aftrap = t.tekst_fmt(d)
        tegen = t.mooie_naam(m.group(1)) if m.group(1).isupper() else m.group(1).strip()
        if not _toekomst(aftrap) or (tegen, aftrap) in gezien:
            continue
        gezien.add((tegen, aftrap))
        status = m.group(8).upper()
        nu = "AVAILABLE" in status
        noot = "Uitverkocht." if "SOLD OUT" in status and "ALMOST" not in status else ""
        if nu:
            noot = "Tickets beschikbaar in de ticketshop; mogelijk eerst alleen voor leden."
        info = not nu and not noot
        if info:
            noot = "Volgens de club start eerst een voorverkoop voor leden; de datum volgt."
        uit.append(wedstrijd(club, tegen, "Bundesliga", aftrap, fases=[], nu=nu, info=info, noot=noot, bron=bron))
    return uit


def haal_schalke(pagina, test, sleutel="schalke"):
    return parse_schalke(t.haal_tekst(pagina, test, locale="en-GB"), sleutel, pagina)


# ---------------------------------------------------------------- Borussia Mönchengladbach
GL_TEGEN = re.compile(r"Am\s+\w+,\s*(\d{1,2})\.\s*([A-Za-zäöü]+)\s*\((\d{1,2}):(\d{2})\s*Uhr\)\s+empfängt\s+die\s+FohlenElf\s+(?:den\s+|die\s+|das\s+)?(.+?)(?:\s+zum\s+|\s+im\s+|\s+in\s+der\s+|\s+zur\s+|\.\s)")
GL_LID = re.compile(r"Ab\s+\w+,\s*(\d{1,2})\.\s*([A-Za-zäöü]+),?\s*um\s*(\d{1,2}):(\d{2})\s*Uhr,\s*können\s+sich\s+([^.]+?)(?:\s+im\s+Online|\.)")
GL_VRIJ = re.compile(r"freie\s+Vorverkauf\s+startet\s+am\s+\w+,\s*(\d{1,2})\.\s*([A-Za-zäöü]+)\s+um\s+(\d{1,2}):(\d{2})\s*Uhr")


def _maand_de(woord):
    return t.MAANDEN_DE_LANG.get(woord.lower())


def parse_gladbach_artikel(tekst, club="gladbach", bron=""):
    m = GL_TEGEN.search(tekst)
    if not m:
        return None
    mnd = _maand_de(m.group(2))
    if not mnd:
        return None
    d = t.jaar_voor_dag(int(m.group(1)), mnd, int(m.group(3)), int(m.group(4)), t.NL, terug=20)
    if not d:
        return None
    aftrap = t.tekst_fmt(d)
    if not _toekomst(aftrap):
        return None
    comp = "DFB-Pokal" if "Pokal" in tekst[:1500] else "Bundesliga"
    fases = []
    lid = GL_LID.search(tekst)
    if lid and _maand_de(lid.group(2)):
        j = _jaar_voor_fase(int(lid.group(1)), _maand_de(lid.group(2)), aftrap)
        fases.append(["lid", f"{j}-{_maand_de(lid.group(2)):02d}-{int(lid.group(1)):02d}T{int(lid.group(3)):02d}:{lid.group(4)}", "Leden, seizoenkaarthouders en fanclubs"])
    vrij = GL_VRIJ.search(tekst)
    if vrij and _maand_de(vrij.group(2)):
        j = _jaar_voor_fase(int(vrij.group(1)), _maand_de(vrij.group(2)), aftrap)
        fases.append(["vrij", f"{j}-{_maand_de(vrij.group(2)):02d}-{int(vrij.group(1)):02d}T{int(vrij.group(3)):02d}:{vrij.group(4)}", "Vrije verkoop"])
    return wedstrijd(club, t.mooie_naam(m.group(5)) if m.group(5).isupper() else m.group(5).strip(), comp, aftrap, fases=fases, nu=False,
                     info=not fases, noot="", bron=bron)


def haal_gladbach(pagina, test, sleutel="gladbach"):
    testmap = os.environ.get("GLADBACH_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/news/[a-z0-9-]*ticket", 12, testmap):
        w = parse_gladbach_artikel(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- aansluiting
CLUBS = [
    ("hsv", "Hamburger SV", "DE", "Hamburger SV", "https://www.hsv.de/en/tickets/infos", haal_hsv),
    ("schalke", "Schalke 04", "DE", "Schalke 04", "https://tickets.schalke04.de/p/heimspiele", haal_schalke),
    ("gladbach", "Borussia Mönchengladbach", "DE", "Borussia Mönchengladbach", "https://www.borussia.de/news", haal_gladbach),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
