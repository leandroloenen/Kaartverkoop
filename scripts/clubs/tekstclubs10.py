"""Leesprogramma's voor Newcastle United, Brighton & Hove Albion en Ajax.
- Newcastle: pagina 'on sale dates' met per wedstrijd het loting- en verkoopmoment voor Mags Members (Londense tijd).
- Brighton: wedstrijdlijst (thuiswedstrijden); de verkoopinformatie staat in nieuwsberichten en is (nog) niet gelezen.
- Ajax: de Eredivisie- en Conference League-pagina met de status per thuiswedstrijd (meestal uitverkocht)."""
import os
import re
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs6 import MAANDEN_EN_LANG, aftrap_dt, toekomst

# ---------------------------------------------------------------- Newcastle
NC_KOP = re.compile(r"^Newcastle United vs ([^\n]+)\n([^/\n]+?)\s*/\s*[^\n]+\n\n\w+ (\d{1,2}) ([A-Za-z]+),\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*KO\s*\n(.*?)(?=^Newcastle United vs |\nOFFICIAL CLUB PARTNERS|\Z)", re.M | re.S)
NC_MOMENT = re.compile(r"^(Mags Member ballot open|Mags Member Sale open):\s*\w+ (\d{1,2})(?:st|nd|rd|th)? ([A-Za-z]+),\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|noon)", re.M)
NC_LABELS = {"mags member ballot open": "Mags Member-loting (inschrijving opent)", "mags member sale open": "Mags Member-verkoop"}
NOOT_MAGS = "Alleen voor Mags Members; seizoenkaarthouders kunnen kaarten doorsturen of wederverkopen."


def klok_en(u, m, ap):
    h = int(u)
    if ap == "noon":
        return 12, 0
    h = h % 12 + (12 if ap == "pm" else 0) if h <= 12 else h
    return h, int(m or 0)


def parse_newcastle(tekst, club="newcastle", bron=""):
    uit = []
    for k in NC_KOP.finditer(tekst):
        mnd = MAANDEN_EN_LANG.get(k.group(4).lower())
        if not mnd:
            continue
        h, mi = klok_en(k.group(5), k.group(6), k.group(7))
        d = t.jaar_voor_dag(int(k.group(3)), mnd, h, mi, t.LONDEN, terug=20)
        if not d:
            continue
        aftrap = t.tekst_fmt(d)
        if not toekomst(aftrap):
            continue
        fases = []
        for m in NC_MOMENT.finditer(k.group(8)):
            mm = MAANDEN_EN_LANG.get(m.group(3).lower())
            if not mm:
                continue
            hh, mi2 = klok_en(m.group(4), m.group(5), m.group(6))
            v = t.jaar_voor(int(m.group(2)), mm, hh, mi2, d, t.LONDEN)
            if v:
                fases.append(["lid", t.tekst_fmt(v), NC_LABELS[m.group(1).lower()]])
        fases.sort(key=lambda f: f[1])
        uit.append(wedstrijd(club, k.group(1).strip(), k.group(2).strip(), aftrap, fases=fases, nu=False, info=not fases,
                             noot=NOOT_MAGS, bron=bron))
    return uit


def haal_newcastle(pagina, test, sleutel="newcastle"):
    return parse_newcastle(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- Brighton
BR_MAAND = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})$", re.M)
BR_RIJ = re.compile(r"^\w+ (\d{1,2}) ([A-Za-z]{3})\n(\d{1,2}):(\d{2})\n(am|pm)\n(?:GMT|BST)\n[^\n]+\n(?:Watch On\n)?([^\n]+)\n([^\n]+)\nMATCH CENTRE", re.M)
BR_EUROPA = {"universitatea craiova", "monaco", "panathinaikos"}
NOOT_BRIGHTON = "Verkoopmomenten staan in een nieuwsbericht per wedstrijd en worden hier (nog) niet getoond."
BR_NAMEN = {"Spurs": "Tottenham Hotspur", "Forest": "Nottingham Forest", "Man Utd": "Manchester United", "Man City": "Manchester City",
            "Villa": "Aston Villa", "Palace": "Crystal Palace", "Newcastle": "Newcastle United"}


def parse_brighton(tekst, club="brighton", bron=""):
    uit, gezien = [], set()
    for m in BR_RIJ.finditer(tekst):
        if m.group(6).strip().lower() != "albion":
            continue
        mnd = t.MAANDEN_EN.get(m.group(2).lower())
        if not mnd:
            continue
        h, mi = klok_en(m.group(3), m.group(4), m.group(5))
        d = t.jaar_voor_dag(int(m.group(1)), mnd, h, mi, t.LONDEN, terug=20)
        if not d:
            continue
        aftrap = t.tekst_fmt(d)
        tegen = BR_NAMEN.get(m.group(7).strip(), m.group(7).strip())
        if (tegen, aftrap) in gezien or not toekomst(aftrap):
            continue
        gezien.add((tegen, aftrap))
        comp = "UEFA" if tegen.lower() in BR_EUROPA else "Premier League"
        uit.append(wedstrijd(club, tegen, comp, aftrap, nu=False, info=True, noot=NOOT_BRIGHTON, bron=bron))
    return uit


def haal_brighton(pagina, test, sleutel="brighton"):
    return parse_brighton(t.haal_tekst(pagina, test), sleutel, pagina)


# ---------------------------------------------------------------- Ajax
AJ_RIJ = re.compile(r"^Ajax - ([^\n]+)\n\n\w+ (\d{1,2}) ([a-z]+), (\d{1,2}):(\d{2}) uur\n\n(.*?)(?=^Ajax - |^Ticketshop\nMobile|^Nieuw: |^Mobile tickets\n\n|\Z)", re.M | re.S)
AJ_LOS = re.compile(r"(?:Losse kaartverkoop|Reguliere kaarten)\s*\t?\s*(🔴|🟢|🟠|🟡)?\s*([^\n]+)")
NOOT_UITVERKOCHT = "Losse kaarten zijn uitverkocht; via Resale komen soms kaarten vrij."
NOOT_CLUBCARD = " Voor deze wedstrijd is een Club Card verplicht."


def parse_ajax(tekst, club="ajax", comp="Eredivisie", bron=""):
    uit = []
    for k in AJ_RIJ.finditer(tekst):
        mnd = t.MAANDEN_NL_LANG.get(k.group(3).lower())
        if not mnd:
            continue
        d = t.jaar_voor_dag(int(k.group(2)), mnd, int(k.group(4)), int(k.group(5)), t.NL, terug=20)
        if not d:
            continue
        aftrap = t.tekst_fmt(d)
        if not toekomst(aftrap):
            continue
        blok = k.group(6)
        los = AJ_LOS.search(blok)
        status = los.group(2).strip().lower() if los else ""
        club_card = "club card-verplichting" in blok.lower()
        if "uitverkocht" in status:
            noot, nu, info = NOOT_UITVERKOCHT, False, True
        elif status.startswith(("open", "beschikbaar")):
            noot, nu, info = "Losse kaarten zijn nu te koop.", True, False
        else:
            noot, nu, info = "Verkoopmomenten niet getoond.", False, True
        if club_card:
            noot += NOOT_CLUBCARD
        uit.append(wedstrijd(club, k.group(1).strip(), comp, aftrap, nu=nu, info=info, noot=noot, bron=bron))
    return uit


# ---- Ajax: verkoopberichten in de nieuwsarchief (lopende tekst, per bericht anders opgebouwd)
AJ_DAG = re.compile(r"(?:(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+)?(\d{1,2})\s+(januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)\b", re.I)
AJ_TIJD = re.compile(r"(\d{1,2}):(\d{2})")
AJ_GROEPEN = [("seizoenkaarthouders", "seizoen", "Seizoenkaarthouders"), ("supportersvereniging", "lid", "Leden Supportersvereniging"),
              ("club card", "clubkaart", "Club Card-houders"), ("geverifieerd account", "vrij", "Vrije verkoop (geverifieerd account)")]
AJ_STOP = re.compile(r"^(F-Side|Mindervalid\w*|Mobile tickets|Kaartverkoop uitwedstrijd|Gerelateerde artikelen)\s*$", re.M)
AJ_ZIN = re.compile(r"(?<=[.!?])\s+|\n+")
AJ_KLEIN = {"fc", "sc", "afc", "sv", "vfb", "ac", "as", "us", "ssc", "bk", "fk", "de", "den", "van"}


def ajax_fases_uit_artikel(tekst, aftrap_nl):
    """Geeft (fases, reden). fases is None als het bericht niet betrouwbaar te lezen is."""
    kop = AJ_STOP.search(tekst)
    start = tekst.find("Kaarten vanaf")
    if start < 0:
        start = tekst.find("Verkoopschema")
    if start < 0:
        return None, "geen verkoopschema in tekst"
    deel = tekst[start:kop.start() if kop and kop.start() > start else len(tekst)]
    huidige_dag = None
    fases = []
    for zin in AJ_ZIN.split(deel):
        laag = zin.lower()
        groepen = [g for g in AJ_GROEPEN if g[0] in laag]
        if "mindervalid" in laag:
            continue
        dag = AJ_DAG.search(zin)
        if dag:
            mnd = t.MAANDEN_NL_LANG.get(dag.group(2).lower())
            huidige_dag = (int(dag.group(1)), mnd) if mnd else huidige_dag
        tijden = AJ_TIJD.findall(zin)
        if not groepen or not tijden:
            continue
        if len(groepen) > 1 or len(tijden) > 1:
            return None, "meerdere groepen of tijden in een zin"
        if not huidige_dag:
            return None, "tijd zonder datum"
        h, mi = int(tijden[0][0]), int(tijden[0][1])
        moment = t.jaar_voor(huidige_dag[0], huidige_dag[1], h, mi, aftrap_nl, t.NL)
        if not moment:
            return None, "verkoopmoment valt na de aftrap"
        fases.append([groepen[0][1], t.tekst_fmt(moment), groepen[0][2]])
    if len(fases) < 2 or not any(f[0] == "vrij" for f in fases):
        return None, "verkoopschema onvolledig (geen vrije verkoop gevonden)"
    if [f[1] for f in fases] != sorted(f[1] for f in fases):
        return None, "volgorde van verkoopmomenten klopt niet"
    return fases, ""


def ajax_wedstrijd_bij(tekst, wedstrijden):
    """De enige toekomstige thuiswedstrijd waarvan de tegenstander in de aanhef van het bericht staat."""
    aanhef = tekst[:900].lower()
    gevonden = []
    for w in wedstrijden:
        woorden = [x for x in re.split(r"[^\w]+", w["tegen"].lower()) if x and x not in AJ_KLEIN]
        if woorden and all(x in aanhef for x in woorden):
            gevonden.append(w)
    return gevonden[0] if len(gevonden) == 1 else None


def haal_ajax(pagina, test, sleutel="ajax"):
    uit = parse_ajax(t.haal_tekst(pagina, test), sleutel, "Eredivisie", pagina)
    eur = t.adres_uit_lijst("Ajax (Conference League)", "https://www.ajax.nl/fans/conference-league/")
    try:
        tekst = t.haal_tekst(eur, os.environ.get("AJAX_EUROPA_TEKST_BESTAND", ""))
        uit += parse_ajax(tekst, sleutel, "Conference League", eur)
    except Exception:  # noqa: BLE001
        pass
    # verkoopberichten: de archiefpagina toont de nieuwste berichten; eerdere fases blijven door update.py bewaard
    testmap = os.environ.get("AJAX_ARTIKEL_MAP", "")
    try:
        artikelen = t.haal_paginas("https://www.ajax.nl/artikelen", r"/artikelen/informatie-(over-)?(losse-)?kaartverkoop", 6, testmap)
    except Exception:  # noqa: BLE001
        artikelen = []
    for adres, tekst in artikelen:
        w = ajax_wedstrijd_bij(tekst, uit)
        if not w:
            print(f"    let op (ajax): kaartverkoopbericht niet aan één wedstrijd te koppelen, overgeslagen: {adres}")
            continue
        fases, reden = ajax_fases_uit_artikel(tekst, aftrap_dt(w["aftrap"]))
        if not fases:
            print(f"    let op (ajax): kaartverkoopbericht niet betrouwbaar gelezen ({reden}): {adres}")
            continue
        w["fases"] = fases
        w["info"] = False
        w["bron"] = adres
    return uit


CLUBS = [
    ("newcastle", "Newcastle United", "EN", "Newcastle (verkoopdata)", "https://www.newcastleunited.com/en/tickets/ticket-information/on-sale-dates", haal_newcastle),
    ("brighton", "Brighton & Hove Albion", "EN", "Brighton (wedstrijden)", "https://www.brightonandhovealbion.com/fixtures-first-team-men", haal_brighton),
    ("ajax", "AFC Ajax", "NL", "Ajax (Eredivisie)", "https://www.ajax.nl/fans/kaartverkoop-eredivisie/", haal_ajax),
]


def _maak(sleutel, naam_, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam_, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
