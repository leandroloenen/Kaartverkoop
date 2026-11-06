"""Leesprogramma's voor clubs waarvan we de zichtbare tekst van de ticketpagina lezen:
AZ, PEC Zwolle, ADO Den Haag, VfB Stuttgart, TSG Hoffenheim, 1. FC Union Berlin en 1. FSV Mainz 05.

Elke club heeft een eigen functie 'parse_<club>(tekst)'; de teksten komen uit de onzichtbare browser (of, bij tests, uit een bestand).
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tymes4 import schoon

ALIAS = {"Excelsior Rotterdam": "Excelsior", "SC Telstar": "Telstar", "NEC": "N.E.C.", "AFC Ajax": "Ajax"}
COMPETITIES = {"vriendenloterij eredivisie": "Eredivisie", "eredivisie": "Eredivisie", "europa league": "Europa League", "uefa europa league": "Europa League",
               "uefa champions league": "Champions League", "bundesliga": "Bundesliga", "dfb-pokal": "DFB-Pokal", "knvb beker": "KNVB Beker"}


def comp(naam):
    laag = naam.lower()
    for sleutel, net in COMPETITIES.items():
        if sleutel in laag:
            return net
    return naam.strip()


def wedstrijd(club, tegen, comp_naam, aftrap, fases=(), nu=False, info=False, noot="", bron=""):
    """aftrap: datetime (met tijd) of datum-string 'YYYY-MM-DD' (tijd nog onbekend)."""
    a = aftrap if isinstance(aftrap, str) else t.tekst_fmt(aftrap)
    return {"club": club, "tegen": ALIAS.get(tegen, tegen), "comp": comp_naam, "aftrap": a,
            "fases": sorted([list(f) for f in fases], key=lambda f: f[1]), "nu": nu, "info": info, "noot": noot, "bron": bron}


# ---------------------------------------------------------------- AZ
AZ_BLOK = re.compile(r"(?:MAANDAG|DINSDAG|WOENSDAG|DONDERDAG|VRIJDAG|ZATERDAG|ZONDAG)\n(\d{1,2}) ([A-Z]{3}) ⎯ (\d{2}):(\d{2})\n\s*Locatie:\n(.*?)\n\s*Team:\n.*?\n\s*Competitie:\n(.*?)\n\s*Thuis Team:\n(.*?)\nvs\nUit Team:\n(.*?)\n(.*?)MEER INFO", re.S)


def parse_az(tekst, club="az", bron=""):
    uit, gezien = [], set()
    for m in AZ_BLOK.finditer(tekst):
        dag, maand, uur, minuut = int(m.group(1)), t.MAANDEN_NL.get(m.group(2).lower()), int(m.group(3)), int(m.group(4))
        thuis, uit_team, status = m.group(7).strip(), m.group(8).strip(), m.group(9).upper()
        if thuis != "AZ" or not maand:
            continue
        aftrap = t.jaar_voor_dag(dag, maand, uur, minuut)
        if not aftrap or (aftrap, uit_team) in gezien:
            continue
        gezien.add((aftrap, uit_team))
        nu = info = False
        noot = ""
        if "RESALE" in status:
            noot = "Alleen nog resale beschikbaar."
        elif "UITVERKOCHT" in status:
            noot = "Uitverkocht."
        elif "KOOP NU" in status or "NU BESCHIKBAAR" in status:
            nu = True
        else:
            info = True
            noot = "Nog niet in de verkoop."
        uit.append(wedstrijd(club, t.mooie_naam(uit_team) if uit_team.isupper() else uit_team, comp(m.group(6)), aftrap, nu=nu, info=info, noot=noot, bron=bron))
    return uit


# ---------------------------------------------------------------- PEC Zwolle
PEC_BLOK = re.compile(r"(?:MA|DI|WO|DO|VR|ZA|ZAT|ZO)\s+(\d{2})\s+([A-Z]{3})\s+-\s+(\d{2}):(\d{2})\s*\n\s*([^\n]+?)\s*\n\s*([^\n]+?)\s*\n(\s*Bestel je tickets)?")


def parse_pec(tekst, club="pec", bron=""):
    uit, gezien = [], set()
    for m in PEC_BLOK.finditer(tekst):
        dag, maand, uur, minuut = int(m.group(1)), t.MAANDEN_NL.get(m.group(2).lower()), int(m.group(3)), int(m.group(4))
        if "MAC3PARK" not in m.group(5).upper() or not maand:
            continue
        teams = m.group(6).strip()
        if not teams.startswith("PEC Zwolle "):
            continue
        aftrap = t.jaar_voor_dag(dag, maand, uur, minuut)
        tegen = teams[len("PEC Zwolle "):].strip()
        if not aftrap or (aftrap, tegen) in gezien:
            continue
        gezien.add((aftrap, tegen))
        nu = bool(m.group(7))
        uit.append(wedstrijd(club, tegen, "Eredivisie", aftrap, nu=nu, info=not nu, noot="" if nu else "Nog niet in de verkoop.", bron=bron))
    return uit


# ---------------------------------------------------------------- ADO Den Haag
ADO_DATUM = re.compile(r"^(?:Ma|Di|Wo|Do|Vr|Za|Zo) (\d{2})-(\d{2})$")


def parse_ado(tekst, club="ado", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i, r in enumerate(regels):
        m = ADO_DATUM.match(r)
        if not m or i < 2 or i + 6 >= len(regels):
            continue
        thuis, tijd, tegen, status, tag = regels[i - 1], regels[i + 1], regels[i + 3], regels[i + 5], regels[i + 6]
        if thuis != "ADO Den Haag" or tag != "mannen" or regels[i + 4] != "Ticket info":
            continue
        uur, minuut = (int(x) for x in tijd.split(":"))
        aftrap = t.jaar_voor_dag(int(m.group(1)), int(m.group(2)), uur, minuut)
        if not aftrap:
            continue
        laag = status.lower()
        nu = laag.startswith("koop") or "(s)cc" in laag
        noot = "(S)CC verplicht." if "(s)cc" in laag else ("" if nu else "Nog geen kaartverkoop.")
        uit.append(wedstrijd(club, tegen, comp(regels[i - 2]), aftrap, nu=nu, info=not nu, noot=noot, bron=bron))
    return uit


# ---------------------------------------------------------------- VfB Stuttgart
ST_DATUM = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})")
ST_BEREIK = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*-\s*(\d{2})\.(\d{2})\.(\d{4})")
ST_START = re.compile(r"\|\s*(\d{2})\.(\d{2})\.(\d{4})\s*\|\s*(\d{1,2})(?::(\d{2}))?\s*Uhr")


def parse_stuttgart(tekst, club="stuttgart", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    starts = [i for i in range(len(regels) - 5) if re.fullmatch(r"\d{1,2}", regels[i]) and re.fullmatch(r"[A-ZÄ]{3,4}\.", regels[i + 1])
              and re.fullmatch(r"\d{4}", regels[i + 2]) and regels[i + 3].startswith("VfB Stuttgart")]
    uit = []
    for n, i in enumerate(starts):
        einde = starts[n + 1] if n + 1 < len(starts) else len(regels)
        blok = regels[i + 4:einde]
        tegen, comp_regel, rest = blok[0], blok[1], blok[2:]
        tekst_blok = "\n".join(rest)
        m = ST_DATUM.search(tekst_blok)
        if m:
            aftrap = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4)), int(m.group(5)), tzinfo=t.NL)
        else:
            b = ST_BEREIK.search(tekst_blok)
            if not b:
                continue
            aftrap = f"{b.group(3)}-{b.group(2)}-{b.group(1)}"
        fases, noot = [], ""
        aantal = re.search(r"max\.\s*(\d+)\s*Tickets", tekst_blok)
        extra = f" (max. {aantal.group(1)} tickets)" if aantal else ""
        for j, r in enumerate(rest):
            if r.lower().startswith("start des") and j + 1 < len(rest):
                s = ST_START.search(rest[j + 1])
                if s:
                    moment = datetime(int(s.group(3)), int(s.group(2)), int(s.group(1)), int(s.group(4)), int(s.group(5) or 0), tzinfo=t.NL)
                    laag = r.lower()
                    if "mitglieder" in laag:
                        fases.append(["lid", t.tekst_fmt(moment), "Leden (Mitglieder)" + extra])
                    else:
                        fases.append(["vrij", t.tekst_fmt(moment), "Start verkoop: " + r[9:].strip()])
        if "Mitgliederverkauf" in rest and not fases:
            noot = "Mitgliederverkauf (ledenverkoop) loopt nu."
        if "usverkauft" in tekst_blok:
            noot = (noot + " Uitverkocht of bijna uitverkocht.").strip()
        uit.append(wedstrijd(club, tegen, comp(comp_regel.split(",")[0]), aftrap, fases=fases, info=not fases and not noot, noot=noot, bron=bron))
    return uit


# ---------------------------------------------------------------- TSG Hoffenheim
def parse_hoffenheim(tekst, club="hoffenheim", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i in range(len(regels) - 8):
        if not (re.fullmatch(r"\d{1,2}", regels[i]) and re.fullmatch(r"[A-ZÄ]{3,4}\.", regels[i + 1]) and re.fullmatch(r"\d{4}", regels[i + 2])
                and regels[i + 3] == "TSG HOFFENHEIM" and regels[i + 4] == "-"):
            continue
        tegen, rest = t.mooie_naam(regels[i + 5]), regels[i + 6:i + 10]
        blok = "\n".join(rest)
        m = ST_DATUM.search(blok)
        if m:
            aftrap = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4)), int(m.group(5)), tzinfo=t.NL)
        else:
            b = ST_BEREIK.search(blok)
            if not b:
                continue
            aftrap = f"{b.group(3)}-{b.group(2)}-{b.group(1)}"
        comp_regel = next((r for r in rest if "2026" in r and ("Bundesliga" in r or "League" in r or "Pokal" in r)), "Bundesliga")
        uit.append(wedstrijd(club, tegen, comp(comp_regel), aftrap, nu="TICKETS" in rest, info="TICKETS" not in rest, bron=bron))
    return uit


# ---------------------------------------------------------------- 1. FC Union Berlin
UNION_KORT = {"Hoffenheim": "TSG Hoffenheim", "Leverkusen": "Bayer Leverkusen", "Bayern": "FC Bayern München", "Dortmund": "Borussia Dortmund",
              "Frankfurt": "Eintracht Frankfurt", "Mainz": "1. FSV Mainz 05", "Köln": "1. FC Köln", "Stuttgart": "VfB Stuttgart",
              "Bremen": "SV Werder Bremen", "Gladbach": "Borussia Mönchengladbach", "Leipzig": "RB Leipzig", "Freiburg": "SC Freiburg",
              "Augsburg": "FC Augsburg", "Wolfsburg": "VfL Wolfsburg", "Hamburg": "Hamburger SV", "Schalke": "FC Schalke 04", "Heidenheim": "1. FC Heidenheim"}
UNION = re.compile(r"(?:MO|DI|MI|DO|FR|SA|SO)\s*\|\s*(\d{2})\.(\d{2})\.\s*\|\s*(\d{1,2})(?::(\d{2}))?\s*UHR\s*\n+\s*([^\n]*?GEGEN\s+[^\n]+?)\s*\n+\s*(TICKETS[^\n]*)")


def parse_union(tekst, club="union", bron=""):
    uit = []
    for m in UNION.finditer(tekst):
        aftrap = t.jaar_voor_dag(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0))
        tegen = re.split(r"GEGEN\s+", m.group(5), 1)[1]
        if aftrap:
            tegen = t.mooie_naam(tegen)
            uit.append(wedstrijd(club, UNION_KORT.get(tegen, tegen), "Bundesliga", aftrap, nu=True,
                                 noot="Staat uitgelicht op de ticketpagina; de club toont niet alle wedstrijden.", bron=bron))
    return uit


# ---------------------------------------------------------------- 1. FSV Mainz 05
MZ_RIJ = re.compile(r"(?=(?:Mo|Di|Mi|Do|Fr|Sa|So)\.,\s+\d{1,2}\.\s*[A-Za-zäöü]+|(?<!\d)\d{1,2}\.-\d{1,2}\.\s*[A-Za-zäöü]+\s*\n?\(finale)")
MZ_DATUM = re.compile(r"(\d{1,2})\.\s*([A-Za-zäöü]+)\s*\(?\s*(\d{1,2})(?::(\d{2}))?\s*Uhr", re.S)
MZ_BEREIK = re.compile(r"(\d{1,2})\.-(\d{1,2})\.\s*([A-Za-zäöü]+)")


def parse_mainz(tekst, club="mainz", bron=""):
    i = tekst.find("Datum\tGegner")
    j = tekst.find("* Bestandskunden", i)
    if i < 0 or j < 0:
        return []
    uit = []
    for rij in MZ_RIJ.split(tekst[i:j]):
        cellen = [c.replace("\xa0", " ").strip() for c in rij.split("\t")]
        if len(cellen) < 6:
            continue
        datum, tegen = cellen[0], cellen[1]
        md = MZ_DATUM.search(datum)
        if md and t.MAANDEN_DE_LANG.get(md.group(2).lower()):
            aftrap = t.jaar_voor_dag(int(md.group(1)), t.MAANDEN_DE_LANG[md.group(2).lower()], int(md.group(3)), int(md.group(4) or 0))
        else:
            mb = MZ_BEREIK.search(datum)
            maand = t.MAANDEN_DE_LANG.get(mb.group(3).lower()) if mb else None
            d = t.jaar_voor_dag(int(mb.group(1)), maand) if maand else None
            aftrap = d.strftime("%Y-%m-%d") if d else None
        if not aftrap:
            continue
        aftrap_dt = aftrap if not isinstance(aftrap, str) else datetime.fromisoformat(aftrap + "T23:59").replace(tzinfo=t.NL)
        aantal = re.sub(r"\D", "", cellen[-1])
        fases = []
        for cel, groep, label in ((cellen[2], "lid", "Mitglieder en Dauerkarteninhaber"), (cellen[3], "clubkaart", "Bestandskunden / 11er-Karteninhaber"),
                                  (cellen[4], "vrij", "Freier Verkauf" + (f" (max. {aantal} tickets)" if aantal else ""))):
            ms = MZ_DATUM.search(cel)
            maand = t.MAANDEN_DE_LANG.get(ms.group(2).lower()) if ms else None
            if ms and maand:
                d = t.jaar_voor(int(ms.group(1)), maand, int(ms.group(3)), int(ms.group(4) or 0), aftrap_dt, t.NL)
                if d:
                    fases.append([groep, t.tekst_fmt(d), label])
        uit.append(wedstrijd(club, tegen, "Bundesliga", aftrap, fases=fases, info=not fases, bron=bron))
    return uit


# ---------------------------------------------------------------- aanmelden
CLUBS = [
    ("az", "AZ", "NL", "AZ", "https://www.az.nl/wedstrijden/tickets", parse_az),
    ("pec", "PEC Zwolle", "NL", "PEC Zwolle", "https://peczwolle.nl/teams/heren/peczwolle-26-27/programma", parse_pec),
    ("ado", "ADO Den Haag", "NL", "ADO Den Haag", "https://adodenhaag.nl/nl/tickets/kaartverkoop", parse_ado),
    ("stuttgart", "VfB Stuttgart", "DE", "VFB Stuttgart", "https://tickets.vfb.de/shop", parse_stuttgart),
    ("hoffenheim", "TSG Hoffenheim", "DE", "TSG Hoffenheim", "https://tickets.tsg-hoffenheim.de/shop", parse_hoffenheim),
    ("union", "1. FC Union Berlin", "DE", "FC Union Berlin", "https://www.tickets.union-zeughaus.de/shop", parse_union),
    ("mainz", "1. FSV Mainz 05", "DE", "FSV Mainz", "https://www.mainz05.de/tickets/heimspiele", parse_mainz),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, parser):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)

    def haal_op():
        return parser(t.haal_tekst(pagina, test), sleutel, pagina)

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=haal_op)


ALLE = [_maak(*c) for c in CLUBS]
