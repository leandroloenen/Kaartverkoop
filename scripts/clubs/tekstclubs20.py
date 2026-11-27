"""Leesprogramma's voor de grotere clubs van Frankrijk, Portugal en België (eerste versie).

Benfica, Olympique Marseille, Lille, AS Monaco, Olympique Lyon, Sporting CP, SC Braga, FC Porto, Anderlecht en KRC Genk.
Alleen Benfica toont de volledige verkoopmomenten per groep. Bij de andere clubs lezen we de wedstrijden uit de kalender en
de status (open / nog niet open / uitverkocht); een startmoment tonen we alleen als de club dat noemt.
Alle thuiswedstrijden komen erin; uitwedstrijden slaan we over.
"""
import os
import re
import unicodedata
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from . import tekst as t

LISSABON = ZoneInfo("Europe/Lisbon")
OPEN = "Verkoop is open (startmoment niet getoond)."
NOG_NIET = "Nog niet in de verkoop."
AANMELDEN = "Nog niet in de verkoop; je kunt je aanmelden voor een bericht."
TIJD_ONBEKEND = "Aanvangstijd nog niet bevestigd."
VOORRANG = "Eerst voorrang voor abonnees en leden."
LEDEN_ALLEEN = "Alleen voor leden."

COMPETITIES = [("conference", "Conference League"), ("europa", "Europa League"), ("champions", "Champions League"),
               ("liga dos campe", "Champions League"), ("ligue 1", "Ligue 1"), ("coupe de france", "Coupe de France"),
               ("liga portugal", "Primeira Liga"), ("portuguese league", "Primeira Liga"), ("liga betclic", "Primeira Liga"),
               ("league portugal", "Primeira Liga"), ("first division a", "Jupiler Pro League"),
               ("jupiler", "Jupiler Pro League"), ("croky", "Croky Cup"), ("taça", "Taça de Portugal"), ("taca", "Taça de Portugal")]
NAMEN = {
    "PFK LEVSKI SOFIA": "Levski Sofia", "OGC NICE": "Nice", "LOSC LILLE": "Lille", "RCS ANDERLECHT": "Anderlecht", "ESTAC TROYES": "Troyes",
    "ANGERS SCO": "Angers", "STADE RENNAIS FC": "Rennes", "AS MONACO": "Monaco", "AS MONACO FC": "Monaco", "OLYMPIQUE LYONNAIS": "Lyon",
    "O. LYONNAIS": "Lyon", "O. MARSEILLE": "Marseille", "OLYMPIQUE DE MARSEILLE": "Marseille", "OLYMPIQUE MARSEILLE": "Marseille",
    "STADE BRESTOIS 29": "Brest", "AJ AUXERRE": "Auxerre", "RC LENS": "Lens", "FC LORIENT": "Lorient", "CELTA VIGO": "Celta de Vigo",
    "LE MANS FC": "Le Mans", "FC BAYERN MUNICH": "Bayern München", "VFB STUTTGART": "VfB Stuttgart", "RC STRASBOURG": "Strasbourg",
    "SK SLOVAN BRATISLAVA": "Slovan Bratislava", "PARIS FC": "Paris FC", "TOULOUSE FC": "Toulouse", "PARIS SAINT GERMAIN": "Paris Saint-Germain",
    "BRIGHTON & HOVE ALBION": "Brighton", "LINCOLN RED IMPS FC": "Lincoln Red Imps", "HEART OF MIDLOTHIAN FC": "Hearts",
    "OFI CRETE FC": "OFI Crete", "TSG 1899 HOFFENHEIM": "Hoffenheim", "SUNDERLAND AFC": "Sunderland", "R ANTWERP FC": "Antwerp",
    "SPORTING CHARLEROI": "Charleroi", "STANDARD LIÈGE": "Standard Luik", "KV KORTRIJK": "Kortrijk", "KAA GENT": "Gent",
    "KV MECHELEN": "Mechelen", "STVV": "Sint-Truiden", "KVC WESTERLO": "Westerlo", "SK BEVEREN": "Beveren", "UNION SG": "Union SG", "ESTRELA AMADORA": "Estrela da Amadora", "LE HAVRE AC": "Le Havre", "BAYER 04 LEVERKUSEN": "Bayer Leverkusen", "REAL BETIS BALOMPIÉ": "Real Betis", "SK SLAVIA PRAHA": "Slavia Praha", "SV WERDER BREMEN": "Werder Bremen", "SC PADERBORN": "SC Paderborn", "ZULTE-WAREGEM": "Zulte Waregem", "SC CHARLEROI": "Charleroi", "STANDARD DE LIÈGE": "Standard Luik", "RAAL LA LOUVIÈRE": "La Louvière", "FK BODØ/GLIMT": "Bodø/Glimt", "COMO 1907": "Como", "STADE RENNAIS": "Rennes", "AS ROMA": "AS Roma", "UNION SAINT-GILLOISE": "Union SG", "LOMMEL": "Lommel SK", "LOMMEL SK": "Lommel SK",
    "VIKTORIA PLZEŇ": "Viktoria Plzeň", "MANCHESTER UNITED FC": "Manchester United", "CS MARÍTIMO": "Marítimo", "CASA PIA AC": "Casa Pia",
    "AROUCA FC": "Arouca", "ACADÉMICO DE VISEU FC": "Académico de Viseu", "MOREIRENSE FC": "Moreirense", "GIL VICENTE FC": "Gil Vicente",
    "VITÓRIA S.C.": "Vitória SC", "FC FAMALICÃO": "Famalicão", "LIVERPOOL FC": "Liverpool", "OL – LILLESTRØM": "Lillestrøm",
    "OL – AS MONACO": "Monaco", "OL – OLYMPIQUE DE MARSEILLE": "Marseille", "OL – UNION SAINT-GILLOISE": "Union SG",
}
KLEIN = {"fc", "ac", "sc", "as", "rc", "sk", "aj", "cs", "kv", "kaa", "krc", "ogc", "sco"}
FR_MAAND = {"jan": 1, "fev": 2, "mar": 3, "avr": 4, "mai": 5, "aou": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
PT_MAAND = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
            "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def comp(naam):
    laag = naam.lower()
    for sleutel, net in COMPETITIES:
        if sleutel in laag:
            return net
    return naam.strip()


def schoon(naam):
    naam = " ".join(naam.split())
    if naam.upper() in NAMEN:
        return NAMEN[naam.upper()]
    if naam.isupper():
        return " ".join(w.lower() if w.lower() in ("de", "la", "le") and i else w.upper() if w.lower() in KLEIN else w.capitalize()
                        for i, w in enumerate(naam.split()))
    return naam


def _zonder_accent(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def maand_fr(s):
    s = _zonder_accent(s).strip(". ")
    if s.startswith("jui"):
        return 6 if s[3:4] == "n" else 7 if s[3:4] == "l" else None
    return FR_MAAND.get(s[:3])


def maand_en(s):
    return t.MAANDEN_EN.get(s.strip(".").lower()[:3])


def maand_any(s):
    return maand_en(s) or maand_fr(s)


def wedstrijd(club, tegen, comp_naam, aftrap, status=None, fases=(), bron="", tbc=False):
    """aftrap: datetime (NL-tijd) of 'YYYY-MM-DD'. status: open / leden / aanmelden / nog_niet / uitverkocht / voorrang / None."""
    a = aftrap if isinstance(aftrap, str) else t.tekst_fmt(aftrap)
    nu = info = False
    noot = ""
    if status == "open":
        nu, noot = True, OPEN
    elif status == "leden":
        nu, noot = True, LEDEN_ALLEEN
    elif status == "aanmelden":
        info, noot = True, AANMELDEN
    elif status == "nog_niet":
        info, noot = True, NOG_NIET
    elif status == "voorrang":
        info, noot = True, VOORRANG
    elif status == "uitverkocht":
        noot = "Uitverkocht."
    elif status == "resale":
        noot = "Alleen nog resale beschikbaar."
    if tbc:
        noot = (noot + " " if noot else "") + TIJD_ONBEKEND
    return {"club": club, "tegen": tegen, "comp": comp_naam, "aftrap": a,
            "fases": sorted([list(f) for f in fases], key=lambda f: f[1]), "nu": nu, "info": info, "noot": noot, "bron": bron}


def _aftrap(dag, maand, uur, minuut, tbc, zone=None, jaar=None):
    """Geef een datetime (NL-tijd) of, bij onbekende tijd, een datum-string."""
    if jaar is None:
        d = t.jaar_voor_dag(dag, maand, uur, minuut, zone or t.NL)
        if not d:
            return None
    else:
        try:
            d = datetime(jaar, maand, dag, uur, minuut, tzinfo=zone or t.NL).astimezone(t.NL)
        except ValueError:
            return None
    return d.strftime("%Y-%m-%d") if tbc else d


def _toekomst(a):
    if isinstance(a, str):
        return a >= datetime.now(t.NL).strftime("%Y-%m-%d")
    return a >= datetime.now(t.NL)


# ---------------------------------------------------------------- Franse ticketkalenders (Marseille, Lille, Monaco)
KOP = re.compile(r"^([^\n]+)\n(?:VS|vs)\n([^\n]+)\n", re.M)
DATUM = re.compile(r"(\d{1,2}) ([A-Za-zéèûôîÉ]+) (\d{4}) - (\d{2}):(\d{2})")
WEEKEND = re.compile(r"Week-end du (\d{1,2})(?:-\d{1,2})*\s+([A-Za-zéèûôî]+)")
MAANDKOP = re.compile(r"^([A-Za-zéèûô]+) (\d{4})$", re.M)


def _status_fr(blok):
    laag = blok.lower()
    if "réserver" in laag or re.search(r"^book$", blok, re.I | re.M):
        return "open"
    if "m'alerter" in laag:
        return "aanmelden"
    if re.search(r"^closed$", blok, re.I | re.M):
        return "nog_niet"
    return None


def parse_frans(tekst, club, thuisnaam, bron=""):
    """thuisnaam: hoofdletters-schrijfwijze van de club op de site, bijv. 'OLYMPIQUE DE MARSEILLE', 'LOSC', 'AS MONACO'."""
    koppen = list(KOP.finditer(tekst))
    jaarkoppen = [(m.start(), int(m.group(2))) for m in MAANDKOP.finditer(tekst) if maand_any(m.group(1))]
    uit = []
    for i, m in enumerate(koppen):
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde]
        if m.group(1).strip().upper() != thuisnaam or re.search(r"EXT[ÉE]RIEUR|D[ÉE]PLACEMENT", blok):
            continue
        cm = re.search(r"^(.+?) • (.+)$", blok, re.M)
        competitie = comp(cm.group(1)) if cm else ""
        d = DATUM.search(blok)
        tbc = bool(re.search(r"Date to be confirmed|non définitifs", blok))
        if d:
            maand = maand_any(d.group(2))
            uur, minuut = int(d.group(4)), int(d.group(5))
            tbc = tbc or (uur == 0 and minuut == 0)
            aftrap = _aftrap(int(d.group(1)), maand, uur, minuut, tbc, jaar=int(d.group(3))) if maand else None
        else:
            w = WEEKEND.search(blok)
            maand = maand_any(w.group(2)) if w else None
            if not maand:
                continue
            jaar = max([j for p, j in jaarkoppen if p < m.start()] or [datetime.now(t.NL).year])
            aftrap = _aftrap(int(w.group(1)), maand, 0, 0, True, jaar=jaar)
            tbc = True
        if not aftrap or not _toekomst(aftrap):
            continue
        uit.append(wedstrijd(club, schoon(m.group(2)), competitie, aftrap, _status_fr(blok), bron=bron, tbc=tbc))
    return uit


def parse_marseille(tekst, club="marseille", bron=""):
    return parse_frans(tekst, club, "OLYMPIQUE DE MARSEILLE", bron)


def parse_lille(tekst, club="lille", bron=""):
    return parse_frans(tekst, club, "LOSC", bron)


def parse_monaco(tekst, club="monaco", bron=""):
    return parse_frans(tekst, club, "AS MONACO", bron)


# ---------------------------------------------------------------- Lyon (de eerstvolgende thuiswedstrijden op de startpagina van de ticketshop)
LYON = re.compile(r"^[A-ZÉÛ]{3,4}\.? (\d{1,2}) ([A-ZÉÛ]{3,5})\.?\n(OL – [^\n]+)\n([^\n·]+)·[^\n]*·\s*(\d{1,2})h(\d{2})\n([^\n]*)", re.M)


def parse_lyon(tekst, club="lyon", bron=""):
    uit = []
    for m in LYON.finditer(tekst):
        maand = maand_fr(m.group(2))
        if not maand:
            continue
        aftrap = _aftrap(int(m.group(1)), maand, int(m.group(5)), int(m.group(6)), False)
        if not aftrap or not _toekomst(aftrap):
            continue
        status = "open" if "réserver" in m.group(7).lower() else None
        uit.append(wedstrijd(club, schoon(m.group(3)), comp(m.group(4)), aftrap, status, bron=bron))
    return uit


# ---------------------------------------------------------------- Benfica (volledige verkoopmomenten)
BF_KOP = re.compile(r"^([^\n]+)\n\nvs\n\n([^\n]+)\nFOOTBALL\n\n([^\n]+)\n\n([^\n]+)\n", re.M)
BF_DATUM = re.compile(r"(\d{1,2}) ([A-Za-z]{3})[a-z]*\.?,?\s*(\d{1,2}):(\d{2})\s*([ap])\.?\s*m", re.I)
BF_REGEL = re.compile(r"^(?:[A-Z][a-z]+day,? )?(\d{1,2})(?: to \d{1,2})? ([A-Z][a-z]+)(?:,|\s)*(?:at|from)?\s*(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?\s*[:,]?\s*(.*)$", re.I)
BF_MAANDEN = {**t.MAANDEN_EN, "dez": 12}


def _uur24(uur, ap):
    uur = int(uur)
    if ap.lower() == "p" and uur != 12:
        uur += 12
    if ap.lower() == "a" and uur == 12:
        uur = 0
    return uur


def _benfica_groep(zin):
    laag = zin.lower()
    if "red pass" in laag:
        return "seizoen", "Red Pass-houders"
    if "general public" in laag:
        return "vrij", "Algemene verkoop"
    if "registered" in laag or "casa benfica" in laag:
        return "clubkaart", "Geregistreerde supporters en Casa Benfica-leden" if "casa benfica" in laag else "Geregistreerde supporters"
    if "member" in laag:
        return "lid", "Leden"
    return None, None


def parse_benfica(tekst, club="benfica", bron=""):
    koppen = list(BF_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        if m.group(1).strip().upper() != "SL BENFICA":
            continue
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde]
        d = BF_DATUM.search(m.group(4))
        maand = BF_MAANDEN.get(d.group(2).lower()) if d else None
        if not maand:
            continue
        aftrap = _aftrap(int(d.group(1)), maand, _uur24(d.group(3), d.group(5)), int(d.group(4)), False, LISSABON)
        if not aftrap or not _toekomst(aftrap):
            continue
        fases = []
        for regel in blok.splitlines():
            r = BF_REGEL.match(regel.strip())
            if not r:
                continue
            maand_s = BF_MAANDEN.get(r.group(2).lower()[:3])
            groep, label = _benfica_groep(r.group(6))
            if not maand_s or not groep:
                continue
            moment = t.jaar_voor(int(r.group(1)), maand_s, _uur24(r.group(3), r.group(5)), int(r.group(4)), aftrap, LISSABON)
            if moment:
                fases.append([groep, t.tekst_fmt(moment), label])
        uitverkocht = bool(re.search(r"^Sold out$", blok, re.I | re.M))
        w = wedstrijd(club, schoon(m.group(2)), comp(m.group(3)), aftrap, "uitverkocht" if uitverkocht else None, fases, bron)
        nu_tijd = datetime.now(t.NL)
        if not uitverkocht and any(f[0] == "vrij" and datetime.fromisoformat(f[1]).replace(tzinfo=t.NL) <= nu_tijd for f in fases):
            w["nu"] = True
        if not fases and not uitverkocht:
            w["info"], w["noot"] = True, NOG_NIET
        uit.append(w)
    return uit


# ---------------------------------------------------------------- Sporting CP (status per wedstrijd)
SP_DATUM = re.compile(r"^(?:[A-Za-zçãéÇ-]+, )?(\d{1,2}) de ([A-Za-zçÇ]+)$", re.M)


def parse_sporting(tekst, club="sporting", bron=""):
    koppen = list(SP_DATUM.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        maand = PT_MAAND.get(m.group(2).lower())
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde]
        r = re.search(r"Futebol \| ([^\n]+)\n(\d{1,2}):(\d{2})\n([^\n]+)\n([^\n]+)\n([^\n]*)", blok)
        if not maand or not r or r.group(4).strip().upper() != "SPORTING CP" or "jogo fora" in blok.lower():
            continue
        aftrap = _aftrap(int(m.group(1)), maand, int(r.group(2)), int(r.group(3)), False, LISSABON)
        if not aftrap or not _toekomst(aftrap):
            continue
        s = r.group(6).lower()
        status = "nog_niet" if "breve" in s else "esgotado" if "esgot" in s else None
        if "comprar" in s:
            status = "leden" if "exclusivo sócios" in blok.lower() else "open"
        uit.append(wedstrijd(club, schoon(r.group(5)), comp(r.group(1)), aftrap, "uitverkocht" if status == "esgotado" else status, bron=bron))
    return uit


# ---------------------------------------------------------------- SC Braga
BR_KOP = re.compile(r"Football\n\nFirst team\n\n([^\n]+)\n\n([^\n]+)\n\n([A-Z][a-z]{2}) (\d{1,2}), (\d{4}), (\d{2}):(\d{2})\n\n[^\n]*\n\n([^\n]*)\n([^\n]*)")


def parse_braga(tekst, club="braga", bron=""):
    uit = []
    for m in BR_KOP.finditer(tekst):
        if m.group(1).strip().upper() != "SC BRAGA":
            continue
        maand = maand_en(m.group(3))
        uur, minuut = int(m.group(6)), int(m.group(7))
        tbc = uur == 0 and minuut == 0
        aftrap = _aftrap(int(m.group(4)), maand, uur, minuut, tbc, LISSABON, int(m.group(5))) if maand else None
        if not aftrap or not _toekomst(aftrap):
            continue
        rest = (m.group(8) + " " + m.group(9)).lower()
        status = "open" if re.search(r"\bbuy\b|buy tickets|on sale", rest) else "nog_niet" if "coming soon" in rest else None
        uit.append(wedstrijd(club, schoon(m.group(2)), "Primeira Liga", aftrap, status, bron=bron, tbc=tbc))
    return uit


# ---------------------------------------------------------------- FC Porto (de eerstvolgende wedstrijden)
PO_RIJ = re.compile(r"^(?:([A-Z][a-z]+) (\d{1,2})|(\d{1,2}) of ([A-Z][a-z]+))\n\n[A-Za-z]+day\n\nF\n\nFootball\n\n([^\n]+)\n\n([^\n]+)\n(\d{2}):(\d{2})\n([^\n]+)\nDetails\n([^\n]*)", re.M)


def parse_porto(tekst, club="porto", bron=""):
    uit = []
    for m in PO_RIJ.finditer(tekst):
        if m.group(6).strip().upper() != "FC PORTO":
            continue
        maand = maand_en(m.group(1) or m.group(4))
        if not maand:
            continue
        aftrap = _aftrap(int(m.group(2) or m.group(3)), maand, int(m.group(7)), int(m.group(8)), False, LISSABON)
        if not aftrap or not _toekomst(aftrap):
            continue
        s = m.group(10).strip().lower()
        status = "uitverkocht" if "sold" in s else "open" if s.startswith("buy") else None
        uit.append(wedstrijd(club, schoon(m.group(9)), comp(m.group(5)), aftrap, status, bron=bron))
    return uit


# ---------------------------------------------------------------- Anderlecht
AN_KOP = re.compile(r"^(.+?) vs (.+?)\n(\d{2})/(\d{2})/(\d{4}) - (\d{2}:\d{2}|TBC)\n([^\n]+)\n", re.M)


def parse_anderlecht(tekst, club="anderlecht", bron=""):
    koppen = list(AN_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        if m.group(1).strip() != "Anderlecht":
            continue
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde]
        tbc = m.group(6) == "TBC"
        uur, minuut = (0, 0) if tbc else (int(m.group(6)[:2]), int(m.group(6)[3:]))
        aftrap = _aftrap(int(m.group(3)), int(m.group(4)), uur, minuut, tbc, jaar=int(m.group(5)))
        if not aftrap or not _toekomst(aftrap):
            continue
        blok = blok[:120]  # alleen de knoppen direct onder de wedstrijd (daarna volgen maandkoppen en de volgende wedstrijd)
        status = "voorrang" if "Abo & member prio" in blok else "open" if re.search(r"^Tickets$", blok, re.M) else "nog_niet"
        uit.append(wedstrijd(club, schoon(m.group(2)), comp(m.group(7)), aftrap, status, bron=bron, tbc=tbc))
    return uit


# ---------------------------------------------------------------- KRC Genk
GE_KOP = re.compile(r"^(?:[A-Za-z]+dag (\d{1,2})/(\d{2}) om (\d{1,2}):(\d{2})|Weekend van (\d{1,2})/(\d{2}))[^\n]*\n(?:[ \t]*\n)?([^\n]+)\nVS\n([^\n]+)\n", re.M)


def parse_genk(tekst, club="genk", bron=""):
    koppen = list(GE_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        if m.group(7).strip() != "KRC Genk":
            continue
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde]
        tbc = m.group(1) is None
        dag, maand = int(m.group(1) or m.group(5)), int(m.group(2) or m.group(6))
        uur, minuut = (0, 0) if tbc else (int(m.group(3)), int(m.group(4)))
        aftrap = _aftrap(dag, maand, uur, minuut, tbc)
        if not aftrap or not _toekomst(aftrap):
            continue
        status = "open" if "Koop tickets" in blok[:80] else "nog_niet"
        uit.append(wedstrijd(club, schoon(m.group(8)), "Jupiler Pro League", aftrap, status, bron=bron, tbc=tbc))
    return uit


# ---------------------------------------------------------------- Bayern München (aanvraagpagina van de officiële ticketshop)
BY_RIJ = re.compile(r"^FC Bayern München - ([^\n]+)\n([^\n]+)\n[A-Za-z]+, ([A-Za-z]+) (\d{1,2}), (\d{4})\nStart:\s*(\d{1,2}):(\d{2}) ?([AP])M\n", re.M)
BY_TOT = re.compile(r"requests are possible until ([A-Za-z]+) (\d{1,2})(?:st|nd|rd|th) (\d{4})(?: until (\d{1,2})(?::(\d{2}))? ?([ap])m)?", re.I)
BY_COMPS = [("bundesliga", "Bundesliga"), ("dfb", "DFB-Pokal"), ("uefa", "Champions League")]


def parse_bayern(tekst, club="bayern", bron=""):
    """Bayern verkoopt via aanvragen (loting). De pagina toont per thuiswedstrijd of aanvragen nog kan, voorbij is (overboekt) of dat er een online shop is."""
    koppen = list(BY_RIJ.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde].split("Page ")[0]
        maand = maand_en(m.group(3))
        if not maand:
            continue
        aftrap = _aftrap(int(m.group(4)), maand, _uur24(m.group(6), m.group(8).lower()), int(m.group(7)), False, jaar=int(m.group(5)))
        if not aftrap or not _toekomst(aftrap):
            continue
        laag = m.group(2).lower()
        competitie = next((n for k, n in BY_COMPS if k in laag), m.group(2).strip())
        w = wedstrijd(club, schoon(m.group(1)), competitie, aftrap, None, bron=bron)
        tot = BY_TOT.search(blok)
        if tot and maand_en(tot.group(1)):
            uur = _uur24(tot.group(4), tot.group(6).lower()) if tot.group(4) else 23
            sluit = _aftrap(int(tot.group(2)), maand_en(tot.group(1)), uur, int(tot.group(5) or 0), False, jaar=int(tot.group(3)))
            w["nu"], w["noot"] = True, "Tickets aanvragen kan nu (loting; geen vaste verkoopdatum)."
            if sluit and _toekomst(sluit):
                w["fases"] = [["vrij", t.tekst_fmt(sluit), "Aanvraagperiode sluit"]]
        elif "overbooked" in blok.lower() or "requests were possible" in blok.lower():
            w["noot"] = "Aanvraagperiode voorbij (overboekt); kaarten nu alleen nog via de Ticketmarket (doorverkoop tussen supporters)."
        elif "onlineshop" in blok.lower():
            w["nu"], w["noot"] = True, "Kaarten zijn te koop in de online shop van Bayern."
        else:
            w["info"], w["noot"] = True, "Aanvraagperiode nog niet bekend."
        if not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
            uit.append(w)
    return uit


def haal_bayern(adres, test, sleutel="bayern"):
    """De lijst heeft meerdere pagina's (vier per keer); we klikken op 'volgende pagina' tot er geen meer is. Lukt dat niet, dan houden we de eerste pagina."""
    if test:
        return parse_bayern(t.haal_tekst(adres, test).replace("\xa0", " "), sleutel, adres)
    from playwright.sync_api import sync_playwright

    teksten = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(locale="en-GB")
            page.goto(adres, wait_until="domcontentloaded", timeout=45000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:  # noqa: BLE001
                pass
            for _ in range(8):
                teksten.append(page.inner_text("body"))
                knop = page.get_by_text("go to next page", exact=False)
                if not knop.count() or not knop.first.is_visible():
                    break
                try:
                    knop.first.click(timeout=8000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:  # noqa: BLE001
                    break
                if len(teksten) > 1 and teksten[-1] == teksten[-2]:
                    break
        finally:
            browser.close()
    uit = []
    for tekst in teksten:
        for w in parse_bayern(tekst.replace("\xa0", " "), sleutel, adres):
            if not any(x["tegen"] == w["tegen"] and x["aftrap"] == w["aftrap"] for x in uit):
                uit.append(w)
    return uit


# ---------------------------------------------------------------- Arsenal (ticketpagina: per wedstrijd status van de loting)
LONDEN = ZoneInfo("Europe/London")
AR_KOP = re.compile(r"^[A-Z][a-z]{2} ([A-Z][a-z]{2}) (\d{1,2}) at (\d{2}):(\d{2})\n([^\n]+)\n([^\n]+)\n(H|A)\n", re.M)
AR_LOTING = re.compile(r"Ballot Opens\s*[A-Z][a-z]{2} ([A-Z][a-z]{2}) (\d{1,2}) at (\d{2}):(\d{2})\s*\n\s*Ballot Closes\s*[A-Z][a-z]{2} ([A-Z][a-z]{2}) (\d{1,2}) at (\d{2}):(\d{2})")
AR_NAMEN = {"MAN CITY": "Manchester City", "MAN UNITED": "Manchester United", "NEWCASTLE": "Newcastle United", "REAL MADRID CF": "Real Madrid"}


def parse_arsenal(tekst, club="arsenal", bron=""):
    """Alleen thuiswedstrijden (H). De competitie staat niet op de pagina: in het 'Arsenal Stadium' (UEFA-naam) spelen ze Europees, in het Emirates de Premier League."""
    koppen = list(AR_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        if m.group(7) != "H":
            continue
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde]
        maand = maand_en(m.group(1))
        aftrap = _aftrap(int(m.group(2)), maand, int(m.group(3)), int(m.group(4)), False, LONDEN) if maand else None
        if not aftrap or not _toekomst(aftrap):
            continue
        tegen = AR_NAMEN.get(m.group(6).strip().upper(), schoon(m.group(6)))
        competitie = "Champions League" if "Arsenal Stadium" in m.group(5) else "Premier League"
        fases = []
        l = AR_LOTING.search(blok)
        if l:
            for g, label in ((l.groups()[0:4], "Loting voor leden: aanvragen openen"), (l.groups()[4:8], "Loting sluit")):
                mo = maand_en(g[0])
                moment = t.jaar_voor(int(g[1]), mo, int(g[2]), int(g[3]), aftrap, LONDEN) if mo else None
                if moment:
                    fases.append(["lid", t.tekst_fmt(moment), label])
        w = wedstrijd(club, tegen, competitie, aftrap, None, fases, bron)
        if fases:
            w["noot"] = "Kaarten zijn alleen voor leden, via loting."
        elif "Ballot Closed" in blok:
            w["noot"] = "Loting gesloten; kaarten nu alleen nog via de Ticket Exchange (doorverkoop tussen supporters)."
        else:
            w["info"], w["noot"] = True, "Loting nog niet aangekondigd."
        uit.append(w)
    return uit


# ---------------------------------------------------------------- Union SG (kalender; de pagina toont per keer één competitie, nu de Pro League)
UN_DATUM = re.compile(r"^(?:[A-Za-z]+\.? )(\d{1,2})[./](\d{2})$")
UN_TIJD = re.compile(r"^(\d{2}):(\d{2})(?: \| .*)?$")


def parse_union_sg(tekst, club="union-sg", bron="", competitie="Jupiler Pro League"):
    """De regels van een wedstrijd staan in wisselende volgorde: soms eerst de datum (eerste wedstrijd), soms eerst de teams.
    De clubnaam die als eerste staat is de thuisploeg. 'Get tickets' hoort bij de wedstrijd die er net voor staat."""
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    start = next((i for i, r in enumerate(regels) if r == "Belgian Cup"), 0)
    eind = next((i for i, r in enumerate(regels) if r == "Ranking"), len(regels))
    regels = regels[start + 1:eind]
    teams, datum, uit, laatste = [], None, [], None
    i = 0
    while i < len(regels):
        r = regels[i]
        d = UN_DATUM.match(r)
        if d:
            tijd = next((UN_TIJD.match(x) for x in regels[i + 1:i + 3] if UN_TIJD.match(x)), None)
            datum = (int(d.group(1)), int(d.group(2)), int(tijd.group(1)) if tijd else 0, int(tijd.group(2)) if tijd else 0)
        elif r == "Union Saint-Gilloise":
            teams.append("UNION")
        elif r == "alt" and i + 1 < len(regels):
            teams.append(regels[i + 1])
            i += 1
        elif r == "Get tickets" and laatste is not None:
            laatste["nu"], laatste["info"], laatste["noot"] = True, False, OPEN
        if len(teams) == 2 and datum:
            if teams[0] == "UNION":
                dag, maand, uur, minuut = datum
                tbc = uur in (0, 1, 2)  # 01:00 en 02:00 zijn plaatsvervangers voor 'tijd nog niet bekend'
                aftrap = _aftrap(dag, maand, uur, minuut, tbc)
                if aftrap and _toekomst(aftrap):
                    laatste = wedstrijd(club, schoon(teams[1]), competitie, aftrap, "nog_niet", bron=bron, tbc=tbc)
                    uit.append(laatste)
                else:
                    laatste = None
            else:
                laatste = None
            teams, datum = [], None
        i += 1
    return uit


UNION_PAGINAS = [("https://rusg.brussels/nl/kalender?calendar-filter=869&ranking-filter=867", "Jupiler Pro League"),
                 ("https://rusg.brussels/nl/kalender?calendar-filter=868&ranking-filter=867", "Europa League"),
                 ("https://rusg.brussels/nl/kalender?calendar-filter=870&ranking-filter=867", "Croky Cup")]


def haal_union_sg(adres, test, sleutel="union-sg"):
    uit = []
    for pagina, competitie in UNION_PAGINAS:
        try:
            tekst = t.haal_tekst(pagina, test).replace("\xa0", " ")
            uit += parse_union_sg(tekst, sleutel, pagina, competitie)
        except Exception as fout:  # noqa: BLE001
            print(f"[union-sg] {competitie}: overgeslagen ({str(fout).splitlines()[0][:100]})")
        if test:
            break  # bij een test gebruiken we één bestand
    return uit


# ---------------------------------------------------------------- Club Brugge (hulppagina over de ticketverkoop; alleen het A-team)
NL_MAANDEN = {"januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7, "augustus": 8, "september": 9,
              "oktober": 10, "november": 11, "december": 12}
CB_KOP = re.compile(r"^(?:(\d{2})/(\d{2})/(\d{4})\s*[–-]\s*(\d{1,2})u(\d{2})|TBD\s*[–-]\s*TBD)\s*[–-]\s*([^–\n]+?)\s*[–-]\s*Club Brugge\s*[–-]\s*([^\n]+)$", re.M)
CB_FASE = re.compile(r"^(Abonnees|Club Members|Vrije verkoop):\s*(?:vanaf\s+)?(?:[a-z]+\s+)?(\d{1,2}) ([a-z]+) om (\d{1,2})u(\d{2})?", re.M)
CB_GROEP = {"Abonnees": ("seizoen", "Abonnees"), "Club Members": ("lid", "Club Members"), "Vrije verkoop": ("vrij", "Vrije verkoop")}


def parse_clubbrugge(tekst, club="club-brugge", bron=""):
    eind = tekst.find("Club NXT")
    if eind > 0:
        tekst = tekst[:eind]  # onder die kop staan de jeugdteams
    koppen = list(CB_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.end():einde]
        if not m.group(1):
            continue  # datum nog niet bekend: zonder datum kunnen we de wedstrijd niet plaatsen
        aftrap = _aftrap(int(m.group(1)), int(m.group(2)), int(m.group(4)), int(m.group(5)), False, jaar=int(m.group(3)))
        if not aftrap or not _toekomst(aftrap):
            continue
        fases = []
        for f in CB_FASE.finditer(blok):
            maand = NL_MAANDEN.get(f.group(3))
            moment = t.jaar_voor(int(f.group(2)), maand, int(f.group(4)), int(f.group(5) or 0), aftrap, t.NL) if maand else None
            if moment:
                fases.append([CB_GROEP[f.group(1)][0], t.tekst_fmt(moment), CB_GROEP[f.group(1)][1]])
        laag = blok.lower()
        status = "nog_niet" if "nog niet in verkoop" in laag else "open" if ("in verkoop" in laag or "beschikbaar" in laag) else None
        w = wedstrijd(club, schoon(m.group(7)), comp(m.group(6)), aftrap, None if fases else status, fases, bron)
        if "account van vóór de loting" in laag:
            w["nu"], w["noot"] = True, "Alleen voor fans met een account van vóór de loting op 27/08."
        elif fases and any(f[0] == "vrij" and datetime.fromisoformat(f[1]).replace(tzinfo=t.NL) <= datetime.now(t.NL) for f in fases):
            w["nu"] = True
        uit.append(w)
    return uit


# ---------------------------------------------------------------- Paris Saint-Germain
# De ticketsite van PSG blokkeert de onzichtbare browser (Cloudflare). Lukt het lezen niet, dan gebruiken we een tekst die jij
# zelf in scripts/handmatig/psg.txt zet (Ctrl+A, Ctrl+C op https://billetterie.psg.fr/en/schedule). Die tekst veroudert, dus ververs hem af en toe.
PSG_KOP = re.compile(r"^[^\n]+ • [^\n]+\n([^\n]+)\n\1\nvs\n([^\n]+)\n\2\n", re.M)


def parse_psg(tekst, club="psg", bron=""):
    koppen = list(PSG_KOP.finditer(tekst))
    uit = []
    for i, m in enumerate(koppen):
        if m.group(1).strip().upper() != "PARIS":
            continue
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        blok = tekst[m.start():einde]
        cm = re.match(r"([^\n]+) • ", blok)
        d = DATUM.search(blok)
        maand = maand_any(d.group(2)) if d else None
        if not maand:
            continue
        uur, minuut = int(d.group(4)), int(d.group(5))
        tbc = "Date to be confirmed" in blok
        aftrap = _aftrap(int(d.group(1)), maand, uur, minuut, tbc, jaar=int(d.group(3)))
        if not aftrap or not _toekomst(aftrap):
            continue
        laag = blok.lower()
        status = ("uitverkocht" if "sold-out" in laag or "sold out" in laag else "open" if "see offers" in laag
                  else "resale" if "tickets resale" in laag else "aanmelden" if "alert me" in laag else None)
        uit.append(wedstrijd(club, schoon(m.group(2)), comp(cm.group(1)), aftrap, status, bron=bron, tbc=tbc))
    return uit


def haal_psg(adres, test, sleutel="psg"):
    from pathlib import Path

    uit = []
    try:
        uit = parse_psg(t.haal_tekst(adres, test, "en-GB").replace("\xa0", " "), sleutel, adres)
    except Exception as fout:  # noqa: BLE001
        print(f"[psg] lezen op de site mislukt: {str(fout).splitlines()[0][:120]}")
    pad = Path(__file__).resolve().parent.parent / "handmatig" / "psg.txt"
    if not uit and not test and pad.exists():
        print("[psg] site niet leesbaar: tekst uit scripts/handmatig/psg.txt gebruikt")
        uit = parse_psg(pad.read_text(encoding="utf-8").replace("\xa0", " "), sleutel, adres + " (handmatig)")
    return uit


# ---------------------------------------------------------------- registratie
ENGELS = {"porto"}  # sites die in de taal van de browser antwoorden: daar vragen we Engels (de teksten die we kennen)


def _maak(sleutel, naam, land, adres, parser):
    test = os.environ.get(f"{sleutel.upper().replace('-', '_')}_TEKST_BESTAND", "")

    def haal_op():
        tekst = t.haal_tekst(adres, test, "en-GB" if sleutel in ENGELS else "nl-NL").replace("\xa0", " ").replace("\u202f", " ")  # harde spaties op de sites
        return parser(tekst, sleutel, adres)

    if sleutel == "bayern":
        haal_op = lambda: haal_bayern(adres, test, sleutel)  # noqa: E731
    if sleutel == "union-sg":
        haal_op = lambda: haal_union_sg(adres, test, sleutel)  # noqa: E731
    if sleutel == "psg":
        haal_op = lambda: haal_psg(adres, test, sleutel)  # noqa: E731
    return SimpleNamespace(CLUB=sleutel, NAAM=naam, PAGINA=adres, LAND=land, BEHOUD=False, haal_op=haal_op)


CLUBS = [
    # sleutel, naam, land, adres van de kalender, lezer (we gebruiken hier bewust vaste kalenderadressen en niet de startadressen uit verken_lijst.txt)
    ("benfica", "SL Benfica", "PT", "https://www.slbenfica.pt/en-us/loja/bilhetes/futebol-modalidades", parse_benfica),
    ("psg", "Paris Saint-Germain", "FR", "https://billetterie.psg.fr/en/schedule", parse_psg),
    ("club-brugge", "Club Brugge", "BE", "https://www.askclub.be/hc/nl/articles/53695700949652-Voor-welke-wedstrijden-kan-ik-tickets-kopen", parse_clubbrugge),
    ("bayern", "FC Bayern München", "DE", "https://tickets.fcbayern.com/internetverkaufanfragen/EventList.aspx", parse_bayern),
    ("arsenal", "Arsenal", "EN", "https://www.arsenal.com/tickets/men", parse_arsenal),
    ("union-sg", "Union SG", "BE", "https://rusg.brussels/nl/kalender?calendar-filter=869&ranking-filter=867", parse_union_sg),
    ("marseille", "Olympique Marseille", "FR", "https://billetterie.om.fr/fr/calendrier-equipe-premiere", parse_marseille),
    ("lille", "Lille OSC", "FR", "https://billetterie.losc.fr/en/calendar", parse_lille),
    ("monaco", "AS Monaco", "FR", "https://billetterie.asmonaco.com/en/matches", parse_monaco),
    ("lyon", "Olympique Lyon", "FR", "https://billetterie.ol.fr/", parse_lyon),
    ("sporting", "Sporting CP", "PT", "https://tickets.sporting.pt/pt", parse_sporting),
    ("braga", "SC Braga", "PT", "https://scbraga.pt/en/ticketing", parse_braga),
    ("porto", "FC Porto", "PT", "https://bilhetes.fcporto.pt/", parse_porto),
    ("anderlecht", "RSC Anderlecht", "BE", "https://www.rsca.be/en/fixture/list/20", parse_anderlecht),
    ("genk", "KRC Genk", "BE", "https://www.krcgenk.be/nl/kalender/wedstrijdkalender", parse_genk),
]

UITGEZET = {"union-sg"}  # tijdelijk uit: de tekst die de update van de Union-site leest, wijkt af van de tekst uit een gewone browser (verkeerde tegenstanders)
ALLE = [_maak(*c) for c in CLUBS if c[0] not in UITGEZET]
