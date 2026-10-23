"""Verzamelaar voor Feyenoord. Alle logica staat in tymes4.py; hier staan alleen de gegevens van de club."""
import os

from . import tymes4

CLUB = "feyenoord"
PAGINA = "https://tickets.feyenoord.com/dashboard"
THUIS_NAAM = "Feyenoord"
BRON_URL = os.environ.get("FEYENOORD_BRON_URL", "")  # alleen voor tests


def haal_op():
    return tymes4.haal_op(CLUB, PAGINA, BRON_URL, THUIS_NAAM)
