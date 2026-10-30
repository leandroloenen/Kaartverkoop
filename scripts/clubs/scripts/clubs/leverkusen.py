"""Verzamelaar voor Bayer Leverkusen: leest per thuiswedstrijd of de verkoop al open is of nog moet starten."""
import os
import re
from datetime import datetime

from . import tekst as t

CLUB = "leverkusen"
NAAM = "Bayer Leverkusen"
LAND = "DE"
PAGINA = "https://www.bayer04.de/en-us/shop/tickets/home-matches"
TEST = os.environ.get("LEVERKUSEN_TEKST_BESTAND", "")
WEDSTRIJD = re.compile(r"^BAYER 04 VS\.\s+(.+)$")
DATUM = re.compile(r"^\w+day\s+(\d{2})\.(\d{2})\.(\d{2})$", re.I)
TIJD = re.compile(r"^(\d{1,2}):(\d{2})$")
SPIELTAG = re.compile(r"^(\d+)\.\s*SPIELTAG$", re.I)


def parse(tekst):
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    uit = []
    for i, r in enumerate(regels):
        m = WEDSTRIJD.match(r)
        if not m:
            continue
        voor = regels[max(0, i - 4):i]
        na = regels[i + 1:i + 4]
        dm = next((DATUM.match(x) for x in na if DATUM.match(x)), None)
        tm = next((TIJD.match(x) for x in na if TIJD.match(x)), None)
        if not dm or not tm:
            continue
        aftrap = datetime(2000 + int(dm.group(3)), int(dm.group(2)), int(dm.group(1)), int(tm.group(1)), int(tm.group(2)), tzinfo=t.NL)
        speeldag = next((int(SPIELTAG.match(x).group(1)) for x in voor if SPIELTAG.match(x)), 99)
        comp = "Europees" if aftrap.weekday() in (1, 2, 3) and speeldag <= 8 else "Bundesliga"
        nu = any("on general sale" in x.lower() for x in voor)
        info = any("starting soon" in x.lower() or "not scheduled" in x.lower() for x in voor)
        uit.append({"club": CLUB, "tegen": t.mooie_naam(m.group(1)), "comp": comp, "aftrap": t.tekst_fmt(aftrap), "fases": [],
                    "nu": nu, "info": info,
                    "noot": "Algemene verkoop is gestart (startmoment niet getoond)." if nu else "Verkoop start binnenkort; datum nog niet bekend.",
                    "bron": PAGINA})
    return uit


def haal_op():
    return parse(t.haal_tekst(PAGINA, TEST))
