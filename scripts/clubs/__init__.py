"""Lijst van alle verzamelaars.

Clubs met een eigen bestand (nec.py, feyenoord.py) staan bovenaan. Clubs met dezelfde
(Tymes4-)ticketshop hoeven geen eigen bestand: zet ze gewoon in de lijst TYMES4_CLUBS.
Formaat: "sleutel": ("Naam van de club", "adres van de ticketshop", "naam van het thuisteam in de shop (mag weg)")
"""
import os
import time
from types import SimpleNamespace

from . import brentford, dortmund, feyenoord, groningen, leverkusen, nec, tekstclubs, tekstclubs2, tekstclubs3, tekstclubs4, tekstclubs5, tekstclubs6, tekstclubs7, tekstclubs8, tekstclubs9, tekstclubs10, tekstclubs11, tekstclubs12, ticketing_es, tymes4, tekstclubs13, tekstclubs14, aanvullen, tekstclubs15, tekstclubs16, tekstclubs17, tekstclubs18, tekstclubs19

TYMES4_CLUBS = {
    "utrecht": ("FC Utrecht", "https://ticketing.fcutrecht.nl/dashboard", "FC Utrecht"),
    "sparta": ("Sparta Rotterdam", "https://ticketshop.sparta-rotterdam.nl/dashboard"),
    "heerenveen": ("SC Heerenveen", "https://tickets.sc-heerenveen.nl/dashboard"),
    "cambuur": ("SC Cambuur", "https://tickets.cambuur.nl/dashboard"),
    "fortuna": ("Fortuna Sittard", "https://ticketshop.fortunasittard.nl/dashboard"),
    "excelsior": ("Excelsior", "https://tickets.excelsiorrotterdam.nl/dashboard"),
    "willem2": ("Willem II", "https://ticketshop.willem-ii.nl/dashboard"),
    "twente": ("FC Twente", "https://kaartverkoop.fctwente.nl/dashboard"),
    "telstar": ("SC Telstar", "https://tickets.sctelstar.nl/dashboard"),
}

# Clubs waarvan de clubsite ook artikelen over de kaartverkoop heeft: die vullen de fases aan (zie aanvullen.py).
EXTRA_FASES = {"willem2": tekstclubs15.haal_willem2_artikelen, "sparta": tekstclubs18.haal_sparta_artikelen,
               "ado": tekstclubs18.haal_ado_artikelen, "brighton": tekstclubs18.haal_brighton_artikelen,
               "liverpool": tekstclubs17.haal_liverpool_extra, "milan": tekstclubs19.haal_milan_artikelen,
               "inter": tekstclubs19.haal_inter_artikelen, "leverkusen": tekstclubs19.haal_leverkusen_artikelen}


def _maak(sleutel, naam, pagina, thuis=None):
    bron = os.environ.get(sleutel.upper() + "_BRON_URL", "")  # alleen voor tests

    def haal_op():
        if not bron:
            time.sleep(3)  # even wachten tussen twee clubs
        uit = tymes4.haal_op(sleutel, pagina, bron, thuis)
        extra = EXTRA_FASES.get(sleutel)
        if extra and uit and not bron:
            try:
                uit = aanvullen.verrijk(uit, extra())
            except Exception as fout:  # noqa: BLE001
                print(f"[{sleutel}] artikelen overgeslagen: {str(fout).splitlines()[0][:150]}")
        return uit

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, haal_op=haal_op)


ALLE = ([nec, feyenoord] + [_maak(k, *gegevens) for k, gegevens in TYMES4_CLUBS.items()]
        + [dortmund, groningen, leverkusen, brentford] + ticketing_es.ALLE + tekstclubs.ALLE + tekstclubs2.ALLE + tekstclubs3.ALLE + tekstclubs4.ALLE + tekstclubs5.ALLE + tekstclubs6.ALLE + tekstclubs7.ALLE + tekstclubs8.ALLE + tekstclubs9.ALLE + tekstclubs10.ALLE + tekstclubs11.ALLE + tekstclubs12.ALLE + tekstclubs13.ALLE + tekstclubs14.ALLE + tekstclubs16.ALLE + tekstclubs17.ALLE + tekstclubs19.ALLE)


def noot_hele_seizoen(uit):
    """Barcelona en Sevilla zetten het hele seizoen in de zomer in één keer in de verkoop."""
    for w in uit:
        if w.get("nu") and not w.get("fases"):
            w["noot"] = "Het seizoen wordt in de zomer in één keer in de verkoop gebracht."
    return uit


NA_AFLOOP = {"mancity": tekstclubs17.noten_city, "barcelona": noot_hele_seizoen, "sevilla": noot_hele_seizoen}


def _verrijk_niet_tymes4(module):
    """ADO en Brighton hebben een eigen verzamelaar voor de wedstrijden; die vullen we hier aan met de artikelen."""
    oud = module.haal_op

    def haal_op():
        uit = oud()
        na = NA_AFLOOP.get(module.CLUB)
        if uit and na:
            try:
                uit = na(uit)
            except Exception as fout:  # noqa: BLE001
                print(f"[{module.CLUB}] aanvulling overgeslagen: {str(fout).splitlines()[0][:150]}")
        extra = EXTRA_FASES.get(module.CLUB)
        if uit and extra:
            try:
                uit = aanvullen.verrijk(uit, extra())
            except Exception as fout:  # noqa: BLE001
                print(f"[{module.CLUB}] artikelen overgeslagen: {str(fout).splitlines()[0][:150]}")
        return uit

    module.haal_op = haal_op


for _m in ALLE:
    if _m.CLUB in ("ado", "brighton", "liverpool", "mancity", "milan", "inter", "leverkusen", "barcelona", "sevilla"):
        _verrijk_niet_tymes4(_m)
