"""Gedeelde verzamelaar voor clubs met een ticketshop van Tymes4 (N.E.C., Feyenoord, ...).

Al deze shops laden hun wedstrijden via hetzelfde JSON-formaat. Het adres geeft zonder sessie een
401-melding, dus we openen de shop in een onzichtbare browser (Playwright) en lezen het antwoord
op het "/v2/Event"-verzoek dat de pagina zelf doet.

Verkoopmomenten staan op twee plekken:
1. In de knop van de wedstrijd (ButtonData): het moment waarop de eerstvolgende fase opengaat
   (alleen de eerstvolgende, dus update.py onthoudt eerdere fases).
2. In een infotekst (ShopLabels, "Voorrangsperioden"): een lijst met datum, tijd en doelgroep.
Alle tijden uit de JSON zijn UTC; de tekst gebruikt Nederlandse tijd.
"""
import html
import json
import re
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

NL = ZoneInfo("Europe/Amsterdam")

COMPETITIES = [("conference league", "Conference League"), ("europa league", "Europa League"),
               ("champions league", "Champions League"), ("eredivisie", "Eredivisie"),
               ("knvb", "KNVB Beker"), ("beker", "KNVB Beker")]
LABELS_KNOP = {"seizoen": "Seizoenkaarthouders (SCC)", "clubkaart": "(Seizoen)clubkaarthouders",
               "vrij": "Vrije verkoop"}
LABELS_TEKST = {"seizoen": "Seizoenkaart-/aandeelhouders", "lid": "Leden Het Legioen / Junior Kameraadjes",
                "vrij": "Vrije verkoop"}
MAANDEN = {"januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7,
           "augustus": 8, "september": 9, "oktober": 10, "november": 11, "december": 12}
GETALLEN = {"één": 1, "een": 1, "1": 1, "twee": 2, "2": 2, "drie": 3, "3": 3, "vier": 4, "4": 4,
            "vijf": 5, "5": 5, "zes": 6, "6": 6}
DATUM_RE = re.compile(r"^[-–\s]*(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+"
                      r"(\d{1,2})\s+([a-z]+)\s+om\s+(\d{1,2})[:.](\d{2})\s+uur", re.I)
AANTAL_RE = re.compile(r"(?:maximaal|max\.?)\s+(één|een|\d+|twee|drie|vier|vijf|zes)\s+tickets?", re.I)
EEN_RE = re.compile(r"\b(één|1)\s+ticket", re.I)


NAAM_ALIAS = {"n.e.c. nijmegen": "N.E.C.", "afc ajax": "Ajax", "sc heerenveen": "SC Heerenveen"}
NIET_HOOFDPLOEG = re.compile(r"\b(vrouwen|women|jong|onder\s?\d+|o\d{2}|u\d{2}|academy|talenten|jeugd)\b", re.I)


def schoon(naam):
    """Haal tekst tussen haakjes weg (zoals '(Noordtribune)') en gebruik overal dezelfde schrijfwijze."""
    naam = re.sub(r"\s*\(.*?\)", "", naam or "").strip()
    return NAAM_ALIAS.get(naam.lower(), naam)


def haal_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kaartverkoop-hobbyproject (persoonlijk gebruik, 1x per dag)"})
    with urllib.request.urlopen(req, timeout=30) as antwoord:
        return json.load(antwoord)


def haal_json_via_browser(pagina):
    """Open de shop in een onzichtbare browser en lees het antwoord van het Event-verzoek."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(locale="nl-NL")
            with page.expect_response(
                lambda r: "/v2/Event" in r.url and r.request.method == "GET" and r.status == 200,
                timeout=60000,
            ) as info:
                page.goto(pagina, wait_until="domcontentloaded")
            return info.value.json()
        finally:
            browser.close()


def utc_naar_nl(tekst):
    d = datetime.fromisoformat(tekst.replace("Z", "")).replace(tzinfo=timezone.utc)
    return d.astimezone(NL)


def competitie(naam):
    laag = (naam or "").lower()
    for sleutel, net in COMPETITIES:
        if sleutel in laag:
            return net
    return naam or "Onbekend"


# Clubs die (volgens de club zelf) nooit vrij verkopen: een onbekende doelgroep is daar altijd deze groep.
STANDAARD_GROEP = {"nec": "clubkaart"}
_HUIDIG = [None]


def groep_uit_knoptekst(tekst):
    """Gok de doelgroep uit de knoptekst. Geeft (groep, label); bij onzekerheid 'vrij' met de ruwe tekst als label."""
    laag = tekst.lower()
    if "(s)cc" in laag:
        return "clubkaart", LABELS_KNOP["clubkaart"]
    if "scc" in laag:
        return "seizoen", LABELS_KNOP["seizoen"]
    if any(w in laag for w in ("clubkaart", "club card", "clubcard")):
        return "clubkaart", LABELS_KNOP["clubkaart"]
    if "seizoen" in laag:
        return "seizoen", LABELS_KNOP["seizoen"]
    if any(w in laag for w in ("leden", "lid ", "member")):
        return "lid", "Leden"
    standaard = STANDAARD_GROEP.get(_HUIDIG[0])
    if standaard:
        return standaard, LABELS_KNOP[standaard]
    print(f"    let op ({_HUIDIG[0]}): verkoopmoment met onbekende doelgroep, laat het even controleren: \"{tekst}\"")
    return "vrij", "Start verkoop (doelgroep niet vermeld)"


MND_NAMEN = "januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december"
TXT_DATUM = re.compile(r"(?<![\d:.])(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{4}|\d{2}))?(?![\d:])")
TXT_DATUM_NAAM = re.compile(r"(\d{1,2})\s+(" + MND_NAMEN + r")(?:\s+(\d{4}))?", re.I)
TXT_TIJD = re.compile(r"(?<!\d)(\d{1,2})[:.](\d{2})(?!\d)")


def moment_uit_tekst(tekst, aftrap):
    """Lees de verkoopstart uit de knoptekst ('Verkoop start 19-11', '13-11 om 13:00 uur', 'Vanaf 20 november 9:00 uur').

    Geeft 'JJJJ-MM-DDTUU:MM' (met tijd) of 'JJJJ-MM-DD' (zonder tijd), of None als er geen datum in staat.
    Het jaar is het laatste jaar waarin de datum niet na de wedstrijd valt."""
    dag = maand = jaar = None
    rest = tekst
    m = TXT_DATUM.search(tekst)
    if m and 1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12:
        dag, maand = int(m.group(1)), int(m.group(2))
        if m.group(3):
            jaar = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        rest = tekst[:m.start()] + " " + tekst[m.end():]
    else:
        n = TXT_DATUM_NAAM.search(tekst)
        if n:
            dag, maand = int(n.group(1)), MAANDEN[n.group(2).lower()]
            jaar = int(n.group(3)) if n.group(3) else None
            rest = tekst[:n.start()] + " " + tekst[n.end():]
    if not dag:
        return None
    if jaar is None:
        for j in (aftrap.year, aftrap.year - 1):
            try:
                if datetime(j, maand, dag, tzinfo=NL).date() <= aftrap.date():
                    jaar = j
                    break
            except ValueError:
                continue
    if jaar is None:
        return None
    try:
        datetime(jaar, maand, dag)
    except ValueError:
        return None
    t = TXT_TIJD.search(rest)
    if t and int(t.group(1)) < 24 and int(t.group(2)) < 60:
        return f"{jaar:04d}-{maand:02d}-{dag:02d}T{int(t.group(1)):02d}:{t.group(2)}"
    return f"{jaar:04d}-{maand:02d}-{dag:02d}"


def fases_uit_knop(item):
    knop = item.get("ButtonData") or {}
    tekst = (knop.get("TranslationCode") or "").strip()
    fases = []
    laag = tekst.lower()
    if (knop.get("ActionType") == "Disabled" and knop.get("ActiveTill")
            and any(c.isdigit() for c in tekst) and "info volgt" not in laag
            and knop["ActiveTill"] < item["EventStartDateTime"]):
        g, label = groep_uit_knoptekst(tekst)
        aftrap_nl = utc_naar_nl(item["EventStartDateTime"])
        moment = moment_uit_tekst(tekst, aftrap_nl) or utc_naar_nl(knop["ActiveTill"]).strftime("%Y-%m-%dT%H:%M")
        fases.append([g, moment, label])
    if item.get("HasGeneralSale") and item.get("OnGeneralSaleFrom"):
        fases.append(["vrij", utc_naar_nl(item["OnGeneralSaleFrom"]).strftime("%Y-%m-%dT%H:%M"), LABELS_KNOP["vrij"]])
    return fases, tekst


def html_naar_regels(tekst):
    tekst = re.sub(r"</p>|<br\s*/?>|</h\d>|</li>", "\n", tekst, flags=re.I)
    tekst = html.unescape(re.sub(r"<[^>]+>", "", tekst))
    return [r.strip() for r in tekst.split("\n") if r.strip()]


def groep_van(zin):
    z = zin.lower()
    if "overige supporters" in z:
        return "vrij"
    if "gratis" in z:
        return None
    if "legioen" in z or "kameraadjes" in z or "leden" in z:
        return "lid"
    if any(w in z for w in ("aandeelhouder", "certificaathouder", "seizoenkaart")):
        return "seizoen"
    return None


def aantal_uit(zin):
    m = AANTAL_RE.search(zin) or EEN_RE.search(zin)
    if not m:
        return ""
    n = GETALLEN.get(m.group(1).lower())
    if n is None and m.group(1).isdigit():
        n = int(m.group(1))
    return f" (max. {n} ticket{'s' if n and n > 1 else ''})" if n else ""


def fases_uit_tekst(item, aftrap):
    tekst = next((l["DetailText"] for l in item.get("ShopLabels") or []
                  if l.get("LabelType") == "AdditionalInfo" and l.get("DetailText")), None)
    if not tekst:
        return []
    blokken, blok, binnen = [], None, False
    for r in html_naar_regels(tekst):
        laag = r.lower()
        if laag.startswith("voorrangsperioden"):
            binnen = True
            continue
        if not binnen:
            continue
        if laag.startswith(("aanmelden als nieuw lid", "ticket exchange", "prijzen")):
            break
        m = DATUM_RE.match(r)
        if m:
            dag, maand, uur, minuut = int(m.group(1)), MAANDEN.get(m.group(2).lower()), int(m.group(3)), int(m.group(4))
            moment = None
            for jaar in (aftrap.year, aftrap.year - 1):
                try:
                    d = datetime(jaar, maand, dag, uur, minuut, tzinfo=NL) if maand else None
                except ValueError:
                    d = None
                if d and d <= aftrap:
                    moment = d
                    break
            blok = {"moment": moment, "regels": []}
            blokken.append(blok)
        elif blok is not None:
            blok["regels"].append(r)
    fases, gezien = [], set()
    for b in blokken:
        if not b["moment"]:
            continue
        for zin in b["regels"]:
            g = groep_van(zin)
            if not g:
                continue
            f = [g, b["moment"].strftime("%Y-%m-%dT%H:%M"), LABELS_TEKST[g] + aantal_uit(zin)]
            if tuple(f) not in gezien:
                gezien.add(tuple(f))
                fases.append(f)
    return fases


def parse(ruw, club, thuis_naam=None):
    uit = []
    tellers = {}
    for tab in ruw.get("TabItems", []):
        if tab.get("TranslationCode") == "SALE-CATEGORY.MATCHHOME":
            for item in tab.get("Items", []):
                n = item.get("NameHomeTeam")
                tellers[n] = tellers.get(n, 0) + 1
    if thuis_naam not in tellers:  # naam onbekend of niet gevonden: herken de hoofdploeg zelf
        kandidaten = {n: c for n, c in tellers.items() if n and not NIET_HOOFDPLOEG.search(n)} or tellers
        thuis_naam = max(kandidaten, key=kandidaten.get) if kandidaten else None
    for tab in ruw.get("TabItems", []):
        if tab.get("TranslationCode") != "SALE-CATEGORY.MATCHHOME":
            continue  # alleen thuiswedstrijden
        for item in tab.get("Items", []):
            if thuis_naam and item.get("NameHomeTeam") != thuis_naam:
                continue  # sla jeugd- en vrouwenteams over
            aftrap = utc_naar_nl(item["EventStartDateTime"])
            fases, knoptekst = fases_uit_knop(item)
            fases += fases_uit_tekst(item, aftrap)
            code = (item.get("ButtonData") or {}).get("TranslationCode")
            nu = bool(item.get("HasTicketsAvailable")) and code in ("BTN.SALE.BUYNOW", "BTN.SALE.LOGINTOBUY")
            info = (not fases) and (not nu) and ("volgt" in (knoptekst or "").lower())
            noot = ""
            if not fases and nu:
                noot = "Nu in de verkoop; startmoment onbekend."
            elif info:
                noot = "Verkoopmomenten nog niet bekendgemaakt."
            uit.append({
                "club": club,
                "tegen": schoon(item["NameAwayTeam"]),
                "comp": competitie(item.get("EventTypeName")),
                "aftrap": aftrap.strftime("%Y-%m-%dT%H:%M"),
                "fases": sorted(fases, key=lambda f: f[1]),
                "nu": nu,
                "info": info,
                "noot": noot,
                "bron": item.get("DeepLinkRoute") or "",
            })
    samen = {}
    for w in uit:
        k = (w["tegen"], w["aftrap"][:10])
        if k not in samen:
            samen[k] = w
            continue
        m = samen[k]
        bekend = {(f[0], f[1], f[2]) for f in m["fases"]}
        m["fases"] = sorted(m["fases"] + [f for f in w["fases"] if (f[0], f[1], f[2]) not in bekend], key=lambda f: f[1])
        m["nu"] = m["nu"] or w["nu"]
        m["info"] = m["info"] and w["info"]
        if not m["noot"]:
            m["noot"] = w["noot"]
    return list(samen.values())


def haal_op(club, pagina, bron_url="", thuis_naam=None):
    """bron_url is alleen voor tests (een lokaal bestand); anders gebruiken we de onzichtbare browser."""
    _HUIDIG[0] = club
    ruw = haal_json(bron_url) if bron_url.startswith("file:") else haal_json_via_browser(pagina)
    return parse(ruw, club, thuis_naam)
