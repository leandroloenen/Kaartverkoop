"""Verzamelaar voor FC Groningen: leest de tabel 'Thuiswedstrijden' op de kaartverkoopinformatie-pagina."""
import os
import re
from datetime import datetime

from . import tekst as t
from .tymes4 import schoon

CLUB = "groningen"
NAAM = "FC Groningen"
LAND = "NL"
PAGINA = "https://www.fcgroningen.nl/kaartverkoopinformatie/"
TEST = os.environ.get("GRONINGEN_TEKST_BESTAND", "")
MOMENT = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})(?:\s+(\d{1,2}):(\d{2}))?")
AANTAL = re.compile(r"(\d+)\s+per\s+\(S\)CC-houder", re.I)


def moment(cel):
    m = MOMENT.search(cel)
    if not m:
        return None, False
    uur, minuut = (int(m.group(4)), int(m.group(5))) if m.group(4) else (0, 0)
    return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), uur, minuut, tzinfo=t.NL), bool(m.group(4))


def label_voor(regeling):
    if "vrije verkoop" in regeling.lower():
        return "vrij", "Vrije verkoop"
    n = AANTAL.search(regeling)
    return "clubkaart", f"(Seizoen)clubkaarthouders, {n.group(1)} per houder" if n else "(Seizoen)clubkaarthouders"


def parse(tekst):
    uit, binnen = [], False
    for regel in tekst.splitlines():
        if regel.strip().upper().startswith("THUISWEDSTRIJDEN"):
            binnen = True
            continue
        if binnen and (regel.strip().startswith("* Reguliere") or regel.strip().upper().startswith("UITWEDSTRIJDEN")):
            break  # einde van de tabel met thuiswedstrijden
        kol = [k.strip() for k in regel.split("\t")]
        if not binnen or len(kol) < 7 or not MOMENT.search(kol[0]):
            continue
        aftrap, heeft_tijd = moment(kol[0])
        tegen = schoon(kol[1])
        tegen = {"NEC": "N.E.C."}.get(tegen, tegen)
        noot = "Toewijzingsregeling." if "toewijzing" in kol[1].lower() else ""
        fases = []
        begin, _ = moment(kol[3])
        if begin and kol[2] not in ("NTB", "-"):
            g, label = label_voor(kol[2])
            fases.append([g, t.tekst_fmt(begin), label])
        begin2, _ = moment(kol[6])
        if begin2 and kol[5] not in ("NTB", "-"):
            g, label = label_voor(kol[5])
            fases.append([g, t.tekst_fmt(begin2), label])
        info = not fases and kol[2].upper() == "NTB"
        if info:
            noot = "Verkoopmomenten nog niet bekendgemaakt (NTB)."
        uit.append({"club": CLUB, "tegen": tegen, "comp": "Eredivisie", "aftrap": t.tekst_fmt(aftrap, not heeft_tijd),
                    "fases": sorted(fases, key=lambda f: f[1]), "nu": False, "info": info, "noot": noot, "bron": PAGINA})
    return uit


def haal_op():
    return parse(t.haal_tekst(PAGINA, TEST))
