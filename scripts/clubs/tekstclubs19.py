"""Clubs uit Italië en Spanje met Engelstalige clubberichten of wedstrijdpagina's: ACF Fiorentina, Udinese, RCD Espanyol en Real Madrid.

Ook de artikel-lezers die de wedstrijdlijst van AC Milan, Inter en Bayer Leverkusen aanvullen met verkoopfases (zie EXTRA_FASES in __init__.py).

Fiorentina/Udinese: verkoopfases uit berichten per thuiswedstrijd.

- Fiorentina: 'Info biglietti Fiorentina vs X' en de ticketpagina per wedstrijd met 'Phase 1: InViola Premium Card', 'Phase 2: General sale', 'Phase 3: Matchday'.
- Udinese: bericht per wedstrijd met 'Phase 1' (leden van het 1896 Membership Programme) en 'Phase 2' (vrije verkoop).
Italiaanse tijden zijn gelijk aan Nederlandse tijden.
"""
import os
import re
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs12 import _jaar_voor_fase
from .tekstclubs5 import toekomst
from .tekstclubs14 import EN_MAAND, _toekomst
from .tekstclubs7 import naam

MND = "|".join(m.capitalize() for m in EN_MAAND)
DAG = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
# '10:00 on Tuesday, November 17, 2026' / '10:00 AM, 17 November 2026' / '16:00 on Friday 16 October'
TIJD = r"(\d{1,2})[:.](\d{2})\s*(AM|PM)?"
DATUM_A = r"(?:" + DAG + r",?\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(" + MND + r")(?:,?\s+(\d{4}))?"
DATUM_B = r"(?:" + DAG + r",?\s+)?(" + MND + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?"
MOMENT_1 = re.compile(TIJD + r"[,\s]*(?:on\s+)?" + DATUM_A, re.I)   # tijd eerst, dag-maand
MOMENT_2 = re.compile(TIJD + r"[,\s]*(?:on\s+)?" + DATUM_B, re.I)   # tijd eerst, maand-dag
MOMENT_3 = re.compile(DATUM_A + r"[,\s]+(?:kick-?off\s*)?(?:at\s+)?" + TIJD, re.I)   # dag-maand eerst
MOMENT_4 = re.compile(DATUM_B + r"[,\s]+(?:kick-?off\s*)?(?:at\s+)?" + TIJD, re.I)   # maand-dag eerst


def _moment_in(blok, aftrap):
    """Eerste 'tijd + datum' in de tekst als 'YYYY-MM-DDTHH:MM' (jaar via aftrap als het ontbreekt)."""
    kand = []
    for m in MOMENT_1.finditer(blok):
        kand.append((m.start(), m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
    for m in MOMENT_2.finditer(blok):
        kand.append((m.start(), m.group(1), m.group(2), m.group(3), m.group(5), m.group(4), m.group(6)))
    for m in MOMENT_3.finditer(blok):
        kand.append((m.start(), m.group(4), m.group(5), m.group(6), m.group(1), m.group(2), m.group(3)))
    if not kand:
        return None
    _, h, mi, ap, dag, mnd, jaar = sorted(kand)[0]
    h = int(h)
    if ap and ap.upper() == "PM" and h < 12:
        h += 12
    if ap and ap.upper() == "AM" and h == 12:
        h = 0
    m = EN_MAAND[mnd.lower()]
    j = int(jaar) if jaar else _jaar_voor_fase(int(dag), m, aftrap)
    return f"{j:04d}-{m:02d}-{int(dag):02d}T{h:02d}:{mi}"


AF_KICKOFF = re.compile(r"(\d{1,2}):(\d{2})\s*(?:CET\s+)?kick-?off.{0,80}?\bon\s+(?:" + DAG + r",?\s+)?(" + MND + r")\s+(\d{1,2}),?\s+(\d{4})", re.I | re.S)


def _aftrap(tekst, tegen_kop):
    """Aftrap uit 'Monday 7 December 2026, 20:45' of 'Monday, December 7, 2026 ... 20:45' vlak bij de kop met de wedstrijd."""
    start = tegen_kop.end()
    stuk = tekst[start:start + 900]
    af = AF_KICKOFF.search(stuk)
    if af:
        mm = EN_MAAND[af.group(3).lower()]
        return f"{int(af.group(5)):04d}-{mm:02d}-{int(af.group(4)):02d}T{int(af.group(1)):02d}:{af.group(2)}"
    fase = re.search(r"Phase\s*\d", stuk, re.I)
    if fase:
        stuk = stuk[:fase.start()]
    kand = []
    for patroon in (MOMENT_3, MOMENT_4):
        m = patroon.search(stuk)
        if m:
            kand.append((m.start(), patroon, m))
    for _, patroon, m in sorted(kand, key=lambda x: x[0])[:1]:
        if True:
            if patroon is MOMENT_3:
                d, mnd, jr, h, mi = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            else:
                mnd, d, jr, h, mi = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            mm = EN_MAAND[mnd.lower()]
            if jr:
                return f"{int(jr):04d}-{mm:02d}-{int(d):02d}T{int(h):02d}:{mi}"
            dt = t.jaar_voor_dag(int(d), mm, int(h), int(mi))
            return t.tekst_fmt(dt) if dt else None
    return None


def _blokken(tekst, kop_regex):
    delen = list(re.finditer(kop_regex, tekst, re.I))
    for n, m in enumerate(delen):
        yield m, tekst[m.end():delen[n + 1].start() if n + 1 < len(delen) else len(tekst)]


# ---------------------------------------------------------------- Fiorentina
FI_KOP = re.compile(r"Fiorentina\s+(?:vs\.?|v|-)\s+([A-Z][A-Za-z.' ]+?)(?:\s+ticket|\s*,|\s*\n|\s*Serie A|\s*\(|\s*Coppa)", re.I)
FI_FASE = r"Phase\s*(\d)\s*[:\-–]?\s*([^\n]*)"


def parse_fiorentina(tekst, club="acf-fiorentina", bron=""):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    k = FI_KOP.search(tekst)
    if not k:
        return None
    aftrap = _aftrap(tekst, k)
    if not aftrap or not _toekomst(aftrap):
        return None
    fases = []
    for m, blok in _blokken(tekst, FI_FASE):
        titel = m.group(2).lower()
        blok = m.group(2) + "\n" + blok[:700]
        start = _moment_in(blok, aftrap)
        if not start:
            continue
        if "inviola" in titel or "premium" in titel:
            fases.append(["clubkaart", start, "InViola Premium Card-houders"])
        elif "general" in titel or "public" in titel:
            fases.append(["vrij", start, "Vrije verkoop"])
        elif "matchday" in titel:
            fases.append(["vrij", start, "Wedstrijddag (tarief op de dag zelf)"])
    if not fases:
        return None
    comp = "Coppa Italia" if re.search(r"coppa italia", tekst[:1500], re.I) else "Serie A"
    return wedstrijd(club, k.group(1).strip().title(), comp, aftrap, fases=sorted(fases, key=lambda f: f[1]), bron=bron)


def haal_fiorentina(pagina, test, sleutel="acf-fiorentina"):
    testmap = os.environ.get("FIORENTINA_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/en/news/info-biglietti-fiorentina-vs-[a-z0-9-]+$", 10, testmap):
        w = parse_fiorentina(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- Udinese
UD_KOP = re.compile(r"Udinese\s+(?:v|vs\.?|-)\s+([A-Z][A-Za-z.' ]+?)(?:\s+ticket|\s+at\b|\s*,|\s*\n|\s+Bluenergy)", re.I)
UD_FASE = r"Phase\s*(\d)\s*[:\-–]?\s*([^\n]*)"


def parse_udinese(tekst, club="udinese-calcio", bron=""):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    k = UD_KOP.search(tekst)
    if not k:
        return None
    aftrap = _aftrap(tekst, k)
    if not aftrap or not _toekomst(aftrap):
        return None
    fases = []
    for m, blok in _blokken(tekst, UD_FASE):
        blok = m.group(2) + "\n" + blok[:600]
        start = _moment_in(blok, aftrap)
        if not start:
            continue
        laag = blok.lower()
        if "member" in laag or "1896" in laag:
            fases.append(["lid", start, "Leden (1896 Membership Programme)"])
        elif "general" in laag or "public" in laag:
            fases.append(["vrij", start, "Vrije verkoop"])
    if not fases:
        return None
    return wedstrijd(club, k.group(1).strip(), "Serie A", aftrap, fases=sorted(fases, key=lambda f: f[1]), bron=bron)


def haal_udinese(pagina, test, sleutel="udinese-calcio"):
    testmap = os.environ.get("UDINESE_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"viewSection\?id=\d+", 15, testmap):
        w = parse_udinese(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- RCD Espanyol (alle thuiswedstrijden uit 'Next matches'; de knop BUY TICKETS staat bij elke thuiswedstrijd en zegt niets over de verkoopstatus)
ES_RIJ = re.compile(
    r"^([A-ZÀ-Ý][A-ZÀ-Ý.' -]+?)\s+VS\s+([A-ZÀ-Ý][A-ZÀ-Ý.' -]+?)\s*\n\s*\nMATCHDAY\s+(\d+)\s+·[^|\n]*\|\s*[A-Z]+,\s*([A-Z]+)\s+(\d{1,2}),\s*(\d{4})"
    r"(?:\s+(\d{1,2}):(\d{2}))?([^\n]*)\n(\s*\n\s*BUY TICKETS)?", re.M)
KLEIN = {"fc", "cf", "ud", "ca", "rc", "rcd", "sd", "cd", "ad"}
ES_NAMEN = {"RC CELTA": "Celta de Vigo", "REAL RACING CLUB": "Real Racing Club", "CA OSASUNA": "Osasuna", "RC DEPORTIVO DE A CORUÑA": "Deportivo de La Coruña"}


def _naam(s):
    s = s.strip()
    if s in ES_NAMEN:
        return ES_NAMEN[s]
    return " ".join(w.lower() if w.lower() in ("de", "la") else w.upper() if w.lower() in KLEIN else w.capitalize() for w in s.split())


def parse_espanyol(tekst, club="rcd-espanyol", bron=""):
    uit = []
    for m in ES_RIJ.finditer(tekst):
        if m.group(1).strip() != "RCD ESPANYOL":
            continue
        mnd = t.MAANDEN_EN.get(m.group(4).lower()[:3])
        if not mnd:
            continue
        dag = f"{int(m.group(6)):04d}-{mnd:02d}-{int(m.group(5)):02d}"
        aftrap = dag + (f"T{int(m.group(7)):02d}:{m.group(8)}" if m.group(7) else "")
        if not toekomst(dag + "T23:59"):
            continue
        uit.append(wedstrijd(club, _naam(m.group(2)), "La Liga", aftrap, nu=False, info=True,
                             noot="Aanvangstijd nog niet bevestigd." if not m.group(7) else "", bron=bron))
    return uit


def haal_espanyol(pagina, test, sleutel="rcd-espanyol"):
    test = os.environ.get("RCD_ESPANYOL_TEKST_BESTAND", "")
    return parse_espanyol(t.haal_tekst(pagina, test, locale="en-GB"), sleutel, pagina)


# ---------------------------------------------------------------- Real Madrid (lijstpagina + pop-up 'More information' per wedstrijd)
RM_KOP = re.compile(r"\nReal Madrid\n\n(.+?)\n\nFútbol · Primer Equipo\n\n(.+?)\n\n[^\n]*\n\n[A-Za-z]+, ([A-Za-z]{3}) (\d{1,2}), (\d{1,2}):(\d{2}) (AM|PM) h")
RM_DATUM = re.compile(r"^[A-Za-z]{3}, ([A-Za-z]{3}) (\d{1,2}) - (\d{1,2})h$")
RM_GROEP = {
    "season ticket holders": ("seizoen", "Seizoenkaarthouders"),
    "affected uefa members": ("lid", "Getroffen UEFA-leden"),
    "non-season ticket holder members": ("lid", "Leden zonder seizoenkaart"),
    "madridistas platinum/premium": ("lid", "Madridistas Platinum/Premium"),
    "general public": ("vrij", "Vrije verkoop"),
}
RM_COMP = {"la liga": "La Liga", "champions league": "Champions League", "copa del rey": "Copa del Rey"}


def parse_rm_lijst(tekst, club="real-madrid", bron=""):
    uit = []
    for m in RM_KOP.finditer("\n" + tekst):
        mnd = t.MAANDEN_EN.get(m.group(3).lower()[:3])
        if not mnd:
            continue
        h = int(m.group(5)) % 12 + (12 if m.group(7) == "PM" else 0)
        dt = t.jaar_voor_dag(int(m.group(4)), mnd, h, int(m.group(6)), t.NL, terug=20)
        if not dt:
            continue
        aftrap = t.tekst_fmt(dt)
        if toekomst(aftrap):
            uit.append(wedstrijd(club, m.group(1).strip(), RM_COMP.get(m.group(2).strip().lower(), m.group(2).strip()), aftrap, info=True,
                                 noot="Verkoopmomenten per groep volgen.", bron=bron))
    return uit


def parse_rm_popup(tekst, aftrap):
    """Fases uit de pop-up 'Prices and on-sale dates' (tijden zijn Spaanse tijd = Nederlandse tijd)."""
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    if "Prices and on-sale dates" not in regels:
        return []
    uit, label, korting = [], None, ""
    for r in regels[regels.index("Prices and on-sale dates") + 1:]:
        if r == "Real Madrid":  # menu onder de pop-up
            break
        d = RM_DATUM.match(r)
        if d and label:
            mnd = t.MAANDEN_EN.get(d.group(1).lower()[:3])
            if mnd:
                j = _jaar_voor_fase(int(d.group(2)), mnd, aftrap)
                uit.append([label[0], f"{j:04d}-{mnd:02d}-{int(d.group(2)):02d}T{int(d.group(3)):02d}:00", label[1] + korting])
            label, korting = None, ""
        elif re.match(r"^\d+% discount$", r):
            korting = f" ({r.split('%')[0]}% korting)"
        elif r.lower() in RM_GROEP:
            label, korting = RM_GROEP[r.lower()], ""
    return sorted(uit, key=lambda f: f[1])


def haal_realmadrid(pagina, test, sleutel="real-madrid"):
    """Lees de lijst, klik per wedstrijd op 'More information' en lees de pop-up."""
    if test:
        return parse_rm_lijst(open(test, encoding="utf-8").read(), sleutel, pagina)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(locale="en-GB")

            def open_lijst():
                page.goto(pagina, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=12000)
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_timeout(2500)
                try:
                    knop = page.get_by_role("button", name=re.compile(r"reject all", re.I)).first
                    if knop.count():
                        knop.click(timeout=3000)
                        page.wait_for_timeout(800)
                except Exception:  # noqa: BLE001
                    pass

            open_lijst()
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(900)
            wedstrijden = parse_rm_lijst(page.inner_text("body"), sleutel, pagina)
            knoppen = page.get_by_role("link", name=re.compile(r"more information", re.I)).or_(page.get_by_role("button", name=re.compile(r"more information", re.I)))
            aantal = min(knoppen.count(), 12)
            for n in range(aantal):
                try:
                    if n:
                        open_lijst()
                        knoppen = page.get_by_role("link", name=re.compile(r"more information", re.I)).or_(page.get_by_role("button", name=re.compile(r"more information", re.I)))
                    knoppen.nth(n).click(timeout=10000, force=True)
                    page.wait_for_timeout(2500)
                    tekst = page.inner_text("body")
                except Exception:  # noqa: BLE001
                    continue
                kop = re.search(r"^Real Madrid - (.+)$", tekst, re.M)
                if not kop:
                    continue
                for w in wedstrijden:
                    if w["tegen"].strip().lower() == kop.group(1).strip().lower():
                        fases = parse_rm_popup(tekst, w["aftrap"])
                        if fases:
                            w["fases"], w["info"], w["noot"] = fases, False, ""
                        break
            return wedstrijden
        finally:
            browser.close()


# ---------------------------------------------------------------- Artikelen van Milan, Inter en Leverkusen (vullen de wedstrijdlijst aan met de verkoopfases)
def _fmt(dag, mnd, h, mi, ampm, aftrap):
    """'YYYY-MM-DDTHH:MM' voor een verkoopmoment; het jaar volgt uit de aftrap (hoogstens op de wedstrijddag zelf)."""
    m = EN_MAAND.get(mnd.lower())
    if not m:
        return None
    h = int(h)
    if ampm and ampm.upper() == "PM" and h < 12:
        h += 12
    if ampm and ampm.upper() == "AM" and h == 12:
        h = 0
    try:
        return f"{_jaar_voor_fase(int(dag), m, aftrap):04d}-{m:02d}-{int(dag):02d}T{h:02d}:{mi}"
    except ValueError:
        return None


MAX4 = "Max. 4 tickets per persoon."

# --- AC Milan: 'Tickets available for the match at San Siro on Tuesday, January 5th, at 8:45 PM CET'
ML_TEGEN = re.compile(r"AC MILAN\s+vs\.?\s+([A-Z][A-Z .'’-]+?)\s*(?::|\n)", re.I)
ML_AFTRAP = re.compile(r"(?:at San Siro on|available for[^\n]{0,60}? on|scheduled for)\s+(?:" + DAG + r",?\s+)?(" + MND + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+at\s+(\d{1,2}):(\d{2})\s*(AM|PM)", re.I)
ML_FASE = re.compile(r"^\s*(Plus Season Ticket Holders|Season Ticket Holders|Milan Club(?: Phase| Members)?|General sale)\b[^\n]*", re.I | re.M)
ML_MOMENT = re.compile(r"(?:" + DAG + r",?\s+)?(" + MND + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+at\s+(\d{1,2}):(\d{2})\s*(AM|PM)", re.I)
ML_COMP = (("europa league", "Europa League"), ("champions league", "Champions League"), ("coppa italia", "Coppa Italia"), ("serie a", "Serie A"))


def parse_milan_artikel(tekst, club="milan", bron=""):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    k = ML_TEGEN.search(tekst)
    a = ML_AFTRAP.search(tekst)
    if not k or not a:
        return None
    mm = EN_MAAND[a.group(1).lower()]
    dt = t.jaar_voor_dag(int(a.group(2)), mm, int(a.group(3)) + (12 if a.group(5).upper() == "PM" and int(a.group(3)) < 12 else 0), int(a.group(4)))
    if not dt:
        return None
    aftrap = t.tekst_fmt(dt)
    if not _toekomst(aftrap):
        return None
    i = tekst.find("TICKETS", a.end())
    j = tekst.find("PRICES AND PROMOTIONS", a.end())
    deel = tekst[i:j if j > i else i + 2500] if i >= 0 else ""
    fases = []
    for m in ML_FASE.finditer(deel):
        regel = m.group(0)
        mo = ML_MOMENT.search(regel)
        if not mo:
            continue
        start = _fmt(mo.group(2), mo.group(1), mo.group(3), mo.group(4), mo.group(5), aftrap)
        if not start:
            continue
        kop = m.group(1).lower()
        if kop.startswith("plus"):
            fases.append(["seizoen", start, "Plus-seizoenkaarthouders"])
        elif kop.startswith("season"):
            fases.append(["seizoen", start, "Seizoenkaarthouders"])
        elif kop.startswith("milan club"):
            fases.append(["lid", start, "Milan Club-leden"])
        else:
            fases.append(["vrij", start, "Vrije verkoop"])
    if not fases:
        return None
    comp = next((c for sleutel, c in ML_COMP if sleutel in tekst[:1500].lower()), "Serie A")
    noot = MAX4 if re.search(r"up to four tickets", deel, re.I) else ""
    return wedstrijd(club, naam(k.group(1)), comp, aftrap, fases=sorted(fases, key=lambda f: f[1]), noot=noot, bron=bron)


def haal_milan_artikelen():
    testmap = os.environ.get("MILAN_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas("https://www.acmilan.com/en/news/articles/ticketing", r"/news/articles/ticketing/\d{4}-\d{2}-\d{2}/", 12, testmap):
        w = parse_milan_artikel(tekst, "milan", adres)
        if w:
            uit.append(w)
    return uit


# --- Inter: 'PHASE 1 – FULL SEASON TICKET HOLDERS' + datum en tijd in de regels eronder
IN_TEGEN = re.compile(r"Inter will (?:host|face)\s+(.+?)\s+at the", re.I)
IN_AF1 = re.compile(r"Kick-off is at\s+(\d{1,2}):(\d{2})\s*CET on\s+(?:" + DAG + r"\s+)?(\d{1,2})\s+(" + MND + r")(?:\s+(\d{4}))?", re.I)
IN_AF2 = re.compile(r"on\s+(?:" + DAG + r"\s+)?(\d{1,2})\s+(" + MND + r")(?:\s+(\d{4}))?\s+at\s+(\d{1,2}):(\d{2})\s*CET", re.I)
IN_KOP = re.compile(r"^\s*(?:PHASE\s*\d+\s*[–-]\s*([^\n]+)|(GENERAL SALE))\s*$", re.M)
IN_DATUM = re.compile(r"(\d{1,2})\s+(" + MND + r")\b")
IN_TIJD = re.compile(r"(\d{1,2}):(\d{2})")


def _label_inter(titel):
    s = titel.lower()
    if "interista" in s:
        return "lid", "INTERISTA-leden"
    if "promo" in s or "bought" in s:
        return "lid", "Kopers van eerdere thuiswedstrijden (promo)"
    if "season" in s and "club" in s and "plus" in s:
        return "seizoen", "Plus-seizoenkaarthouders en Inter Club Plus-leden"
    if "season" in s and "club" in s and "base" in s:
        return "seizoen", "Base-seizoenkaarthouders en Inter Club Base-leden"
    if "full season" in s:
        return "seizoen", "Full-seizoenkaarthouders (extra tickets voor vrienden en familie)"
    if "club plus" in s:
        return "lid", "Inter Club Plus-leden"
    if "club base" in s:
        return "lid", "Inter Club Base-leden"
    if "second tier green" in s:
        return "seizoen", "Seizoenkaarthouders Tweede ring Groen"
    if "season ticket" in s:
        return "seizoen", "Seizoenkaarthouders"
    return None


def _inter_aftrap(tekst):
    m = IN_AF1.search(tekst)
    if m:
        h, mi, d, mnd, jr = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    else:
        m = IN_AF2.search(tekst)
        if not m:
            return None
        d, mnd, jr, h, mi = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    mm = EN_MAAND[mnd.lower()]
    if jr:
        return f"{int(jr):04d}-{mm:02d}-{int(d):02d}T{int(h):02d}:{mi}"
    dt = t.jaar_voor_dag(int(d), mm, int(h), int(mi))
    return t.tekst_fmt(dt) if dt else None


def parse_inter_artikel(tekst, club="inter", bron=""):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    k = IN_TEGEN.search(tekst)
    aftrap = _inter_aftrap(tekst)
    if not k or not aftrap or not _toekomst(aftrap):
        return None
    delen = list(IN_KOP.finditer(tekst))
    fases = []
    for n, m in enumerate(delen):
        einde = delen[n + 1].start() if n + 1 < len(delen) else len(tekst)
        blok = tekst[m.end():min(einde, m.end() + 700)]
        if m.group(2):
            fases += _inter_vrij(blok, aftrap)
            continue
        lab = _label_inter(m.group(1))
        if not lab:
            continue
        d, tj = IN_DATUM.search(blok), IN_TIJD.search(blok)
        if not d or not tj:
            continue
        start = _fmt(d.group(1), d.group(2), tj.group(1), tj.group(2), None, aftrap)
        if start:
            fases.append([lab[0], start, lab[1]])
    if not fases:
        return None
    comp = "Champions League" if re.search(r"champions league", tekst[:2500], re.I) else ("Supercoppa" if re.search(r"supercup|supercoppa", tekst[:2500], re.I) else "Serie A")
    noot = MAX4 if re.search(r"up to (?:4|four) tickets", tekst, re.I) else ""
    return wedstrijd(club, naam(k.group(1)), comp, aftrap, fases=sorted(fases, key=lambda f: f[1]), noot=noot, bron=bron)


def _inter_vrij(blok, aftrap):
    """Algemene verkoop: soms eerst alleen Bancomat Pay, daarna alle betaalmethoden."""
    stukken = re.split(r"(?<=[.])\s+(?=From\b)", blok.strip(), maxsplit=1)
    uit = []
    for n, stuk in enumerate(stukken):
        d, tj = IN_DATUM.search(stuk), IN_TIJD.search(stuk)
        if not d or not tj:
            continue
        start = _fmt(d.group(1), d.group(2), tj.group(1), tj.group(2), None, aftrap)
        if not start:
            continue
        if len(stukken) == 2 and "bancomat" in stukken[0].lower():
            lab = "Vrije verkoop (alleen met Bancomat Pay)" if n == 0 else "Vrije verkoop (alle betaalmethoden)"
        else:
            lab = "Vrije verkoop"
        uit.append(["vrij", start, lab])
        if len(stukken) == 1:
            break
    return uit


def haal_inter_artikelen():
    testmap = os.environ.get("INTER_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas("https://www.inter.it/en/news", r"/en/news/tickets-[a-z0-9-]+$", 12, testmap):
        w = parse_inter_artikel(tekst, "inter", adres)
        if w:
            uit.append(w)
    return uit


# --- Bayer Leverkusen: 'Tickets go on exclusive sale to season ticket holders and Club members on ... at 08:00 CET. ... to non-members on ...'
LV_TEGEN = re.compile(r"Bayer 04 host\s+(.+?)\s+at the BayArena", re.I)
LV_AF = re.compile(r"kicks off at\s+(\d{1,2}):(\d{2})\s*CET on\s+(?:" + DAG + r",?\s+)?(\d{1,2})\s+(" + MND + r")\s+(\d{4})", re.I)
LV_MOMENT = re.compile(r"(?:" + DAG + r",?\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(" + MND + r")\s+at\s+(\d{1,2}):(\d{2})\s*CET", re.I)
LV_NAMEN = {"SV 07 Elversberg": "SV Elversberg", "FC Augsburg": "FC Augsburg", "Mainz 05": "1. FSV Mainz 05"}


def parse_leverkusen_artikel(tekst, club="leverkusen", bron=""):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    k = LV_TEGEN.search(tekst)
    a = LV_AF.search(tekst)
    if not k or not a:
        return None   # zonder vaste aftrap (alleen een weekend) laten we de wedstrijd aan de lijst over
    aftrap = f"{int(a.group(5)):04d}-{EN_MAAND[a.group(4).lower()]:02d}-{int(a.group(3)):02d}T{int(a.group(1)):02d}:{a.group(2)}"
    if not _toekomst(aftrap):
        return None
    fases = []
    for zin in re.split(r"(?<=[.!])\s+", tekst[a.end():a.end() + 1500]):
        s = zin.lower()
        if "on sale" not in s and "on exclusive sale" not in s:
            continue
        mo = LV_MOMENT.search(zin)
        if not mo:
            continue
        start = _fmt(mo.group(1), mo.group(2), mo.group(3), mo.group(4), None, aftrap)
        if not start:
            continue
        if "non-member" in s:
            fases.append(["vrij", start, "Vrije verkoop (niet-leden)"])
        elif "season ticket" in s or "member" in s:
            fases.append(["lid", start, "Seizoenkaarthouders en clubleden"])
    if not fases:
        return None
    noot = MAX4 if re.search(r"ticket limit:\s*4", tekst, re.I) else ""
    return wedstrijd(club, t.mooie_naam(LV_NAMEN.get(k.group(1).strip(), k.group(1).strip())), "Bundesliga", aftrap, fases=sorted(fases, key=lambda f: f[1]), noot=noot, bron=bron)


def haal_leverkusen_artikelen():
    testmap = os.environ.get("LEVERKUSEN_DETAIL_MAP", "")
    uit = []
    for start in ("https://www.bayer04.de/en-us/page/news-centre", "https://www.bayer04.de/en-us/news/bundesliga/tickets-for-the-home-match-against-sv-07-elversberg"):
        try:
            paginas = t.haal_paginas(start, r"/news/bundesliga/tickets-for-the-home-match-against-[a-z0-9-]+$", 10, testmap)
        except Exception as fout:  # noqa: BLE001
            print(f"[leverkusen] {start}: {str(fout).splitlines()[0][:120]}")
            continue
        for adres, tekst in paginas:
            w = parse_leverkusen_artikel(tekst, "leverkusen", adres)
            if w and not any(x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
                uit.append(w)
    return uit


CLUBS = [
    ("acf-fiorentina", "ACF Fiorentina", "IT", "Fiorentina (artikelen)", "https://www.acffiorentina.com/en/news", haal_fiorentina),
    ("udinese-calcio", "Udinese Calcio", "IT", "Udinese (artikelen)", "https://www.udinese.it/eng/news", haal_udinese),
    ("rcd-espanyol", "RCD Espanyol", "ES", "Espanyol (wedstrijden)", "https://www.rcdespanyol.com/en/nextmatches", haal_espanyol),
    ("real-madrid", "Real Madrid", "ES", "Real Madrid (wedstrijden)", "https://www.realmadrid.com/en-US/tickets?filter-tickets=vip;general&filter-football=primer-equipo-masculino", haal_realmadrid),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper().replace('-', '_')}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, BEHOUD=(sleutel == "real-madrid"), haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
