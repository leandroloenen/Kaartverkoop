"""Willem II: nieuwsartikelen 'Kaartverkoop ...' met de verkoopmomenten (fases per doelgroep).

De wedstrijden zelf komen uit de ticketshop; deze artikelen vullen daar de verkoopfases bij aan (zie aanvullen.py).
"""
import os
import re

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs12 import _jaar_voor_fase

WII_WEDSTRIJD = re.compile(r"Op [a-z]+dag (\d{1,2}) (januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)(?: om (\d{1,2})[.:](\d{2}) uur)?[^.]*?\bWillem II\b[^.]*?\bop tegen ([A-Z][^.]+?)\.", re.S)
WII_PUBLICATIE = re.compile(r"Gepubliceerd op\s*(\d{2})-(\d{2})-(\d{4})")
WII_MOMENT = re.compile(r"^(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+(\d{1,2})\s+([a-z]+),?\s+(\d{1,2})[.:](\d{2})\s+uur:\s*(.+)$", re.I)
WII_TERUGKOOP = re.compile(r"vanaf vandaag.*?eigen plaats terugkopen|eigen plaats terugkopen.*?vanaf vandaag", re.I | re.S)


def parse_willem2_artikel(tekst, club="willem2", bron=""):
    m = WII_WEDSTRIJD.search(tekst)
    if not m:
        return None
    maand = t.MAANDEN_NL_LANG[m.group(2)]
    dag = int(m.group(1))
    p = WII_PUBLICATIE.search(tekst)
    jaar = int(p.group(3)) if p else t.datetime.now(t.NL).year
    aftrap = f"{jaar:04d}-{maand:02d}-{dag:02d}"
    if maand < int(p.group(2)) if p else False:
        aftrap = f"{jaar + 1:04d}-{maand:02d}-{dag:02d}"
    fases = []
    if p and WII_TERUGKOOP.search(tekst):
        fases.append(["seizoen", f"{jaar:04d}-{int(p.group(2)):02d}-{int(p.group(1)):02d}", "Seizoenkaarthouders: eigen plaats terugkopen"])
    for regel in tekst.splitlines():
        r = WII_MOMENT.match(regel.strip())
        if not r:
            continue
        mnd = t.MAANDEN_NL_LANG.get(r.group(2).lower())
        if not mnd:
            continue
        j = _jaar_voor_fase(int(r.group(1)), mnd, aftrap)
        moment = f"{j:04d}-{mnd:02d}-{int(r.group(1)):02d}T{int(r.group(3)):02d}:{r.group(4)}"
        z = r.group(5).lower()
        if "vrije verkoop" in z:
            fases.append(["vrij", moment, "Vrije verkoop"])
        elif "seizoenkaarthouders" in z:
            fases.append(["seizoen", moment, "Seizoenkaarthouders (extra kaarten)"])
        elif "clubkaarthouders" in z:
            fases.append(["clubkaart", moment, "Clubkaarthouders en WII Kings-leden" if "kings" in z else "Clubkaarthouders"])
    if not fases:
        return None
    comp = "KNVB Beker" if "knvb beker" in tekst.lower() else "Eredivisie"
    return wedstrijd(club, m.group(5).strip(), comp, aftrap, fases=fases, bron=bron)


def haal_willem2_artikelen():
    testmap = os.environ.get("WILLEM2_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas("https://www.willem-ii.nl/", r"/artikel/kaartverkoop", 8, testmap):
        w = parse_willem2_artikel(tekst, "willem2", adres)
        if w:
            uit.append(w)
    return uit
