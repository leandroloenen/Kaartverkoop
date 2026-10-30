"""Verzamelaar voor Brentford: leest 'On-sale dates' (per wedstrijd de voorverkoop per groep, in Britse tijd)."""
import os
import re
from datetime import datetime

from . import tekst as t

CLUB = "brentford"
NAAM = "Brentford"
LAND = "EN"
PAGINA = "https://www.brentfordfc.com/en/ticket-information"
TEST = os.environ.get("BRENTFORD_TEKST_BESTAND", "")
MATCHDATUM = re.compile(r"^(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2})\s+([A-Z]{3})\s+'(\d{2})$")
MOMENT = re.compile(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+([A-Za-z]{3}),\s*(\d{1,2}):(\d{2})$")
TIJD = re.compile(r"^(\d{1,2}):(\d{2})$")


def groep_van(regel):
    laag = regel.lower()
    if "season ticket" in laag or "premium seat" in laag:
        return "seizoen"
    if "member" in laag:
        return "lid"
    return "vrij"


def parse(tekst):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    if "ON-SALE DATES" in regels:
        regels = regels[regels.index("ON-SALE DATES") + 1:]
    uit, i = [], 0
    while i < len(regels) - 2:
        if regels[i + 1] not in ("HOME", "AWAY"):
            i += 1
            continue
        tegen, thuis = t.mooie_naam(regels[i]), regels[i + 1] == "HOME"
        j = i + 2
        blok = []
        while j < len(regels) and regels[j] != "FIND OUT MORE":
            blok.append(regels[j])
            j += 1
        status = regels[j + 1] if j + 1 < len(regels) else ""
        i = j + 1
        if not thuis:
            continue
        md = next((MATCHDATUM.match(r) for r in blok if MATCHDATUM.match(r)), None)
        tijd = next((TIJD.match(r) for r in blok if TIJD.match(r)), None)
        if not md or not tijd:
            continue
        aftrap = t.naar_nl(datetime(2000 + int(md.group(3)), t.MAANDEN_EN[md.group(2).lower()], int(md.group(1)),
                                    int(tijd.group(1)), int(tijd.group(2))), t.LONDEN)
        comp = next((r.title() for r in blok if "LEAGUE" in r or "CUP" in r), "Premier League")
        fases, groeptekst = [], None
        for r in blok:
            m = MOMENT.match(r)
            if m and groeptekst:
                d = t.jaar_voor(int(m.group(1)), t.MAANDEN_EN[m.group(2).lower()], int(m.group(3)), int(m.group(4)), aftrap, t.LONDEN)
                if d:
                    fases.append([groep_van(groeptekst), t.tekst_fmt(d), groeptekst.capitalize()])
            elif not (MATCHDATUM.match(r) or TIJD.match(r) or r.startswith("CATEGORY") or r in ("HOME", "AWAY") or r.upper() == comp.upper()):
                groeptekst = r
        uit.append({"club": CLUB, "tegen": tegen, "comp": comp, "aftrap": t.tekst_fmt(aftrap),
                    "fases": sorted(fases, key=lambda f: f[1]), "nu": status == "BUY NOW", "info": False,
                    "noot": "Tijden in Nederlandse tijd (omgerekend uit Brits)." if fases else "", "bron": PAGINA})
    return uit


def haal_op():
    return parse(t.haal_tekst(PAGINA, TEST))
