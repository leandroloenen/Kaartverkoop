"""Leesprogramma's voor PSV en Go Ahead Eagles.

- PSV: de Champions League-pagina (losse thuiswedstrijden) plus nieuwsartikelen over de losse verkoop (beker).
- Go Ahead Eagles: nieuwsartikelen 'Kaartverkoopinformatie Go Ahead Eagles - tegenstander' (alleen thuiswedstrijden).
Voor de Champions League-pagina geldt:

PSV zet per toernooi een informatiepagina online met de losse thuiswedstrijden. Er staan geen
verkoopdata op: alleen of de kaarten nu te koop zijn of uitverkocht. Elk seizoen heeft die pagina
een nieuw adres; zet het nieuwe adres in scripts/verken_lijst.txt achter 'PSV | '.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd


def _toekomst(aftrap):
    return datetime.fromisoformat(aftrap[:10]).date() >= datetime.now(t.NL).date()

PSV_BLOK = re.compile(
    r"^PSV\s*[–-]\s*([^|\n]+?)\s*\|\s*[a-z]+dag\s+(\d{1,2})\s+([a-z]+),?\s*(\d{1,2})[.:](\d{2})\s*uur\s*\n(.*?)(?=^PSV\s*[–-]\s|\Z)",
    re.I | re.S | re.M)


def parse_psv(tekst, club="psv", bron=""):
    uit, gezien = [], set()
    comp = "Champions League" if "CHAMPIONS LEAGUE" in tekst.upper() else "Europese wedstrijd"
    for m in PSV_BLOK.finditer(tekst):
        maand = t.MAANDEN_NL_LANG.get(m.group(3).lower())
        if not maand:
            continue
        aftrap = t.jaar_voor_dag(int(m.group(2)), maand, int(m.group(4)), int(m.group(5)))
        if not aftrap:
            continue
        tegen = m.group(1).strip()
        if (aftrap, tegen) in gezien:
            continue
        gezien.add((aftrap, tegen))
        blok = m.group(6)
        # alleen de regels bij deze wedstrijd, niet de kopjes eronder
        blok = re.split(r"\n\s*(?:TICKETALERT|BESTEL ONLINE|DIGITALE TOEGANG)", blok)[0]
        if re.search(r"uitverkocht", blok, re.I):
            wed = wedstrijd(club, tegen, comp, aftrap, noot="Uitverkocht.", bron=bron)
        else:
            wed = wedstrijd(club, tegen, comp, aftrap, nu=True, noot="Kaarten zijn nu te koop voor leden en Club Card-houders.", bron=bron)
        uit.append(wed)
    return uit


# ---- PSV: nieuwsartikelen over de losse verkoop
DAGEN = {"maandag": 0, "dinsdag": 1, "woensdag": 2, "donderdag": 3, "vrijdag": 4, "zaterdag": 5, "zondag": 6}
PSV_WEDSTRIJD = re.compile(r"PSV speelt op [a-z]+dag (\d{1,2}) ([a-z]+) om (\d{1,2})[.:](\d{2}) uur een thuiswedstrijd tegen ([^.\n]+?)\.\s*(?:De kaartverkoop voor (?:het duel|de wedstrijd) in (?:de )?([^\n]*?) verloopt)?", re.I)
PSV_DATUM = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
PSV_DAG = re.compile(r"(?:(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+)?(\d{1,2}) (januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)")
PSV_REL = re.compile(r"[Vv]anaf (vandaag|maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)")


def _psv_datum(zin, artikeldatum):
    """Eerste verkoopdatum in een zin: een datum, 'vandaag' of een weekdag na de publicatiedatum."""
    mm = PSV_DAG.search(zin)
    rel = PSV_REL.search(zin)
    if mm and (not rel or mm.start() < rel.start() + 30):
        maand = t.MAANDEN_NL_LANG[mm.group(2)]
        return datetime(artikeldatum.year, maand, int(mm.group(1))).date()
    if rel:
        w = rel.group(1)
        if w == "vandaag":
            return artikeldatum
        d = artikeldatum
        for _ in range(7):
            d = d.fromordinal(d.toordinal() + 1)
            if d.weekday() == DAGEN[w]:
                return d
    return None


def parse_psv_artikel(tekst, club="psv", bron=""):
    m = PSV_WEDSTRIJD.search(tekst)
    k = PSV_DATUM.search(tekst)
    if not m or not k:
        return None
    maand = t.MAANDEN_NL_LANG.get(m.group(2).lower())
    if not maand:
        return None
    artikeldatum = datetime(int(k.group(3)), int(k.group(2)), int(k.group(1))).date()
    aftrap = t.jaar_voor_dag(int(m.group(1)), maand, int(m.group(3)), int(m.group(4)))
    if not aftrap or not _toekomst(t.tekst_fmt(aftrap)):
        return None
    comp_tekst = (m.group(6) or "").upper()
    comp = "KNVB Beker" if "BEKER" in comp_tekst else ("Champions League" if "CHAMPIONS" in comp_tekst else ("Eredivisie" if not comp_tekst else m.group(6).strip()))
    fases = []
    for zin in re.split(r"(?<=\.)\s+", tekst[m.end():]):
        z = zin.lower()
        if "supportersvereniging" in z and "club card" in z:
            groep, label = "clubkaart", "Club Card-houders en supportersvereniging"
        elif "seizoen club card" in z:
            groep, label = "seizoen", "Seizoen Club Card-houders"
        elif "leden" in z and ("voorrang" in z or "vanaf" in z):
            groep, label = "lid", "Betalende leden"
        elif "vrije verkoop" in z:
            groep, label = "vrij", "Vrije verkoop"
        else:
            continue
        d = _psv_datum(zin, artikeldatum)
        if d and not any(f[0] == groep for f in fases):
            fases.append([groep, d.isoformat(), label])
    if not fases:
        return None
    return wedstrijd(club, m.group(5).strip(), comp, aftrap, fases=fases, bron=bron)


def haal_psv(pagina, test, sleutel="psv"):
    uit = parse_psv(t.haal_tekst(pagina, test), sleutel, pagina)
    testmap = os.environ.get("PSV_DETAIL_MAP", "")
    if test and not testmap:
        return uit
    try:
        for adres, tekst in t.haal_paginas("https://www.psv.nl/", r"media/artikel/[a-z0-9-]*(?:verkoop|kaart|ticket)", 6, testmap):
            w = parse_psv_artikel(tekst, sleutel, adres)
            if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
                uit.append(w)
    except Exception as e:  # noqa: BLE001
        print(f"PSV nieuwsartikelen overgeslagen: {e}")
    return uit


# ---------------------------------------------------------------- Go Ahead Eagles
GAE_WEDSTRIJD = re.compile(r"speelt op [a-z]+dag (\d{1,2}) ([a-z]+) om (\d{1,2})[.:](\d{2}) uur (?:de |het )?([^.\n]*?)tegen ([^.\n]+?)\.", re.I)
GAE_VANAF = re.compile(r"[Vv]anaf (?:[a-z]+dag )?(\d{1,2}) ([a-z]+)(?: om (\d{1,2})[.:](\d{2}) uur)?")


def parse_gae_artikel(tekst, club="gae", bron=""):
    m = GAE_WEDSTRIJD.search(tekst)
    if not m or "uit" in m.group(5).lower().replace("duit", ""):
        return None
    maand = t.MAANDEN_NL_LANG.get(m.group(2).lower())
    if not maand:
        return None
    aftrap = t.jaar_voor_dag(int(m.group(1)), maand, int(m.group(3)), int(m.group(4)))
    if not aftrap or not _toekomst(t.tekst_fmt(aftrap)):
        return None
    comp = "KNVB Beker" if "beker" in m.group(5).lower() else "Eredivisie"
    alinea = tekst[m.start():].split("Hieronder")[0]
    fases = []
    for v in GAE_VANAF.finditer(alinea):
        mv = t.MAANDEN_NL_LANG.get(v.group(2).lower())
        if not mv:
            continue
        d = t.jaar_voor_dag(int(v.group(1)), mv, int(v.group(3) or 0), int(v.group(4) or 0), terug=300)
        if not d:
            continue
        stuk = alinea[max(0, v.start() - 10):v.end() + 160].lower()
        if "clubkaarthouders" in stuk and "seizoenkaarthouders" in stuk:
            groep, label = "seizoen", "Seizoenkaart- en clubkaarthouders (extra kaarten)"
        else:
            groep, label = "vrij", "Start verkoop"
        fases.append([groep, t.tekst_fmt(d) if v.group(3) else d.strftime("%Y-%m-%d"), label])
        break
    noot = "Seizoenkaarthouders hebben gratis toegang tot hun eigen plaats." if "gratis toegang" in alinea.lower() else ""
    return wedstrijd(club, m.group(6).strip(), comp, aftrap, fases=fases, info=not fases, noot=noot, bron=bron)


def haal_gae(pagina, test, sleutel="gae"):
    testmap = os.environ.get("GAE_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"kaartverkoopinformatie-go-ahead-eagles-", 6, testmap):
        w = parse_gae_artikel(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
            uit.append(w)
    return uit


CLUBS = [
    ("psv", "PSV", "NL", "PSV", "https://www.psv.nl/ticketinfo/veelgestelde-vragen/informatie-league-phase-uefa-champions-league-2026-2027", haal_psv),
    ("gae", "Go Ahead Eagles", "NL", "Go Ahead Eagles", "https://www.ga-eagles.nl/category/eerste-selectie/", haal_gae),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
