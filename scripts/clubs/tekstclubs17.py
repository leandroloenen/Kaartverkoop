"""Premier League: Aston Villa, Hull City, Sunderland, Ipswich Town en Crystal Palace.

Villa, Hull, Sunderland en Ipswich publiceren een nieuwsbericht per thuiswedstrijd (die verdwijnen na een paar dagen van de
nieuwsoverzichtspagina, daarom bewaart update.py de wedstrijden van deze clubs: BEHOUD). Palace heeft een tabel met het hele seizoen.
Alle tijden zijn Engelse tijd; wij rekenen ze om naar Nederlandse tijd.
"""
import os
import re
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs12 import _jaar_voor_fase
from .tekstclubs5 import DAGEN, ORD, maand, moment, regels_van, toekomst, uur

DAG3 = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
KOP = re.compile(DAG3 + r"[A-Za-z]*\s+(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{1,2}):(\d{2})\s+(.+?)\s+(HOME|AWAY)\b", re.S | re.I)
TIJD_AM = re.compile(r"(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)
MD = r"(\d{1,2})" + ORD + r"?\s+([A-Za-z]+)"


def _comp(tekst, kop="", bron=""):
    k = (kop + " " + tekst[:1200]).lower() + (" ucl" if re.search(r"[-/]ucl\b", bron) else "")
    for sleutel_c, naam_c in (("champions league", "Champions League"), ("europa league", "Europa League"), ("conference league", "Conference League"),
                              ("fa cup", "FA Cup"), ("carabao", "EFL Cup"), ("efl cup", "EFL Cup"), ("league cup", "EFL Cup"), (" ucl", "Champions League")):
        if sleutel_c in k:
            return naam_c
    return "Premier League"


def _kop(tekst):
    m = KOP.search(tekst)
    if not m or m.group(6).upper() != "HOME":
        return None
    aftrap = moment(m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), terug=20)
    if not aftrap or not toekomst(aftrap):
        return None
    return aftrap, " ".join(m.group(5).split()).title()


# ---------------------------------------------------------------- Aston Villa
VI_RIJ = re.compile(r"^" + DAGEN + r",?\s+([A-Za-z]+)\s+(\d{1,2})\t(.+)$", re.M)


def parse_villa_artikel(tekst, club="aston-villa", bron=""):
    kop = _kop(tekst)
    if not kop:
        return None
    aftrap, tegen = kop
    tm = TIJD_AM.search(tekst[tekst.upper().find("ON-SALE DATES"):]) if "ON-SALE DATES" in tekst.upper() else None
    h, mi = (uur(tm.group(1), tm.group(2), tm.group(3)) if tm else (9, 30))
    fases = []
    for r in VI_RIJ.finditer(tekst):
        wie = r.group(3).lower()
        d = moment(r.group(2), r.group(1), h, mi)
        if not d:
            continue
        if "general sale" in wie:
            fases.append(["vrij", d, "Vrije verkoop"])
        elif "season ticket" in wie:
            fases.append(["seizoen", d, "Seizoenkaarthouders"])
        elif "junior" in wie and "member" in wie:
            fases.append(["lid", d, "Leden (volwassenen en junioren)"])
        elif "member" in wie:
            fases.append(["lid", d, "Leden"])
    if not fases:
        return None
    return wedstrijd(club, tegen, _comp(tekst, tegen, bron), aftrap, fases=fases, nu=False, info=False,
                     noot="Eerst alleen voor leden; de club verwacht dat de kaarten voor leden snel uitverkocht zijn.", bron=bron)


def haal_villa(pagina, test, sleutel="aston-villa"):
    return _uit_artikelen(sleutel, parse_villa_artikel, "VILLA", [pagina, "https://www.avfc.co.uk/news/2026/november/06/ticketing-crystal-palace-home-ticket-details-26-27/"],
                          r"/news/\d{4}/[a-z]+/\d+/ticketing-(?![a-z0-9-]*away)[a-z0-9-]*ticket-details")


# ---------------------------------------------------------------- Hull City
HU_VERKOOP = re.compile(r"on sale from\s+" + DAGEN + r"\s+" + MD + r"\s+at\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)


def parse_hull_artikel(tekst, club="hull-city", bron=""):
    kop = _kop(tekst)
    if not kop:
        return None
    aftrap, tegen = kop
    fases = []
    for m in HU_VERKOOP.finditer(tekst):
        h, mi = uur(m.group(3), m.group(4), m.group(5))
        d = moment(m.group(1), m.group(2), h, mi)
        if d:
            n = re.search(r"maximum of (\w+) tickets?", tekst, re.I)
            aantal = {"one": 1, "two": 2, "three": 3, "four": 4}.get(n.group(1).lower(), n.group(1)) if n else ""
            fases.append(["lid", d, "Leden en supporters met aankoopgeschiedenis" + (f" (max. {aantal} tickets)" if aantal else "")])
    if not fases:
        return None
    return wedstrijd(club, tegen, _comp(tekst, tegen, bron), aftrap, fases=fases, nu=False, info=False,
                     noot="Kaarten zijn er alleen voor leden en voor supporters die dit of vorig seizoen een Hull-kaartje kochten.", bron=bron)


def haal_hull(pagina, test, sleutel="hull-city"):
    return _uit_artikelen(sleutel, parse_hull_artikel, "HULL", [pagina, "https://www.wearehullcity.co.uk/news/2026/november/02/ticket-details-totthenham-hotspur-h-26-27/"],
                          r"/news/\d{4}/[a-z]+/\d+/ticket-(?:details|update)-[a-z0-9-]*-h(?:-[a-z0-9-]*)?/?$")


# ---------------------------------------------------------------- Sunderland
SU_KOP = re.compile(r"^(.+?)\s+v\s+(.+?)\s+\(([HA])\)\s*$")
SU_INFO = re.compile(r"^" + DAGEN + r",?\s+" + MD + r",\s*(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)[^,]*,\s*[^,]+,\s*(.+?)\.?$", re.I)
SU_RIJ = re.compile(r"^" + DAGEN + r",?\s+" + MD + r",\s*(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm|p)\b", re.I)


def parse_sunderland_artikel(tekst, club="sunderland", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit, i = [], 0
    huidig = None
    while i < len(regels):
        r = regels[i]
        k = SU_KOP.match(r)
        if k:
            if huidig and huidig["fases"]:
                uit.append(huidig)
            huidig = None
            if k.group(3) == "H" and k.group(1).strip().lower() == "sunderland" and i + 1 < len(regels):
                inf = SU_INFO.match(regels[i + 1])
                if inf:
                    h, mi = uur(inf.group(3), inf.group(4), inf.group(5))
                    aftrap = moment(inf.group(1), inf.group(2), h, mi, terug=20)
                    if aftrap and toekomst(aftrap):
                        huidig = {"tegen": k.group(2).strip(), "aftrap": aftrap, "comp": _comp("", inf.group(6)), "fases": []}
                i += 2
                continue
        if huidig is not None:
            m = SU_RIJ.match(r)
            if m and i + 2 < len(regels) and not SU_KOP.match(regels[i + 1]):
                ap = "pm" if m.group(5).lower() == "p" else m.group(5)
                h, mi = uur(m.group(3), m.group(4), ap)
                d = moment(m.group(1), m.group(2), h, mi)
                wat, wie = regels[i + 1].lower(), regels[i + 2].lower()
                if d:
                    if "general sale" in wat:
                        huidig["fases"].append(["vrij", d, "Vrije verkoop"])
                    elif "ballot opens" in wat:
                        huidig["fases"].append(["lid", d, "Loting voor leden: aanvragen openen"])
                    elif "seat selection opens" in wat:
                        huidig["fases"].append(["lid", d, "Loting: uitslag en aankoopvenster opent"])
                    elif "seat reservation opens" in wat:
                        huidig["fases"].append(["seizoen", d, "Seizoenkaarthouders: plaatsen reserveren"])
                i += 3
                continue
        i += 1
    if huidig and huidig["fases"]:
        uit.append(huidig)
    return [wedstrijd(club, w["tegen"], w["comp"], w["aftrap"], fases=_uniek(w["fases"]), nu=False, info=False,
                      noot="Kaarten zijn er eerst alleen voor leden (loting).", bron=bron) for w in uit]


def haal_sunderland(pagina, test, sleutel="sunderland"):
    uit = []
    for adres, tekst in _paginas(pagina, [pagina, "https://www.safc.com/news/2026/november/02/ticketing-in-november-key-dates/"], "SUNDERLAND",
                                 r"/news/\d{4}/[a-z]+/\d+/(?:ticketing-[a-z0-9-]*|[a-z0-9-]*key-dates)/?$"):
        for w in parse_sunderland_artikel(tekst, sleutel, adres):
            if not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
                uit.append(w)
    return uit


# ---------------------------------------------------------------- Ipswich Town
IP_KOP = re.compile(r"^TICKET DETAILS\s*\|\s*(.+?)\s*\(H\)\s*$", re.I | re.M)
IP_AFTRAP = re.compile(r"\bH\s+(\d{1,2}):(\d{2})\s+" + DAG3 + r"\s+(\d{1,2})\s+([A-Za-z]{3})", re.S)
IP_BALLOT = re.compile(r"ballot[^.]{0,120}?open from\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)\s+on\s+" + DAGEN + r",?\s+" + MD, re.I)
IP_SUCCES = re.compile(r"ballot[^.]{0,200}?commence from\s+" + DAGEN + r",?\s+" + MD, re.I | re.S)
IP_ALGEMEEN = re.compile(r"from\s+" + DAGEN + r",?\s+" + MD + r",?\s+at\s+(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)", re.I)


def parse_ipswich_artikel(tekst, club="ipswich-town", bron=""):
    k = IP_KOP.search(tekst)
    a = IP_AFTRAP.search(tekst)
    if not k or not a:
        return None
    aftrap = moment(a.group(3), a.group(4), int(a.group(1)), int(a.group(2)), terug=20)
    if not aftrap or not toekomst(aftrap):
        return None
    fases = []
    b = IP_BALLOT.search(tekst)
    if b:
        h, mi = uur(b.group(1), b.group(2), b.group(3))
        d = moment(b.group(4), b.group(5), h, mi)
        if d:
            fases.append(["lid", d, "Loting voor leden: aanvragen openen"])
    s = IP_SUCCES.search(tekst)
    if s:
        d = moment(s.group(1), s.group(2))
        if d:
            fases.append(["lid", d[:10], "Loting: uitslag en aankoopvenster opent"])
    g = IP_ALGEMEEN.search(tekst)
    if g:
        h, mi = uur(g.group(3), g.group(4), g.group(5))
        d = moment(g.group(1), g.group(2), h, mi)
        if d:
            fases.append(["lid", d, "Tweede verkoop (leden)"])
    if not fases:
        return None
    return wedstrijd(club, k.group(1).strip().title(), _comp(tekst), aftrap, fases=_uniek(fases), nu=False, info=False,
                     noot="Kaarten zijn er alleen voor leden. Eerst is er een loting.", bron=bron)


def haal_ipswich(pagina, test, sleutel="ipswich-town"):
    return _uit_artikelen(sleutel, parse_ipswich_artikel, "IPSWICH", [pagina],
                          r"/news/\d{4}/[a-z]+/\d+/[a-z0-9-]*ticket-details[a-z0-9-]*/?$")


# ---------------------------------------------------------------- Crystal Palace
PA_RIJ = re.compile(r"^(.+?)\t(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)\t([A-C])\t(\d+)\t(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)\t(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)\t(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)\t(\d+)\s*$", re.M)


def parse_palace(tekst, club="crystal-palace", bron=""):
    deel = tekst.split("TICKET RESALE", 1)[0]
    uit = []
    for m in PA_RIJ.finditer(deel):
        mnd = maand(m.group(3))
        if not mnd:
            continue
        d = t.jaar_voor_dag(int(m.group(2)), mnd, 0, 0, t.NL, terug=20)
        if not d:
            continue
        aftrap = d.strftime("%Y-%m-%d")
        if not toekomst(aftrap):
            continue
        fases = []
        for (dag, mn), groep, label in (((m.group(6), m.group(7)), "lid", "Gold-leden en Season Ticket+-houders (voorrang)"),
                                        ((m.group(8), m.group(9)), "lid", "Overige leden en seizoenkaarthouders"),
                                        ((m.group(10), m.group(11)), "lid", "Gasttickets voor leden en seizoenkaarthouders")):
            mm = maand(mn)
            if mm:
                j = _jaar_voor_fase(int(dag), mm, aftrap)
                fases.append([groep, f"{j:04d}-{mm:02d}-{int(dag):02d}", label])
        uit.append(wedstrijd(club, m.group(1).strip(), "Premier League", aftrap, fases=fases, nu=False, info=False,
                             noot="Voor alle kaarten is een lidmaatschap of seizoenkaart nodig. De aftraptijd is nog niet bekend.", bron=bron))
    return uit


def haal_palace(pagina, test, sleutel="crystal-palace"):
    tekst = t.haal_tekst(pagina, test, "en-GB")
    return parse_palace(tekst, sleutel, pagina)


# ---------------------------------------------------------------- gedeelde hulpjes
def _uniek(fases):
    gezien, uit = set(), []
    for f in sorted(fases, key=lambda f: f[1]):
        if (f[0], f[1]) not in gezien:
            gezien.add((f[0], f[1]))
            uit.append(f)
    return uit


def _paginas(pagina, starts, naam, patroon):
    testmap = os.environ.get(f"{naam}_DETAIL_MAP", "")
    gezien, uit = set(), []
    for start in dict.fromkeys(starts):
        for adres, tekst in t.haal_paginas(start, patroon, 12, testmap):
            if adres not in gezien:
                gezien.add(adres)
                uit.append((adres, tekst))
        if testmap:
            break
    return uit


def _uit_artikelen(sleutel, parser, naam, starts, patroon):
    uit = []
    for adres, tekst in _paginas(starts[0], starts, naam, patroon):
        w = parser(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
            uit.append(w)
    return uit


CLUBS = [
    ("aston-villa", "Aston Villa", "EN", "Aston Villa (artikelen)", "https://www.avfc.co.uk/news/", haal_villa, True),
    ("hull-city", "Hull City", "EN", "Hull City (artikelen)", "https://www.wearehullcity.co.uk/news/", haal_hull, True),
    ("sunderland", "Sunderland", "EN", "Sunderland (artikelen)", "https://www.safc.com/news/", haal_sunderland, True),
    ("ipswich-town", "Ipswich Town", "EN", "Ipswich Town (artikelen)", "https://www.itfc.co.uk/category/tickets", haal_ipswich, True),
    ("crystal-palace", "Crystal Palace", "EN", "Crystal Palace (verkoopdata)", "https://www.cpfc.co.uk/tickets/tickets-on-sale-dates/", haal_palace, False),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal, behoud):
    test = os.environ.get(f"{sleutel.upper().replace('-', '_')}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, BEHOUD=behoud, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
