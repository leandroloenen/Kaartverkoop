"""Leesprogramma's voor Spaanse clubs waarvan we de zichtbare tekst lezen: FC Barcelona, Real Betis en Valencia.

Deze sites tonen alleen of de verkoop al open is ("nu") of nog niet ("info"), geen startmomenten.
Real Madrid toont op de pagina geen wedstrijden en is daarom (nog) niet opgenomen.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd

MAANDEN_ES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
COMP_ES = {"primera división": "La Liga", "laliga": "La Liga", "la liga": "La Liga", "champions league": "Champions League",
           "uefa champions league": "Champions League", "copa del rey": "Copa del Rey", "europa league": "Europa League"}
TEGEN_ES = {"atlético de madrid": "Atlético Madrid", "rc deportivo": "Deportivo La Coruña", "celta": "Celta de Vigo", "racing": "Racing Santander"}


def comp_es(naam):
    return COMP_ES.get(naam.strip().lower(), naam.strip().title())


def _datum(dag, maand, uur=None, minuut=0):
    """Kies het jaar; zonder tijd geven we alleen de datum terug."""
    d = t.jaar_voor_dag(dag, maand, uur or 0, minuut)
    if not d:
        return None
    return d if uur is not None else t.tekst_fmt(d, alleen_datum=True)


# ---------------------------------------------------------------- Barcelona
BARCA_DATUM = re.compile(r"^(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2})(?:\s*/\s*(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+\d{1,2})?\s+([A-Z]{3})$")
BARCA_TIJD = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_barcelona(tekst, club="barcelona", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i, r in enumerate(regels):
        m = BARCA_DATUM.match(r)
        if not m:
            continue
        maand = t.MAANDEN_EN.get(m.group(2).lower())
        if not maand:
            continue
        blok = regels[i + 1:i + 14]
        if "vs." not in blok:
            continue
        k = blok.index("vs.")
        if k < 1 or k + 1 >= len(blok) or blok[k - 1] != "FC Barcelona":
            continue
        tegen = blok[k + 1]
        tm = BARCA_TIJD.match(blok[0])
        uur, minuut = (int(tm.group(1)), int(tm.group(2))) if tm else (None, 0)
        aftrap = _datum(int(m.group(1)), maand, uur, minuut)
        if not aftrap:
            continue
        compnaam = next((x for x in blok[:k] if x.lower() in COMP_ES or "league" in x.lower()), "")
        na = " ".join(blok[k + 2:k + 6]).lower()
        nu = "see tickets" in na
        info = not nu
        noot = "Verkoop is open (startmoment niet getoond)." if nu else "Nog niet in de verkoop; je kunt je aanmelden voor een bericht."
        uit.append(wedstrijd(club, TEGEN_ES.get(tegen.lower(), tegen), comp_es(compnaam), aftrap, nu=nu, info=info, noot=noot, bron=bron))
    return uit


# ---------------------------------------------------------------- Betis
BETIS_DAG = re.compile(r"^\d{2}$")


def parse_betis(tekst, club="betis", bron=""):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i in range(len(regels) - 6):
        if not BETIS_DAG.match(regels[i]) or regels[i + 1].lower()[:3] not in MAANDEN_ES:
            continue
        blok = regels[i + 2:i + 10]
        if "REAL BETIS" not in blok or "VS" not in blok:
            continue
        k = blok.index("VS")
        if k + 1 >= len(blok) or blok[k - 1] != "REAL BETIS":
            continue
        tegen = blok[k + 1]
        dag, maand = int(regels[i]), MAANDEN_ES[regels[i + 1].lower()[:3]]
        tm = re.search(r"(\d{1,2}):(\d{2})", blok[0])
        aftrap = _datum(dag, maand, int(tm.group(1)) if tm else None, int(tm.group(2)) if tm else 0)
        if not aftrap:
            continue
        compnaam = blok[k - 2] if k >= 2 else ""
        na = " ".join(blok[k + 2:k + 4]).upper()
        nu = "BUY" in na
        info = not nu
        noot = "Verkoop is open (startmoment niet getoond)." if nu else "Nog niet in de verkoop; je kunt je aanmelden voor een bericht."
        uit.append(wedstrijd(club, TEGEN_ES.get(tegen.lower(), t.mooie_naam(tegen)), comp_es(compnaam), aftrap, nu=nu, info=info, noot=noot, bron=bron))
    return uit


# ---------------------------------------------------------------- Valencia
VAL_DATUM = re.compile(r"^(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2})\s+([A-Z]{3})\b")


def parse_valencia(tekst, club="valencia", bron=""):
    """Alleen wedstrijden met een datum; de rest staat nog als 'to be determined' en kan niet worden getoond."""
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i, r in enumerate(regels):
        m = VAL_DATUM.match(r.upper())
        if not m:
            continue
        maand = t.MAANDEN_EN.get(m.group(2).lower())
        blok = regels[i + 1:i + 8]
        if not maand or "VALENCIA CF" not in [b.upper() for b in blok]:
            continue
        namen = [b.upper() for b in blok]
        k = namen.index("VALENCIA CF")
        tm = next((re.match(r"^(\d{1,2}):(\d{2})$", b) for b in blok[k:] if re.match(r"^(\d{1,2}):(\d{2})$", b)), None)
        rest = [b for b in blok[k + 1:] if not re.match(r"^\d{1,2}:\d{2}$", b) and b.upper() not in ("VS", "VIP TICKETS MATCH TICKETS", "VIP TICKETS", "MATCH TICKETS")]
        if not rest:
            continue
        tegen = rest[0]
        aftrap = _datum(int(m.group(1)), maand, int(tm.group(1)) if tm else None, int(tm.group(2)) if tm else 0)
        if not aftrap:
            continue
        nu = "MATCH TICKETS" in " ".join(blok).upper()
        compnaam = next((b for b in blok[:k] if b.upper() in ("LALIGA", "LA LIGA")), "LaLiga")
        uit.append(wedstrijd(club, t.mooie_naam(tegen), comp_es(compnaam), aftrap, nu=nu, info=not nu,
                             noot="Verkoop is open (startmoment niet getoond)." if nu else "Nog niet in de verkoop.", bron=bron))
    return uit


CLUBS = [
    ("barcelona", "FC Barcelona", "ES", "FC Barcelona", "https://www.fcbarcelona.com/en/tickets/football", parse_barcelona),
    ("betis", "Real Betis", "ES", "Real Betis", "https://en.realbetisbalompie.es/tickets/", parse_betis),
    ("valencia", "Valencia CF", "ES", "Valencia", "https://www.valenciacf.com/tickets", parse_valencia),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, parser):
    test = os.environ.get(f"{sleutel.upper()}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)

    def haal_op():
        return parser(t.haal_tekst(pagina, test), sleutel, pagina)

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=haal_op)


ALLE = [_maak(*c) for c in CLUBS]
