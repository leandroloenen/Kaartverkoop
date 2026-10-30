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


DUITSE_NAMEN = ("bayern", "dortmund", "leipzig", "frankfurt", "stuttgart", "hoffenheim", "mainz", "augsburg", "freiburg",
                "bremen", "wolfsburg", "gladbach", "köln", "union berlin", "hertha", "hamburg", "schalke", "bochum", "heidenheim",
                "st. pauli", "kiel", "darmstadt", "elversberg", "paderborn", "hannover", "nürnberg", "düsseldorf", "karlsruhe",
                "magdeburg", "braunschweig", "kaiserslautern", "fürth", "greuther", "regensburg", "münster", "ulm", "dresden",
                "rostock", "saarbrücken", "osnabrück", "bielefeld", "aachen", "wehen", "viktoria", "verl", "ingolstadt",
                "sandhausen", "lübeck", "havelse", "lautern", "oldenburg", "meppen", "essen", "duisburg", "cottbus")


def bepaal_competitie(w, bevestigd):
    """Weekend of speeldag 9+ = Bundesliga. Doordeweeks: Duitse tegenstander = DFB-Pokal, anders Europees voetbal."""
    spieltag, weekend, naam = w["_spieltag"], w["_weekend"], w["tegen"]
    duits = naam in bevestigd or any(k in naam.lower() for k in DUITSE_NAMEN)
    if spieltag is not None and (spieltag >= 9 or weekend):
        return "Bundesliga"
    if duits:
        # een Bundesliga-tegenstander komt maar één keer voor in de competitie; staat hij al elders, dan is dit de beker
        if spieltag is not None and naam not in bevestigd:
            return "Bundesliga"
        return "DFB-Pokal"
    return "Europees"


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
        speeldag = next((int(SPIELTAG.match(x).group(1)) for x in voor if SPIELTAG.match(x)), None)
        nu = any("on general sale" in x.lower() for x in voor)
        info = any("starting soon" in x.lower() or "not scheduled" in x.lower() for x in voor)
        uit.append({"club": CLUB, "tegen": t.mooie_naam(m.group(1)), "comp": "", "aftrap": t.tekst_fmt(aftrap), "fases": [],
                    "nu": nu, "info": info,
                    "noot": "Algemene verkoop is gestart (startmoment niet getoond)." if nu else "Verkoop start binnenkort; datum nog niet bekend.",
                    "bron": PAGINA, "_spieltag": speeldag, "_weekend": aftrap.weekday() in (4, 5, 6)})
    bevestigd = {w["tegen"] for w in uit if w["_spieltag"] is not None and (w["_spieltag"] >= 9 or w["_weekend"])}
    for w in uit:
        w["comp"] = bepaal_competitie(w, bevestigd)
        del w["_spieltag"], w["_weekend"]
    return uit


def haal_op():
    return parse(t.haal_tekst(PAGINA, TEST))
