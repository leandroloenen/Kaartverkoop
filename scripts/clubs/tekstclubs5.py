"""Leesprogramma's voor Everton, Nottingham Forest, AFC Bournemouth, Coventry City en Leeds United.

Alle vijf clubs publiceren de verkoopmomenten met datum en tijd, maar elk op een eigen manier:
- Everton: een tabel met het hele seizoen op een pagina (alleen datums).
- Forest, Bournemouth, Coventry en Leeds: een ticketartikel per thuiswedstrijd (of per twee wedstrijden bij Coventry).
Alle tijden zijn Engelse tijd; wij rekenen ze om naar Nederlandse tijd.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd

MAANDEN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
ORD = r"(?:st|nd|rd|th)?"
DAGEN = r"(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day"


def maand(woord):
    return MAANDEN.get(woord.strip().lower()[:3])


def uur(u, m, ap):
    h = int(u) % 12 + (12 if ap.lower() == "pm" else 0)
    return h, int(m or 0)


def moment(dag, mnd, h=0, mi=0, terug=250):
    """Engelse tijd -> tekst in Nederlandse tijd 'JJJJ-MM-DDTHH:MM'."""
    m = maand(mnd)
    if not m:
        return None
    d = t.jaar_voor_dag(int(dag), m, h, mi, t.LONDEN, terug=terug)
    return t.tekst_fmt(d) if d else None


def regels_van(tekst):
    return [r.strip() for r in tekst.splitlines() if r.strip()]


def toekomst(aftrap):
    d = datetime.fromisoformat(aftrap)
    return d.date() >= datetime.now(t.NL).date()


def mooi(naam):
    return t.mooie_naam(naam) if hasattr(t, "mooie_naam") else naam.title()


# ---------------------------------------------------------------- Everton
EV_DATUM = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
EV_DAG = re.compile(r"^" + DAGEN + r"\s+(\d{1,2})\s+([A-Za-z]+)\*?$")


def parse_everton(tekst, club="everton", bron=""):
    """Tabel 'On sale dates': per wedstrijd een datum voor de loting (Forever Blue+) en een verkoopvenster (Forever Blue)."""
    regels = regels_van(tekst)
    uit = []
    for i, r in enumerate(regels):
        m = EV_DATUM.match(r)
        if not m or i < 1 or i + 2 >= len(regels):
            continue
        a, b = EV_DAG.match(regels[i + 1]), EV_DAG.match(regels[i + 2])
        if not a or not b:
            continue
        aftrap = f"20{m.group(3)}-{m.group(2)}-{m.group(1)}"
        if not toekomst(aftrap):
            continue
        fases = []
        wd = datetime.fromisoformat(aftrap)
        for g, label in ((a, "Forever Blue+ leden: loting"), (b, "Forever Blue leden: verkoopvenster")):
            mnd = maand(g.group(2))
            if not mnd:
                continue
            jaar = wd.year if mnd <= wd.month else wd.year - 1
            fases.append(["lid", f"{jaar}-{mnd:02d}-{int(g.group(1)):02d}", label])
        uit.append(wedstrijd(club, regels[i - 1], "Premier League", aftrap, fases=fases, nu=False, info=False,
                             noot="De club noemt alleen de dagen, geen uren. Kaarten zijn er alleen voor leden.", bron=bron))
    return uit


def haal_everton(pagina, test, sleutel="everton"):
    return parse_everton(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- Nottingham Forest
FO_TITEL = re.compile(r"^(?:TICKET UPDATE|TICKET DETAILS)\s*\|\s*(.+?)\s*\(([HA])\)\s*$", re.I)
FO_AFTRAP = re.compile(r"\bon\s+" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)[^.]{0,40}?kick-off[^.]{0,40}?(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.S | re.I)
FO_RIJ_DAG = re.compile(r"^" + DAGEN + r"\s+(\d{1,2})\s+([A-Za-z]+)$")
FO_TIJD = re.compile(r"^(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)$", re.I)


def parse_forest_artikel(tekst, club="forest", bron=""):
    regels = regels_van(tekst)
    kop = next((FO_TITEL.match(r) for r in regels[:40] if FO_TITEL.match(r)), None)
    if not kop or kop.group(2).upper() != "H" or any(w in kop.group(1).upper() for w in ("WOMEN", "B TEAM", "U21", "U18", "U23", "UNDER", "ACADEMY", "PL2")):
        return None
    kop_tekst = " ".join(regels[:40]).upper()
    if "PREMIER LEAGUE 2" in kop_tekst or "UNDER-21" in kop_tekst or "UNDER 21" in kop_tekst:
        return None
    af = FO_AFTRAP.search(tekst)
    if not af:
        return None
    h, mi = uur(af.group(3), af.group(4), af.group(5))
    aftrap = moment(af.group(1), af.group(2), h, mi, terug=20)
    if not aftrap or not toekomst(aftrap):
        return None
    fases, gezien = [], set()
    in_tabel = False
    for r in tekst.splitlines():
        if r.strip().upper().startswith("TICKET SALE DATES"):
            in_tabel = True
            continue
        if r.strip().upper().startswith("FURTHER DATES"):
            break
        if not in_tabel:
            continue
        delen = [x.strip() for x in r.split("\t") if x.strip()]
        if len(delen) < 3:
            continue
        dag, tijd = FO_RIJ_DAG.match(delen[0]), FO_TIJD.match(delen[1])
        if not dag or not tijd:
            continue
        rest = " ".join(delen[2:])
        if len(delen) >= 4 and "member" in delen[3].lower() and "Applications" not in delen[3]:
            label = delen[3].replace(" | ", ", ").replace(" members", "-leden")
        elif "Ballot results" in rest:
            label = "Loting: uitslag en aankoopvenster opent"
        elif "Applications open" in rest:
            label = "Loting voor leden: aanvragen openen"
        elif "Second Sale" in rest:
            label = "Tweede verkoop (leden)"
        else:
            continue
        h2, m2 = uur(tijd.group(1), tijd.group(2), tijd.group(3))
        d = moment(dag.group(1), dag.group(2), h2, m2)
        if d and (label, d) not in gezien:
            gezien.add((label, d))
            fases.append(["lid", d, label])
    fases.sort(key=lambda f: f[1])
    tegen = mooi(kop.group(1))
    comp = "Premier League"
    for sleutel_c, naam_c in (("FA CUP", "FA Cup"), ("CARABAO", "EFL Cup"), ("LEAGUE CUP", "EFL Cup"), ("EUROPA LEAGUE", "Europa League"),
                              ("CONFERENCE LEAGUE", "Conference League"), ("CHAMPIONS LEAGUE", "Champions League"), ("FRIENDLY", "Vriendschappelijk")):
        if sleutel_c in kop_tekst or sleutel_c in tekst.upper()[:600]:
            comp = naam_c
            break
    return wedstrijd(club, tegen, comp, aftrap, fases=fases, nu=False, info=not fases,
                     noot="Kaarten zijn er alleen voor MyForest-leden. De hoogste lidmaatschappen kunnen als eerste kopen." if fases else "", bron=bron)


def haal_forest(pagina, test, sleutel="forest"):
    testmap = os.environ.get("FOREST_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/news/2026/[a-z]+/\d+/ticket-[a-z0-9-]+-h-/", 10, testmap):
        w = parse_forest_artikel(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- AFC Bournemouth
BO_TITEL = re.compile(r"^(?:TICKET & POINTS DROP INFORMATION|INFORMATION & POINTS DROP|TICKET INFORMATION)\s*:\s*(.+?)\s*\(([HA])\)\s*$", re.I)
BO_AFTRAP = re.compile(r"(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)\s+kick-off\s+on\s+" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)", re.I)
BO_RIJ = re.compile(r"^" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)\s*(?:\((?:Starting now,?\s*)?(?:(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm))?\))?$", re.I)


def parse_bournemouth_artikel(tekst, club="bournemouth", bron=""):
    regels = regels_van(tekst)
    kop = next((BO_TITEL.match(r) for r in regels[:40] if BO_TITEL.match(r)), None)
    if not kop or kop.group(2).upper() != "H":
        return None
    af = BO_AFTRAP.search(tekst)
    if not af:
        return None
    h, mi = uur(af.group(1), af.group(2), af.group(3))
    aftrap = moment(af.group(4), af.group(5), h, mi, terug=20)
    if not aftrap or not toekomst(aftrap):
        return None
    comp = "Premier League"
    for naam in ("Europa League", "Conference League", "Champions League"):
        if naam in tekst:
            comp = naam
            break
    algemeen = re.search(r"at\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)\s*:", tekst)
    basis = uur(*algemeen.groups()) if algemeen else (10, 0)
    fases = []
    for r in tekst.splitlines():
        delen = [x.strip() for x in re.split(r"\t+", r.strip()) if x.strip()]
        if len(delen) < 2:
            continue
        m = BO_RIJ.match(delen[0])
        if not m:
            continue
        detail = delen[1].rstrip("*^ ")
        if m.group(4):
            h2, m2 = uur(m.group(4), m.group(5), m.group(6))
        else:
            h2, m2 = basis
        d = moment(m.group(1), m.group(2), h2, m2)
        if not d:
            continue
        if "season ticket" in detail.lower():
            fases.append(["seizoen", d[:10] if not m.group(4) else d, "Seizoenkaarthouders (per wedstrijd)"])
        else:
            fases.append(["lid", d, "Leden met " + detail.replace("Home Points", "thuispunten").replace("Home Point", "thuispunt")])
    fases.sort(key=lambda f: f[1])
    return wedstrijd(club, mooi(kop.group(1)), comp, aftrap, fases=fases, nu=False, info=not fases,
                     noot="De verkoop gaat per niveau van thuispunten (loyaliteitspunten).", bron=bron)


def haal_bournemouth(pagina, test, sleutel="bournemouth"):
    testmap = os.environ.get("BOURNEMOUTH_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/news/2026/[a-z]+/\d+/[a-z0-9-]+-h-?/$", 10, testmap):
        w = parse_bournemouth_artikel(tekst, sleutel, adres)
        if w:
            uit.append(w)
    return uit


# ---------------------------------------------------------------- Coventry City
CO_WEDSTRIJD = re.compile(r"(?:^|\band\s)(.+?)\s+on\s+" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)\s*\((\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)\s*KO\)", re.I)
CO_RIJ = re.compile(r"^(.+?)\t+" + DAGEN + r"\s+(\d{1,2})\s+([A-Za-z]+),\s*(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)$", re.I)
CO_LABELS = (("sky blue members", "Sky Blues Members"), ("previous purchase history able", "Kopers van eerdere wedstrijden: tickets doorgeven aan nieuwe supporters"),
             ("previous purchase history", "Leden met eerdere aankoopgeschiedenis"))


def parse_coventry_artikel(tekst, club="coventry", bron=""):
    zin = next((r.strip() for r in tekst.splitlines() if " host " in r and "KO)" in r), "")
    if not zin:
        return []
    zin = zin.split(" host ", 1)[1]
    fases = []
    for r in tekst.splitlines():
        m = CO_RIJ.match(r.strip())
        if not m:
            continue
        label = next((l for k, l in CO_LABELS if k in m.group(1).lower()), None)
        if not label:
            continue
        h, mi = uur(m.group(4), m.group(5), m.group(6))
        d = moment(m.group(2), m.group(3), h, mi)
        if d:
            fases.append(["lid", d, label])
    fases.sort(key=lambda f: f[1])
    uit = []
    for m in CO_WEDSTRIJD.finditer(zin):
        h, mi = uur(m.group(4), m.group(5), m.group(6))
        aftrap = moment(m.group(2), m.group(3), h, mi, terug=20)
        if aftrap and toekomst(aftrap):
            uit.append(wedstrijd(club, mooi(m.group(1)), "Premier League", aftrap, fases=list(fases), nu=False, info=not fases,
                                 noot="Kaarten zijn er eerst alleen voor leden.", bron=bron))
    return uit


def haal_coventry(pagina, test, sleutel="coventry"):
    testmap = os.environ.get("COVENTRY_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/news/2026/[a-z]+/\d+/ticket-news", 6, testmap):
        uit += parse_coventry_artikel(tekst, sleutel, adres)
    return uit


# ---------------------------------------------------------------- Leeds United
LE_TEGEN = re.compile(r"fixture versus\s+(.+?)\.\s", re.I)
LE_DATUM = re.compile(r"take place on\s+" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)", re.I)
LE_AFTRAP = re.compile(r"Kick-off is scheduled for\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)
LE_FASE1 = re.compile(r"^" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)[,\s]+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)
LE_FASE_LOTING = re.compile(r"^" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)\s*-\s*Ballot opens at\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)


def parse_leeds_artikel(tekst, club="leeds", bron=""):
    if "our home" not in tekst.lower():
        return None
    tegen, datum, ko = LE_TEGEN.search(tekst), LE_DATUM.search(tekst), LE_AFTRAP.search(tekst)
    if not tegen or not datum:
        return None
    h, mi = uur(*ko.groups()) if ko else (0, 0)
    aftrap = moment(datum.group(1), datum.group(2), h, mi, terug=20)
    if not aftrap or not toekomst(aftrap):
        return None
    if not ko:
        aftrap = aftrap[:10]
    regels = regels_van(tekst)
    fases = []
    for i, r in enumerate(regels[:-1]):
        nxt = regels[i + 1]
        if r.upper().startswith("PHASE 1") and LE_FASE1.match(nxt):
            m = LE_FASE1.match(nxt)
            h2, m2 = uur(m.group(3), m.group(4), m.group(5))
            d = moment(m.group(1), m.group(2), h2, m2)
            label = "Fase 1: My Leeds Priority-leden (wie het eerst komt, het eerst)"
        elif r.upper().startswith("PHASE 2") and LE_FASE_LOTING.match(nxt):
            m = LE_FASE_LOTING.match(nxt)
            h2, m2 = uur(m.group(3), m.group(4), m.group(5))
            d = moment(m.group(1), m.group(2), h2, m2)
            label = "Fase 2: loting opent voor leden die vorig seizoen 11+ thuiswedstrijden kochten"
        elif r.upper().startswith("PHASE 3") and LE_FASE_LOTING.match(nxt):
            m = LE_FASE_LOTING.match(nxt)
            h2, m2 = uur(m.group(3), m.group(4), m.group(5))
            d = moment(m.group(1), m.group(2), h2, m2)
            label = "Fase 3: loting opent voor alle leden"
        else:
            continue
        if d:
            fases.append(["lid", d, label])
    comp = "Premier League" if "Premier League" in tekst else ("EFL Cup" if "EFL Cup" in tekst else "Premier League")
    return wedstrijd(club, mooi(tegen.group(1)), comp, aftrap, fases=fases, nu=False, info=not fases,
                     noot="Kaarten zijn er alleen voor leden (My Leeds). Seizoenkaarthouders hebben hun eigen plek.", bron=bron)


def haal_leeds(pagina, test, sleutel="leeds"):
    testmap = os.environ.get("LEEDS_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/en/news/ticket-information-", 10, testmap):
        w = parse_leeds_artikel(tekst, sleutel, adres)
        if w:
            uit.append(w)
    return uit


# ---------------------------------------------------------------- aansluiting
CLUBS = [
    ("everton", "Everton", "EN", "Everton (verkoopdata)", "https://www.evertonfc.com/tickets/on-sale-dates", haal_everton),
    ("forest", "Nottingham Forest", "EN", "Nottingham Forest", "https://www.nottinghamforest.co.uk/tickets/", haal_forest),
    ("bournemouth", "AFC Bournemouth", "EN", "AFC Bournemouth", "https://www.afcb.co.uk/tickets", haal_bournemouth),
    ("coventry", "Coventry City", "EN", "Coventry City", "https://www.ccfc.co.uk/tickets", haal_coventry),
    ("leeds", "Leeds United", "EN", "Leeds United", "https://www.leedsunited.com/en/news/category/ticketing", haal_leeds),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
