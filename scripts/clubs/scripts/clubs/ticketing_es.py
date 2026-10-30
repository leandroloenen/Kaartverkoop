"""Verzamelaar voor clubs met hetzelfde Spaanse 'Ticketing'-systeem (Sevilla, Elche, Osasuna, Deportivo).

Dit systeem toont alleen de wedstrijden die NU te koop zijn (met datum, competitie en of de verkoop open staat).
Een verkoopstart wordt dus niet vooraf getoond; de pagina laat zien 'Nu te koop' en je ziet aan de lijst
hoeveel wedstrijden vooruit de club verkoopt.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from types import SimpleNamespace

from . import tekst as t
from .tymes4 import NIET_HOOFDPLOEG

COMPETITIES = {"laliga ea sports": "La Liga", "laliga hypermotion": "Segunda División", "copa del rey": "Copa del Rey"}

CLUBS = {
    "sevilla": ("Sevilla FC", "https://entradas.sevillafc.es/"),
    "elche": ("Elche CF", "https://entradas.elchecf.es/"),
    "osasuna": ("CA Osasuna", "https://entradas.osasuna.es/"),
    "deportivo": ("RC Deportivo", "https://ticketing.rcdeportivo.es/"),
}


def haal_json_via_browser(pagina):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(locale="es-ES")
            with page.expect_response(
                lambda r: r.url.split("?")[0].endswith("/api/events") and r.request.method == "GET" and r.status == 200,
                timeout=60000,
            ) as info:
                page.goto(pagina, wait_until="domcontentloaded")
            return info.value.json()
        finally:
            browser.close()


def parse(events, club, naam=""):
    wedstrijden = [e for e in events if e.get("type") in (None, "MATCH")]  # niet elke club vult het type in
    tellers = {}
    for e in wedstrijden:
        n = (e.get("localTeam") or {}).get("name")
        tellers[n] = tellers.get(n, 0) + 1
    kandidaten = {n: c for n, c in tellers.items() if n and not NIET_HOOFDPLOEG.search(n)} or tellers
    sleutelwoord = max(naam.split(), key=len).lower() if naam else ""
    voorkeur = {n: c for n, c in kandidaten.items() if sleutelwoord and sleutelwoord in n.lower()} or kandidaten
    thuis = max(voorkeur, key=voorkeur.get) if voorkeur else None
    uit = []
    for e in wedstrijden:
        if (e.get("localTeam") or {}).get("name") != thuis:
            continue
        d = datetime.fromisoformat(e["date"].replace("Z", "+00:00")).astimezone(t.NL)
        open_ = e.get("standardSaleType") == "public" and e.get("allowed", True)
        definitief = not e.get("noFinalDate")
        comp = COMPETITIES.get((e.get("competition") or "").lower(), e.get("competition") or "Onbekend")
        noot = "Nu in de verkoop (de shop toont geen startdatum)." if open_ else "Staat in de shop, maar de verkoop is nog niet open."
        if not definitief:
            noot += " Datum en tijd zijn nog niet definitief."
        uit.append({"club": club, "tegen": (e.get("awayTeam") or {}).get("name", "Onbekend"), "comp": comp,
                    "aftrap": t.tekst_fmt(d, not definitief), "fases": [], "nu": bool(open_), "info": not open_,
                    "noot": noot, "bron": ""})
    return uit


def _maak(sleutel, naam, pagina):
    testbestand = os.environ.get(f"{sleutel.upper()}_EVENTS_BESTAND", "")

    def haal_op():
        events = json.load(open(testbestand, encoding="utf-8")) if testbestand else haal_json_via_browser(pagina)
        return parse(events, sleutel, naam)

    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND="ES", haal_op=haal_op)


ALLE = [_maak(k, n, p) for k, (n, p) in CLUBS.items()]
