"""Lijst van alle verzamelaars.

Clubs met een eigen bestand (nec.py, feyenoord.py) staan bovenaan. Clubs met dezelfde
(Tymes4-)ticketshop hoeven geen eigen bestand: zet ze gewoon in de lijst TYMES4_CLUBS.
Formaat: "sleutel": ("Naam van de club", "adres van de ticketshop", "naam van het thuisteam in de shop (mag weg)")
"""
import os
import time
from types import SimpleNamespace

from . import brentford, dortmund, feyenoord, groningen, leverkusen, nec, tekstclubs, tekstclubs2, tekstclubs3, tekstclubs4, tekstclubs5, tekstclubs6, tekstclubs7, tekstclubs8, tekstclubs9, tekstclubs10, tekstclubs11, tekstclubs12, ticketing_es, tymes4, tekstclubs13, tekstclubs14

TYMES4_CLUBS = {
    "utrecht": ("FC Utrecht", "https://ticketing.fcutrecht.nl/dashboard", "FC Utrecht"),
    "sparta": ("Sparta Rotterdam", "https://ticketshop.sparta-rotterdam.nl/dashboard"),
    "heerenveen": ("SC Heerenveen", "https://tickets.sc-heerenveen.nl/dashboard"),
    "cambuur": ("SC Cambuur", "https://tickets.cambuur.nl/dashboard"),
    "fortuna": ("Fortuna Sittard", "https://ticketshop.fortunasittard.nl/dashboard"),
    "excelsior": ("Excelsior", "https://tickets.excelsiorrotterdam.nl/dashboard"),
    "willem2": ("Willem II", "https://ticketshop.willem-ii.nl/dashboard"),
    "twente": ("FC Twente", "https://kaartverkoop.fctwente.nl/dashboard"),
}


def _maak(sleutel, naam, pagina, thuis=None):
    bron = os.environ.get(sleutel.upper() + "_BRON_URL", "")  # alleen voor tests

    def haal_op():
        if not bron:
            time.sleep(3)  # even wachten tussen twee clubs
        return tymes4.haal_op(sleutel, pagina, bron, thuis)

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, haal_op=haal_op)


ALLE = ([nec, feyenoord] + [_maak(k, *gegevens) for k, gegevens in TYMES4_CLUBS.items()]
        + [dortmund, groningen, leverkusen, brentford] + ticketing_es.ALLE + tekstclubs.ALLE + tekstclubs2.ALLE + tekstclubs3.ALLE + tekstclubs4.ALLE + tekstclubs5.ALLE + tekstclubs6.ALLE + tekstclubs7.ALLE + tekstclubs8.ALLE + tekstclubs9.ALLE + tekstclubs10.ALLE + tekstclubs11.ALLE + tekstclubs12.ALLE + tekstclubs13.ALLE + tekstclubs14.ALLE)
