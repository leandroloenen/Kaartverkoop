"""Leesprogramma's voor Engelse clubs waarvan we de zichtbare tekst lezen: Tottenham Hotspur, Manchester City en Liverpool.

- Tottenham toont per groep (One Hotspur+, One Hotspur, General Sale) een datum of 'On Sale' (datum zonder tijd).
- Manchester City toont alleen of de verkoop open is; 'Hospitality on sale' tellen we niet als kaartverkoop.
- Liverpool toont alleen 'ON SALE SOON' / 'SOLD OUT' of niets; we tonen de thuiswedstrijden van het eerste team zonder startmoment.
"""
import os
import re
from datetime import datetime, date
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd

EN_COMP = {"premier league": "Premier League", "champions league": "Champions League", "uefa champions league": "Champions League",
           "fa cup": "FA Cup", "efl cup": "League Cup", "carabao cup": "League Cup", "europa league": "Europa League"}
MAANDEN_LANG = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8, "september": 9,
                "october": 10, "november": 11, "december": 12}


def comp_en(naam):
    return EN_COMP.get(naam.strip().lower(), naam.strip())


def _dag_voor(dag, maand, aftrap):
    """Jaar kiezen zodat de verkoopdatum op of voor de wedstrijddag valt."""
    a = aftrap if isinstance(aftrap, date) and not isinstance(aftrap, datetime) else aftrap.date()
    for jaar in (a.year, a.year - 1):
        try:
            d = date(jaar, maand, dag)
        except ValueError:
            continue
        if d <= a:
            return d.strftime("%Y-%m-%d")
    return None


# ---------------------------------------------------------------- Tottenham
SPURS_TIJD = re.compile(r"^(\d{1,2}):(\d{2}),\s+\w{3}\s+(\d{1,2})\s+([A-Za-z]{3})$")
SPURS_GROEP = re.compile(r"^(One Hotspur\+|One Hotspur|General Sale):\s*(.+)$")
SPURS_DATUM = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3})$")
SPURS_GROEPEN = {"One Hotspur+": ("lid", "One Hotspur+ (leden)"), "One Hotspur": ("lid", "One Hotspur (leden)"), "General Sale": ("vrij", "General Sale")}


def parse_tottenham(tekst, club="tottenham", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i, r in enumerate(regels):
        m = SPURS_TIJD.match(r)
        if not m:
            continue
        maand = t.MAANDEN_EN.get(m.group(4).lower())
        if not maand or i < 3:
            continue
        # de tegenstander staat vier regels boven de tijd: naam, competitie, categorie, tijd
        tegen, compnaam = regels[i - 3], regels[i - 2]
        aftrap = t.jaar_voor_dag(int(m.group(3)), maand, int(m.group(1)), int(m.group(2)), t.LONDEN)
        if not aftrap:
            continue
        fases, nu = [], False
        for x in regels[i + 2:i + 6]:
            g = SPURS_GROEP.match(x)
            if not g:
                continue
            groep, label = SPURS_GROEPEN[g.group(1)]
            waarde = g.group(2).strip()
            if waarde.lower() == "on sale":
                nu = True
                continue
            d = SPURS_DATUM.match(waarde)
            maand_f = t.MAANDEN_EN.get(d.group(2).lower()) if d else None
            if d and maand_f:
                dagtekst = _dag_voor(int(d.group(1)), maand_f, aftrap)
                if dagtekst:
                    if groep == "lid":
                        # De club meldt in haar nieuwsbericht over de verkoopdata dat de ledenverkoop om 10.00 uur (UK) begint = 11.00 uur NL.
                        dagtekst += "T11:00"
                        label += " - 10.00 uur UK-tijd"
                    fases.append([groep, dagtekst, label])
        uit.append(wedstrijd(club, tegen, comp_en(compnaam), aftrap, fases=fases, nu=nu, info=not fases and not nu,
                             noot="Starttijd voor leden volgens de club: 10.00 uur UK-tijd." if fases else "", bron=bron))
    return uit


# ---------------------------------------------------------------- Manchester City
CITY_DATUM = re.compile(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+([A-Za-z]{3})$")
CITY_TIJD = re.compile(r"^(\d{1,2}):(\d{2})$")


ENGELSE_CLUBS = ("brighton", "fulham", "leeds", "chelsea", "hull", "tottenham", "nottingham", "arsenal", "newcastle", "everton", "manchester united",
                 "crystal palace", "brentford", "aston villa", "liverpool", "coventry", "ipswich", "sunderland", "bournemouth", "bradford",
                 "west ham", "wolves", "burnley", "leicester", "southampton", "middlesbrough", "norwich")


def comp_city(tegen):
    """Buitenlandse tegenstander = Champions League; anders gaan we uit van de Premier League (een beker kan niet worden uitgesloten)."""
    return "Premier League" if any(k in tegen.lower() for k in ENGELSE_CLUBS) else "Champions League"


def parse_city(tekst, club="mancity", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i, r in enumerate(regels):
        m = CITY_DATUM.match(r)
        if not m or i + 6 >= len(regels):
            continue
        maand = t.MAANDEN_EN.get(m.group(2).lower())
        blok = regels[i + 1:i + 9]
        if not maand or blok[1] != "Manchester City" or not CITY_TIJD.match(blok[2]):
            continue  # alleen thuiswedstrijden (City staat dan als eerste team)
        tm = CITY_TIJD.match(blok[2])
        zone = t.LONDEN
        tegen = blok[4]
        aftrap = t.jaar_voor_dag(int(m.group(1)), maand, int(tm.group(1)), int(tm.group(2)), zone)
        if not aftrap:
            continue
        status = " ".join(blok[5:8]).lower()
        nu = ("tickets & hospitality on sale" in status) or ("tickets available" in status)
        qualifying = "qualifying" in status
        noot = ("Kaarten alleen voor 'qualifying fans' (o.a. seizoenkaart/leden)." if qualifying
                else "Verkoop is open (startmoment niet getoond)." if nu
                else "Alleen hospitality in de verkoop; gewone kaarten nog niet." if "hospitality on sale" in status
                else "Uitverkocht." if "sold out" in status else "")
        uit.append(wedstrijd(club, tegen, comp_city(tegen), aftrap, nu=nu, info=not nu and "sold out" not in status, noot=noot, bron=bron))
    return uit


# ---------------------------------------------------------------- Liverpool
LFC_DATUM = re.compile(r"^(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2})\s+([A-Z]+)$")
LFC_COMPS = ("premier league", "champions league", "fa cup", "efl cup", "carabao cup", "europa league")


def parse_liverpool(tekst, club="liverpool", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i, r in enumerate(regels):
        m = LFC_DATUM.match(r)
        if not m or i < 2 or i + 4 >= len(regels):
            continue
        maand = MAANDEN_LANG.get(m.group(2).lower())
        tm = re.match(r"^(\d{1,2}):(\d{2})$", regels[i - 2])
        if not maand or not tm:
            continue
        thuis, tegen, compnaam = regels[i + 1], regels[i + 2], regels[i + 3]
        if thuis != "Liverpool" or compnaam.lower() not in LFC_COMPS:
            continue
        stad_status = regels[i + 5].upper() if i + 5 < len(regels) else ""
        if "SOLD OUT" in stad_status:
            continue
        soon = "ON SALE SOON" in stad_status
        aftrap = t.jaar_voor_dag(int(m.group(1)), maand, int(tm.group(1)), int(tm.group(2)), t.LONDEN)
        if aftrap:
            uit.append(wedstrijd(club, tegen, comp_en(compnaam), aftrap, info=True,
                                 noot=("Verkoop start binnenkort; " if soon else "Verkoopstatus niet getoond; ") + "kaarten zijn alleen voor leden (All Red).", bron=bron))
    return uit


CLUBS = [
    ("tottenham", "Tottenham Hotspur", "EN", "Tottenham Hotspur", "https://www.tottenhamhotspur.com/tickets/mens-home-tickets", parse_tottenham),
    ("mancity", "Manchester City", "EN", "Manchester City", "https://www.mancity.com/tickets/mens", parse_city),
    ("liverpool", "Liverpool", "EN", "Liverpool", "https://www.liverpoolfc.com/tickets", parse_liverpool),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, parser):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)

    def haal_op():
        return parser(t.haal_tekst(pagina, test), sleutel, pagina)

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=haal_op)


ALLE = [_maak(*c) for c in CLUBS]
