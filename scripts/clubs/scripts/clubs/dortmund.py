"""Verzamelaar voor Borussia Dortmund: leest de tabel 'Schedule Overview' op de voorverkooppagina.

Let op: de Engelse pagina schrijft '12 am' bij het startmoment. Wij lezen dat als 12:00 uur (BVB gebruikt
in het Duits '12 Uhr'); controleer dit een keer bij een echte verkoopstart.
"""
import os
import re
from datetime import datetime

from . import tekst as t

CLUB = "bvb"
NAAM = "Borussia Dortmund"
LAND = "DE"
PAGINA = "https://www.bvb.de/de/en/tickets/ticket-information/presale-schedule.html"
TEST = os.environ.get("BVB_TEKST_BESTAND", "")
DATUM = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
VOORVERKOOP = re.compile(r"(\d{2})/(\d{2})/(\d{2}),\s*(\d{1,2}(?::\d{2})?\s*[ap]m)(?:\s*\((\d+) tickets?[^)]*\))?", re.I)
COMP = {"champions league": "Champions League", "bundesliga": "Bundesliga", "dfb-pokal": "DFB-Pokal", "europa league": "Europa League"}


def parse(tekst):
    uit = []
    for regel in tekst.splitlines():
        kol = regel.split("\t")
        if len(kol) < 6 or not DATUM.match(kol[0].strip()):
            continue
        m = re.match(r"^(.*?)\s*\((H|A)\)\s*$", kol[2].strip())
        if not m or m.group(2) != "H":
            continue  # alleen thuiswedstrijden
        d = [int(x) for x in DATUM.match(kol[0].strip()).groups()]
        uur, minuut = t.klok(kol[1])
        aftrap = datetime(2000 + d[2], d[0], d[1], uur, minuut, tzinfo=t.NL)
        fases = []
        for cel, groep, label in ((kol[4], "lid", "Leden (BVB-Mitglieder)"), (kol[5], "vrij", "Vrije voorverkoop (BVB-Fan)")):
            v = VOORVERKOOP.search(cel)
            if not v:
                continue
            u, mi = t.klok(v.group(4))
            moment = datetime(2000 + int(v.group(3)), int(v.group(1)), int(v.group(2)), u, mi, tzinfo=t.NL)
            extra = f" (max. {v.group(5)} tickets)" if v.group(5) else ""
            fases.append([groep, t.tekst_fmt(moment), label + extra])
        comp = COMP.get(kol[3].strip().lower(), kol[3].strip())
        uit.append({"club": CLUB, "tegen": m.group(1), "comp": comp, "aftrap": t.tekst_fmt(aftrap), "fases": fases,
                    "nu": False, "info": not fases, "noot": "", "bron": PAGINA})
    return uit


def haal_op():
    return parse(t.haal_tekst(PAGINA, TEST))
