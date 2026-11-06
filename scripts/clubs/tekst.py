"""Hulpfuncties voor clubs waarvan we de zichtbare tekst van de pagina lezen (geen nette gegevensbron)."""
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

NL = ZoneInfo("Europe/Amsterdam")
LONDEN = ZoneInfo("Europe/London")
MAANDEN_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
ZELF_HOOFDLETTERS = {"FC", "SC", "SV", "TSG", "FSV", "AS", "AC", "RB", "BSC", "AFC", "CF", "UD", "CD", "RCD", "FK", "SK", "NK", "PSV", "AZ"}
SPECIAAL = {"vfb": "VfB", "vfl": "VfL", "m'gladbach": "M'gladbach"}


def haal_tekst(pagina, testbestand=""):
    """Geef de zichtbare tekst van een pagina. Met testbestand lezen we dat in plaats van de site."""
    if testbestand:
        return open(testbestand, encoding="utf-8").read()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(locale="nl-NL")
            page.goto(pagina, wait_until="domcontentloaded", timeout=45000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:  # noqa: BLE001
                pass
            for _ in range(3):  # scrollen zodat lange lijsten volledig laden
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
            return page.inner_text("body")
        finally:
            browser.close()


def mooie_naam(tekst):
    """'BAYER 04 VS. VFB STUTTGART' -> 'VfB Stuttgart'-achtige schrijfwijze."""
    uit = []
    for w in tekst.strip().split():
        laag = w.lower()
        if laag in SPECIAAL:
            uit.append(SPECIAAL[laag])
        elif w.upper() in ZELF_HOOFDLETTERS:
            uit.append(w.upper())
        else:
            uit.append(w[:1].upper() + w[1:].lower())
    return " ".join(uit)


def naar_nl(d, zone):
    return d.replace(tzinfo=zone).astimezone(NL)


def tekst_fmt(d, alleen_datum=False):
    return d.strftime("%Y-%m-%d" if alleen_datum else "%Y-%m-%dT%H:%M")


def jaar_voor(dag, maand, uur, minuut, aftrap, zone):
    """Kies het jaar waarin een verkoopmoment voor de aftrap valt."""
    for jaar in (aftrap.year, aftrap.year - 1):
        try:
            d = datetime(jaar, maand, dag, uur, minuut, tzinfo=zone).astimezone(NL)
        except ValueError:
            continue
        if d <= aftrap:
            return d
    return None


def klok(tekst):
    """'8:45 pm' / '9 pm' / '12 am' -> (uur, minuut) in 24 uur. '12 am' lezen we als 12:00 (zie opmerking in dortmund.py)."""
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", tekst.strip(), re.I)
    uur, minuut, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
    if ap == "pm" and uur != 12:
        uur += 12
    return uur, minuut


MAANDEN_NL = {"jan": 1, "feb": 2, "mrt": 3, "maa": 3, "apr": 4, "mei": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12}
MAANDEN_DE = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12}
MAANDEN_DE_LANG = {"januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
                   "oktober": 10, "november": 11, "dezember": 12}
MAANDEN_NL_LANG = {"januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7, "augustus": 8, "september": 9,
                   "oktober": 10, "november": 11, "december": 12}


def adres_uit_lijst(naam, standaard):
    """Het adres van een club staat in scripts/verken_lijst.txt; dat is het exacte adres dat jij hebt ingevuld."""
    from pathlib import Path

    pad = Path(__file__).resolve().parent.parent / "verken_lijst.txt"
    if pad.exists():
        for regel in pad.read_text(encoding="utf-8").splitlines():
            n, _, a = regel.partition("|")
            if n.strip().lower() == naam.lower() and a.strip():
                return a.strip()
    return standaard


def jaar_voor_dag(dag, maand, uur=0, minuut=0, zone=NL, terug=45):
    """Datums op clubsites hebben geen jaar: kies het jaar waarbij de datum niet langer dan 'terug' dagen geleden is."""
    nu = datetime.now(zone)
    for jaar in (nu.year, nu.year + 1):
        try:
            d = datetime(jaar, maand, dag, uur, minuut, tzinfo=zone)
        except ValueError:
            continue
        if (nu - d).days <= terug:
            return d.astimezone(NL)
    return None
