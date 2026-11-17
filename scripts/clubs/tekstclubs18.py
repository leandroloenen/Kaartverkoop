"""Verkoopfases uit artikelen voor ADO Den Haag, Sparta en Brighton (aanvulling op de wedstrijden uit de shop of de wedstrijdlijst).

- ADO: een ticketinfo-pagina per thuiswedstrijd, met een tabel 'Verkoopperiode voor / Start' (Nederlandse tijd).
- Sparta: een bericht per thuiswedstrijd ('Supporters met een SCC kunnen vanaf woensdag 21 oktober, 11:00 uur ...').
- Brighton: een bericht per twee thuiswedstrijden met alleen datums ('On sale dates:'), zonder tijd.
"""
import os
import re

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs12 import _jaar_voor_fase
from .tekstclubs5 import DAGEN, ORD, maand, moment, toekomst, uur

NL_DAG = r"(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)"
NL_MND = "|".join(t.MAANDEN_NL_LANG)


def _fase_nl(dag, mnd, uurtje, minuut, aftrap):
    m = t.MAANDEN_NL_LANG.get(mnd.lower())
    if not m:
        return None
    j = _jaar_voor_fase(int(dag), m, aftrap)
    kern = f"{j:04d}-{m:02d}-{int(dag):02d}"
    return kern + (f"T{int(uurtje):02d}:{minuut}" if uurtje is not None else "")


# ---------------------------------------------------------------- ADO Den Haag
ADO_KOP = re.compile(r"^ADO DEN HAAG\s*-\s*(.+?)\s*\nDatum:\s*\n\s*(\d{1,2})\s+(" + NL_MND + r")\s+(\d{4})\s*\nTijd:\s*\n\s*(\d{1,2}):(\d{2})", re.M | re.I)
ADO_RIJ = re.compile(r"^(.+?)\t\s*" + NL_DAG + r"\s+(\d{1,2})\s+(" + NL_MND + r"),?\s*(\d{1,2})[:.](\d{2})\s*uur", re.M | re.I)


def parse_ado_ticketinfo(tekst, club="ado", bron=""):
    k = ADO_KOP.search(tekst)
    if not k:
        return None
    mnd = t.MAANDEN_NL_LANG.get(k.group(3).lower())
    aftrap = f"{int(k.group(4)):04d}-{mnd:02d}-{int(k.group(2)):02d}T{int(k.group(5)):02d}:{k.group(6)}"
    if not toekomst(aftrap):
        return None
    fases = []
    for r in ADO_RIJ.finditer(tekst):
        wie = r.group(1).lower()
        d = _fase_nl(r.group(2), r.group(3), r.group(4), r.group(5), aftrap)
        if not d:
            continue
        if "ado den haag+" in wie or "club card" in wie:
            fases.append(["clubkaart", d, "ADO Den Haag+ en ADO Den Haag Kids" if "kids" in wie else "ADO Den Haag+"])
        elif "regulier" in wie or "vrije" in wie:
            fases.append(["vrij", d, "Reguliere kaartverkoop"])
    if not fases:
        return None
    noot = ""
    if re.search(r"uitsluitend aankopen als je in bezit bent van ADO Den Haag\+", tekst):
        noot = "In de eerste week kun je alleen kopen met ADO Den Haag+."
    return wedstrijd(club, k.group(1).strip().title().replace("Fc ", "FC "), "Eredivisie", aftrap, fases=fases, nu=False, info=False, noot=noot, bron=bron)


def haal_ado_artikelen():
    testmap = os.environ.get("ADO_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas("https://adodenhaag.nl/nl/tickets/kaartverkoop", r"/ticketinfo/\d+-ado-den-haag-[a-z0-9-]+$", 10, testmap):
        w = parse_ado_ticketinfo(tekst, "ado", adres)
        if w:
            uit.append(w)
    return uit


# ---------------------------------------------------------------- Sparta
SP_KOP = re.compile(r"^Sparta Rotterdam\s+[–-]\s+(.+?)\s*\n[^\n]*\n\s*" + NL_DAG + r"\s+(\d{1,2})\s+(" + NL_MND + r"),\s*(\d{1,2})[:.](\d{2})\s*uur", re.M | re.I)
SP_ZIN = re.compile(r"^(.+?)\s+kunnen\s+vanaf\s+" + NL_DAG + r"\s+(\d{1,2})\s+(" + NL_MND + r"),\s*(\d{1,2})[:.](\d{2})\s*uur(?:\s+maximaal\s+(\d+)\s+tickets)?", re.M | re.I)


def parse_sparta_artikel(tekst, club="sparta", bron=""):
    k = SP_KOP.search(tekst)
    if not k:
        return None
    aftrap = _fase_nl(k.group(2), k.group(3), int(k.group(4)), k.group(5), "9999-12-31")
    # het jaar van de wedstrijd: het komende jaar waarin de datum nog niet voorbij is
    m = t.MAANDEN_NL_LANG[k.group(3).lower()]
    d = t.jaar_voor_dag(int(k.group(2)), m, int(k.group(4)), int(k.group(5)), t.NL, terug=20)
    if not d:
        return None
    aftrap = t.tekst_fmt(d)
    if not toekomst(aftrap):
        return None
    fases, aantal = [], ""
    for z in SP_ZIN.finditer(tekst):
        wie = z.group(1).lower()
        f = _fase_nl(z.group(2), z.group(3), z.group(4), z.group(5), aftrap)
        if not f:
            continue
        if z.group(6):
            aantal = z.group(6)
        if re.search(r"\bscc\b", wie):
            fases.append(["seizoen", f, "Seizoenclubkaarthouders (SCC)"])
        elif re.search(r"\bcc\b", wie):
            fases.append(["clubkaart", f, "Clubkaarthouders (CC)"])
        elif re.search(r"iedereen|overige|alle supporters|vrije", wie):
            fases.append(["vrij", f, "Vrije verkoop"])
    if not fases:
        return None
    return wedstrijd(club, k.group(1).strip(), "Eredivisie", aftrap, fases=fases, nu=False, info=False,
                     noot=(f"Max. {aantal} tickets per persoon." if aantal else ""), bron=bron)


def haal_sparta_artikelen():
    testmap = os.environ.get("SPARTA_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas("https://www.sparta-rotterdam.nl/clubliefde/ticketinformatie/", r"/ticketinformatie-26-27-sparta-rotterdam-[a-z0-9-]+/?$", 10, testmap):
        w = parse_sparta_artikel(tekst, "sparta", adres)
        if w:
            uit.append(w)
    return uit


# ---------------------------------------------------------------- Brighton
BR_A = re.compile(r"We host\s+(.+?)\s+at the Amex on\s+" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+),\s*kick-off\s*(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)
BR_B = re.compile(r"On\s+" + DAGEN + r"\s+(\d{1,2})" + ORD + r"\s+([A-Za-z]+)\s+we host\s+(.+?)\s+at the Amex,\s*(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)\s+kick-off", re.I)
BR_RIJ = re.compile(r"^(.+?)\s*:\s*" + DAGEN + r"\s+(\d{1,2})" + ORD + r"?\s+([A-Za-z]+)(?:\s+at\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm))?\s*$", re.M | re.I)
BR_NAMEN = {"Spurs": "Tottenham Hotspur", "Forest": "Nottingham Forest", "Man Utd": "Manchester United", "Man City": "Manchester City",
            "Villa": "Aston Villa", "Palace": "Crystal Palace", "Newcastle": "Newcastle United"}


def parse_brighton_artikel(tekst, club="brighton", bron=""):
    kopjes = []
    for m in BR_A.finditer(tekst):
        kopjes.append((m.start(), m.end(), m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
    for m in BR_B.finditer(tekst):
        kopjes.append((m.start(), m.end(), m.group(3), m.group(1), m.group(2), m.group(4), m.group(5), m.group(6)))
    kopjes.sort()
    uit = []
    for n, (begin, eind, tegen, dag, mnd, h0, mi0, ap) in enumerate(kopjes):
        h, mi = uur(h0, mi0, ap)
        aftrap = moment(dag, mnd, h, mi, terug=20)
        if not aftrap or not toekomst(aftrap):
            continue
        blok = tekst[eind:kopjes[n + 1][0] if n + 1 < len(kopjes) else len(tekst)]
        fases = []
        for r in BR_RIJ.finditer(blok):
            wie = r.group(1).lower()
            mm = maand(r.group(3))
            if not mm:
                continue
            j = _jaar_voor_fase(int(r.group(2)), mm, aftrap)
            f = f"{j:04d}-{mm:02d}-{int(r.group(2)):02d}"
            if r.group(4):
                hh, mmi = uur(r.group(4), r.group(5), r.group(6))
                f += f"T{hh:02d}:{mmi:02d}"
            if "sth" in wie or "season" in wie:
                fases.append(["seizoen", f, "Seizoenkaarthouders, 1901 Club-leden en gasten van MyAlbion+-leden"])
            elif "baller" in wie or "little albion" in wie:
                fases.append(["kids", f, "MyAlbion Baller en Little Albion"])
            elif "myalbion+" in wie:
                fases.append(["lid", f, "MyAlbion+-leden"])
            elif "general" in wie:
                fases.append(["vrij", f, "Vrije verkoop"])
        if fases:
            tg = tegen.strip()
            uit.append(wedstrijd(club, BR_NAMEN.get(tg, tg), "Premier League", aftrap, fases=sorted(fases, key=lambda f: f[1]), nu=False, info=False, noot="", bron=bron))
    return uit


def haal_brighton_artikelen():
    testmap = os.environ.get("BRIGHTON_DETAIL_MAP", "")
    uit, gezien = [], set()
    for start in ("https://www.brightonandhovealbion.com/latest-news-men", "https://www.brightonandhovealbion.com/media-article/tickets-on-sale-for-brentford-and-newcastle-at-the-amex"):
        for adres, tekst in t.haal_paginas(start, r"/media-article/tickets-on-sale-[a-z0-9-]+$", 8, testmap):
            if adres in gezien:
                continue
            gezien.add(adres)
            uit.extend(parse_brighton_artikel(tekst, "brighton", adres))
        if testmap:
            break
    return uit
