"""Lijst van alle verzamelaars.

Clubs met een eigen bestand (nec.py, feyenoord.py) staan bovenaan. Clubs met dezelfde
(Tymes4-)ticketshop hoeven geen eigen bestand: zet ze gewoon in de lijst TYMES4_CLUBS.
Formaat: "sleutel": ("Naam van de club", "adres van de ticketshop")
"""
import os
import time
from types import SimpleNamespace

from . import feyenoord, nec, tymes4

TYMES4_CLUBS = {
    "utrecht": ("FC Utrecht", "https://ticketing.fcutrecht.nl/dashboard"),
    "sparta": ("Sparta Rotterdam", "https://ticketshop.sparta-rotterdam.nl/dashboard"),
    "heerenveen": ("SC Heerenveen", "https://tickets.sc-heerenveen.nl/dashboard"),
    "cambuur": ("SC Cambuur", "https://tickets.cambuur.nl/dashboard"),
    "fortuna": ("Fortuna Sittard", "https://ticketshop.fortunasittard.nl/dashboard"),
    "excelsior": ("Excelsior", "https://tickets.excelsiorrotterdam.nl/dashboard"),
    "willem2": ("Willem II", "https://ticketshop.willem-ii.nl/dashboard"),
    "twente": ("FC Twente", "https://kaartverkoop.fctwente.nl/dashboard"),
}


def _maak(sleutel, naam, pagina):
    bron = os.environ.get(sleutel.upper() + "_BRON_URL", "")  # alleen voor tests

    def haal_op():
        if not bron:
            time.sleep(3)  # even wachten tussen twee clubs
        return tymes4.haal_op(sleutel, pagina, bron, None)

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, haal_op=haal_op)


ALLE = [nec, feyenoord] + [_maak(k, n, p) for k, (n, p) in TYMES4_CLUBS.items()]
