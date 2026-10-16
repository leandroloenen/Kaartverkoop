"""Verzamelaar voor N.E.C.

De ticketshop (tickets.nec-nijmegen.nl) haalt zijn wedstrijden op via een JSON-adres.
Dit programma leest datzelfde adres één keer per dag en zet het om naar ons formaat.

Wat de JSON ons vertelt (gecontroleerd op de voorbeeldgegevens van 16 oktober 2026):
- Alle tijden staan in UTC en worden hier omgezet naar Nederlandse tijd.
- Per wedstrijd laat de shop maar ÉÉN verkoopmoment zien: dat van de eerstvolgende fase
  (de "knop" die nog uitgeschakeld is, met in ActiveTill het moment waarop hij opengaat).
  Is die fase voorbij, dan springt de knop naar de volgende fase. update.py onthoudt
  daarom de fases van eerdere dagen en voegt de nieuwe erbij.
- Wedstrijden die al te koop zijn zonder aangekondigde fases krijgen alleen een notitie.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CLUB = "nec"
BRON_URL = os.environ.get("NEC_BRON_URL", "https://nec.api.tymes4-infra.com/v2/Event")
NL = ZoneInfo("Europe/Amsterdam")

COMPETITIES = [("eredivisie", "Eredivisie"), ("europa league", "Europa League"),
               ("conference league", "Conference League"), ("knvb", "KNVB Beker"),
               ("beker", "KNVB Beker")]
LABELS = {"seizoen": "Seizoenkaarthouders (SCC)", "clubkaart": "(Seizoen)clubkaarthouders",
          "vrij": "Vrije verkoop"}


def haal_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "kaartverkoop-hobbyproject (persoonlijk gebruik, 1x per dag)",
        "Accept": "application/json",
        "Referer": "https://tickets.nec-nijmegen.nl/",
        "Origin": "https://tickets.nec-nijmegen.nl",
    })
    with urllib.request.urlopen(req, timeout=30) as antwoord:
        return json.load(antwoord)


def naar_nl(tekst):
    """'2026-10-19T10:00:00' (UTC) -> '2026-10-19T12:00' (Nederlandse tijd)."""
    d = datetime.fromisoformat(tekst.replace("Z", "")).replace(tzinfo=timezone.utc)
    return d.astimezone(NL).strftime("%Y-%m-%dT%H:%M")


def competitie(naam):
    laag = (naam or "").lower()
    for sleutel, net in COMPETITIES:
        if sleutel in laag:
            return net
    return naam or "Onbekend"


def groep_uit_tekst(tekst):
    laag = tekst.lower()
    if "(s)cc" in laag:
        return "clubkaart"
    if "scc" in laag:
        return "seizoen"
    return "clubkaart"


def fases_van(item):
    knop = item.get("ButtonData") or {}
    tekst = (knop.get("TranslationCode") or "").strip()
    fases = []
    if (knop.get("ActionType") == "Disabled" and knop.get("ActiveTill")
            and tekst.lower().startswith("verkoop") and "info volgt" not in tekst.lower()):
        g = groep_uit_tekst(tekst)
        fases.append([g, naar_nl(knop["ActiveTill"]), LABELS[g]])
    if item.get("HasGeneralSale") and item.get("OnGeneralSaleFrom"):
        fases.append(["vrij", naar_nl(item["OnGeneralSaleFrom"]), LABELS["vrij"]])
    return fases, tekst


def parse(ruw):
    uit = []
    for tab in ruw.get("TabItems", []):
        if tab.get("TranslationCode") != "SALE-CATEGORY.MATCHHOME":
            continue  # alleen thuiswedstrijden
        for item in tab.get("Items", []):
            fases, tekst = fases_van(item)
            noot = ""
            if fases:
                noot = "Bron: " + tekst
            elif item.get("HasTicketsAvailable") and item.get("CurrentlyOnSaleForUser") is False \
                    and (item.get("ButtonData") or {}).get("TranslationCode") == "BTN.SALE.LOGINTOBUY":
                noot = "Nu in de verkoop (inloggen nodig); startmoment onbekend."
            uit.append({
                "club": CLUB,
                "tegen": item["NameAwayTeam"],
                "comp": competitie(item.get("EventTypeName")),
                "aftrap": naar_nl(item["EventStartDateTime"]),
                "fases": fases,
                "noot": noot,
                "bron": item.get("DeepLinkRoute") or "",
            })
    return uit


def haal_op():
    return parse(haal_json(BRON_URL))
