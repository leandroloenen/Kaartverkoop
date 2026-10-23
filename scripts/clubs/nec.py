"""Verzamelaar voor N.E.C. Alle logica staat in tymes4.py; hier staan alleen de gegevens van de club."""
import os

from . import tymes4

CLUB = "nec"
PAGINA = "https://tickets.nec-nijmegen.nl/dashboard"
THUIS_NAAM = "N.E.C."
BRON_URL = os.environ.get("NEC_BRON_URL", "")  # alleen voor tests


def haal_op():
    return tymes4.haal_op(CLUB, PAGINA, BRON_URL, THUIS_NAAM)
