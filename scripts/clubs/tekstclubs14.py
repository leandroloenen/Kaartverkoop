"""Leesprogramma's voor US Sassuolo en SSC Napoli (nieuwsartikelen over de kaartverkoop van thuiswedstrijden).

- Sassuolo: artikelen 'SASSUOLO-X: info prevendita' op de ticketnieuwspagina (alleen de mannen, geen vrouwen/Primavera/uit).
- Napoli: artikelen 'Napoli v X ticket info' op de nieuwspagina. Daarin staat alleen het begin van de verkoop (fase 1);
  de data van de latere fases staan er niet in.
Italiaanse tijden zijn gelijk aan Nederlandse tijden.
"""
import os
import re
from datetime import datetime
from types import SimpleNamespace

from . import tekst as t
from .tekstclubs import wedstrijd
from .tekstclubs12 import _jaar_voor_fase

IT_MAAND = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
            "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12}
EN_MAAND = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12}


def _toekomst(aftrap):
    return datetime.fromisoformat(aftrap[:10]).date() >= datetime.now(t.NL).date()


# ---------------------------------------------------------------- Sassuolo
SA_TEGEN = re.compile(r"Sassuolo\s*[-–]\s*([A-Za-zÀ-ÿ' .]+?)\s*,\s*gara valida", re.I)
SA_AFTRAP = re.compile(r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+alle ore\s+(\d{1,2})[:.](\d{2})", re.I)
SA_LIBERA = re.compile(r"dalle ore\s+(\d{1,2})(?:[:.](\d{2}))?\s+di\s+[a-zì]+\s+(\d{1,2})°?\s+([a-z]+)\s+inizia la vendita libera", re.I)
SA_PROMO = re.compile(r"dalle ore\s+(\d{1,2})(?:[:.](\d{2}))?\s+di\s+[a-zì]+\s+(\d{1,2})°?(?:\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre))?\s+fino alle ore\s+\d{1,2}(?:[:.]\d{2})?\s+di\s+[a-zì]+\s+\d{1,2}°?\s+([a-z]+)[^.]*abbonati", re.I)
SA_PREVENDITA = re.compile(r"prevendita prender[àa] il via\s+[a-zì]+\s+(\d{1,2})°?\s+([a-z]+)\s+alle ore\s+(\d{1,2})[:.](\d{2})", re.I)


def parse_sassuolo_artikel(tekst, club="us-sassuolo", bron="", alleen_toekomst=True):
    tekst = re.sub(r"[ \t\xa0]+", " ", tekst)
    m = SA_TEGEN.search(tekst)
    a = SA_AFTRAP.search(tekst)
    if not m or not a:
        return None
    maand = IT_MAAND[a.group(2).lower()]
    aftrap_dt = t.jaar_voor_dag(int(a.group(1)), maand, int(a.group(3)), int(a.group(4)))
    if not aftrap_dt:
        return None
    aftrap = t.tekst_fmt(aftrap_dt)
    if alleen_toekomst and not _toekomst(aftrap):
        return None
    kop = tekst[:a.end() + 200]
    comp = "Coppa Italia" if "coppa italia" in kop.lower() else "Serie A"
    fases = []

    def _fase(groep, dag, mnd_naam, uur, minuut, label):
        mnd = IT_MAAND.get((mnd_naam or "").lower())
        if not mnd:
            return
        jaar = _jaar_voor_fase(int(dag), mnd, aftrap[:10])
        fases.append([groep, f"{jaar:04d}-{mnd:02d}-{int(dag):02d}T{int(uur):02d}:{minuut or '00'}", label])

    v = SA_LIBERA.search(tekst)
    if v:
        _fase("vrij", v.group(3), v.group(4), v.group(1), v.group(2), "Vrije verkoop")
    p = SA_PROMO.search(tekst)
    if p:
        _fase("seizoen", p.group(3), p.group(4) or p.group(5), p.group(1), p.group(2), "Seizoenkaarthouders (korting op 2 tickets)")
    if not fases:
        pv = SA_PREVENDITA.search(tekst)
        if pv:
            _fase("vrij", pv.group(1), pv.group(2), pv.group(3), pv.group(4), "Vrije verkoop")
            if "abbonati" in tekst.lower():
                _fase("seizoen", pv.group(1), pv.group(2), pv.group(3), pv.group(4), "Seizoenkaarthouders (korting op 2 tickets)")
    if not fases:
        return None
    noot = "Tickets voor Tribuna Sud zijn alleen voor houders van de SassuoloCard." if re.search(r"Tribuna Sud", tekst) and re.search(r"SassuoloCard", tekst) else ""
    return wedstrijd(club, m.group(1).strip().title(), comp, aftrap, fases=fases, noot=noot, bron=bron)


def haal_sassuolo(pagina, test, sleutel="us-sassuolo"):
    testmap = os.environ.get("SASSUOLO_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/biglietteria/sassuolo-[a-z-]*info-prevendita", 8, testmap):
        w = parse_sassuolo_artikel(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- Napoli
NA_VERKOOP = re.compile(r"tickets for Napoli v ([A-Za-z.' ]+?) will go on sale at (\d{1,2})[:.](\d{2}) CEST on [A-Za-z]+ (\d{1,2}) ([A-Za-z]+) (\d{4})", re.I)
NA_AFTRAP = re.compile(r"takes place on [A-Za-z]+,? (\d{1,2}) ([A-Za-z]+) at (\d{1,2})[:.](\d{2})", re.I)


def parse_napoli_artikel(tekst, club="ssc-napoli", bron="", alleen_toekomst=True):
    v = NA_VERKOOP.search(tekst)
    a = NA_AFTRAP.search(tekst)
    if not v or not a:
        return None
    mnd_v, mnd_a = EN_MAAND.get(v.group(5).lower()), EN_MAAND.get(a.group(2).lower())
    if not mnd_v or not mnd_a:
        return None
    aftrap_dt = t.jaar_voor_dag(int(a.group(1)), mnd_a, int(a.group(3)), int(a.group(4)))
    if not aftrap_dt:
        return None
    aftrap = t.tekst_fmt(aftrap_dt)
    if alleen_toekomst and not _toekomst(aftrap):
        return None
    start = f"{int(v.group(6)):04d}-{mnd_v:02d}-{int(v.group(4)):02d}T{int(v.group(2)):02d}:{v.group(3)}"
    laag = tekst.lower()
    comp = "Champions League" if "champions league" in laag else ("Coppa Italia" if "coppa italia" in laag else "Serie A")
    fases = [["seizoen", start, "Seizoenkaarthouders (fase 1)"]]
    noot = "Daarna volgen fases voor Fidelity Card-houders, Premium Members en de vrije verkoop; de data daarvan staan niet in het bericht."
    return wedstrijd(club, v.group(1).strip(), comp, aftrap, fases=fases, noot=noot, bron=bron)


def haal_napoli(pagina, test, sleutel="ssc-napoli"):
    testmap = os.environ.get("NAPOLI_DETAIL_MAP", "")
    uit = []
    for adres, tekst in t.haal_paginas(pagina, r"/en/news/[a-z0-9-]*(?:biglietti|tickets|ticket)", 8, testmap):
        w = parse_napoli_artikel(tekst, sleutel, adres)
        if w and not any(x["tegen"] == w["tegen"] and x["aftrap"][:10] == w["aftrap"][:10] for x in uit):
            uit.append(w)
    return uit


# ---------------------------------------------------------------- aansluiting
CLUBS = [
    ("us-sassuolo", "US Sassuolo", "IT", "Sassuolo", "https://www.sassuolocalcio.it/biglietteria/news-info/", haal_sassuolo),
    ("ssc-napoli", "SSC Napoli", "IT", "SSC Napoli", "https://sscnapoli.it/en/news", haal_napoli),
]


def _maak(sleutel, naam, land, lijstnaam, standaard, haal):
    test = os.environ.get(f"{sleutel.upper().replace('-', '_')}_TEKST_BESTAND", "")
    pagina = t.adres_uit_lijst(lijstnaam, standaard)
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=pagina, LAND=land, haal_op=lambda: haal(pagina, test, sleutel))


ALLE = [_maak(*c) for c in CLUBS]
