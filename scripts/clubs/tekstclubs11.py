"""Leesprogramma's voor VfL Wolfsburg en FC St. Pauli (beide 2. Bundesliga).

- Wolfsburg: een Wölfeshop-pagina per thuiswedstrijd met een blok VERKAUFSSTART (datum, tijd en doelgroep).
- St. Pauli: een lijst 'Nächste Begegnungen' met per wedstrijd een regel over de verkoop.
Duitse tijden zijn gelijk aan Nederlandse tijden.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd


def _toekomst(aftrap):
    return datetime.fromisoformat(aftrap).date() >= datetime.now(t.NL).date()


def _naam(tekst):
    return t.mooie_naam(tekst.strip())


# ---------------------------------------------------------------- VfL Wolfsburg
WO_KOP = re.compile(r"^VFL WOLFSBURG VS\.?\s*(.*)$", re.I)
WO_DATUM = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*/\s*(\d{1,2})\.(\d{2})\s*Uhr")
WO_VERKOOP = re.compile(r"^[A-Za-zäöü]{2}\.?,?\s*(\d{2})\.(\d{2})\.(\d{4})\s+ab\s+(\d{1,2})\.(\d{2})\s*Uhr\s*-\s*(.+)$")


def parse_wolfsburg(tekst, club="wolfsburg", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    if "Männer" not in regels:
        return None
    kop = next((i for i, r in enumerate(regels) if WO_KOP.match(r)), None)
    if kop is None:
        return None
    rest = WO_KOP.match(regels[kop]).group(1)
    if not rest:  # tegenstander staat op de volgende regel
        rest = regels[kop + 1]
        kop += 1
    comp_regel = regels[kop + 1] if kop + 1 < len(regels) else ""
    comp = comp_regel.split(" - ")[0].strip()
    if "Frauen" in comp_regel or not comp:
        return None
    dm = next((WO_DATUM.search(r) for r in regels[kop + 1:kop + 5] if WO_DATUM.search(r)), None)
    if not dm:
        return None
    aftrap = f"{dm.group(3)}-{dm.group(2)}-{dm.group(1)}T{int(dm.group(4)):02d}:{dm.group(5)}"
    if not _toekomst(aftrap):
        return None
    fases = []
    in_blok = False
    vrij_onzeker = False
    for r in regels:
        if r.upper().startswith("VERKAUFSSTART"):
            in_blok = True
            continue
        if in_blok and r.upper().startswith(("INKLUSIONSTICKETS", "GÄSTETICKETS", "TICKETBEREITSTELLUNG")):
            break
        if in_blok and "freien Verkauf geben wird" in r:
            vrij_onzeker = True
        m = WO_VERKOOP.match(r) if in_blok else None
        if not m:
            continue
        d = f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{int(m.group(4)):02d}:{m.group(5)}"
        wie = m.group(6).lower()
        if "freier verkauf" in wie:
            fases.append(["vrij", d, "Vrije verkoop"])
        elif "dauerkarten" in wie and "mitglied" in wie:
            fases.append(["lid", d, "Seizoenkaarthouders en leden"])
        elif "dauerkarten" in wie:
            fases.append(["seizoen", d, "Seizoenkaarthouders"])
        elif "mitglied" in wie:
            fases.append(["lid", d, "Leden"])
        else:
            fases.append(["lid", d, "Voorverkoop (beperkt)"])
    noten = []
    if any(f[2] in ("Seizoenkaarthouders en leden", "Leden") for f in fases):
        noten.append("Alleen leden die al vóór 1 juli lid waren, mogen kopen.")
    if vrij_onzeker:
        noten.append("Of er vrije verkoop komt, is nog niet bekend.")
    return wedstrijd(club, _naam(rest), comp, aftrap, fases=fases, nu=False, info=not fases, noot=" ".join(noten), bron=bron)


def haal_wolfsburg(pagina, test, sleutel="wolfsburg"):
    testmap = os.environ.get("WOLFSBURG_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/vfl-wolfsburg-vs\.-[^/]+/GD\d+", 14, testmap):
        w = parse_wolfsburg(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- FC St. Pauli
SP_BLOK = re.compile(
    r"\d+\.\s*Spieltag\s*\n+\s*(?:[A-Za-z]{2},\s*(\d{2})\.(\d{2})\.(\d{4})\s*\|\s*(\d{2}):(\d{2})|Noch nicht fix terminiert\s*\((\d{2})\.(\d{2})\.(\d{4})\))"
    r"\s*\n+(?:[^\n]*\n+)??\s*ST\. PAULI\s*\n+\s*\\\s*\n+\s*([^\n]+)\n(.*?)(?=\n\s*\d+\.\s*Spieltag|Zum Spielplan|\Z)", re.S)
SP_LID = re.compile(r"Mitgliedervorverkauf:\s*[A-Za-zäöü]+\s*\((\d{1,2})\.(\d{1,2})\.,?\s*(\d{1,2})(?::(\d{2}))?\s*Uhr\)")
SP_AB = re.compile(r"Tickets ab (\d{2})\.(\d{2})\.(\d{2})")


def parse_stpauli(tekst, club="stpauli", bron=""):
    i = tekst.find("Nächste Begegnungen")
    if i < 0:
        return []
    uit = []
    for m in SP_BLOK.finditer(tekst[i:]):
        if m.group(1):
            aftrap = f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}:{m.group(5)}"
        else:
            aftrap = f"{m.group(8)}-{m.group(7)}-{m.group(6)}"
        if not _toekomst(aftrap[:10]):
            continue
        rest = m.group(10)
        tegen = _naam(m.group(9))
        comp = "DFB-Pokal" if "Pokal" in rest else "2. Bundesliga"
        fases = []
        lid = SP_LID.search(rest)
        if lid:
            jaar = aftrap[:4]
            fases.append(["lid", f"{jaar}-{int(lid.group(2)):02d}-{int(lid.group(1)):02d}T{int(lid.group(3)):02d}:{lid.group(4) or '00'}", "Ledenvoorverkoop"])
        ab = SP_AB.search(rest)
        if ab and not lid:  # alleen als de club geen ledenvoorverkoop noemt
            fases.append(["vrij", f"20{ab.group(3)}-{ab.group(2)}-{ab.group(1)}", "Verkoop start (volgens de club)"])
        nu = False
        noot = ""
        if "Ausverkauft" in rest:
            noot = "Uitverkocht."
        elif "verfügbar" in rest or "erhältlich" in rest:
            nu = True
        uit.append(wedstrijd(club, tegen, comp, aftrap, fases=fases, nu=nu, info=not fases and not nu and not noot, noot=noot, bron=bron))
    return uit


def haal_stpauli(pagina, test, sleutel="stpauli"):
    return parse_stpauli(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- aansluiting
CLUBS = [
    ("wolfsburg", "VfL Wolfsburg", "DE", "VfL Wolfsburg", "https://shop.vfl-wolfsburg.de/tickets/maenner/", haal_wolfsburg),
    ("stpauli", "FC St. Pauli", "DE", "FC St. Pauli", "https://www.fcstpauli.com/fu%C3%9Fball/tickets/heimspiele", haal_stpauli),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
