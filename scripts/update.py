"""Dagelijkse update van data.json.

Elke club heeft een eigen 'verzamelaar' in scripts/clubs/. Dit programma draait ze allemaal, voegt de
resultaten samen met wat er al in data.json staat en schrijft het bestand alleen terug als er iets
veranderd is.

Regels:
- Handmatig ingevoerde wedstrijden (zonder "auto": true) met een aftrap-TIJD blijven altijd ongemoeid.
  Dezelfde wedstrijd (zelfde club, zelfde dag) wordt dan niet nogmaals automatisch toegevoegd.
- Handmatige invoer met alleen een datum (zonder tijd) is minder nauwkeurig: die wordt vervangen door de
  automatische versie, of verwijderd als de club de wedstrijd niet meer noemt.
- Automatisch toegevoegde wedstrijden ("auto": true) worden elke dag vervangen door de nieuwste versie,
  maar verkoopfases uit eerdere dagen blijven bewaard (sommige shops tonen steeds maar één fase).
- Faalt een verzamelaar of geeft hij (bijna) niets terug, dan blijven de oude gegevens van die club staan.
"""
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clubs  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data.json"


def zonder_accenten(tekst):
    return "".join(c for c in unicodedata.normalize("NFD", tekst) if unicodedata.category(c) != "Mn").lower()


# Eén schrijfwijze per club, ook als clubs elkaar anders noemen ("PSV Eindhoven", "sc Cambuur", "N.e.c.").
NAAM_GELIJK = {"psv eindhoven": "PSV", "n.e.c.": "N.E.C.", "nec": "N.E.C.", "nec nijmegen": "N.E.C.", "n.e.c. nijmegen": "N.E.C.",
               "sc cambuur": "SC Cambuur", "cambuur": "SC Cambuur", "leipzig": "RB Leipzig", "rb leipzig": "RB Leipzig",
               "afc ajax": "Ajax", "az alkmaar": "AZ", "sc heerenveen": "SC Heerenveen", "heerenveen": "SC Heerenveen",
               "fc utrecht": "FC Utrecht", "fc twente": "FC Twente", "fc groningen": "FC Groningen",
               "borussia m'gladbach": "Borussia Mönchengladbach", "sc freiburg": "SC Freiburg", "sc telstar": "Telstar"}


def gelijke_naam(naam):
    return NAAM_GELIJK.get(zonder_accenten(naam).strip(), naam)


def sleutel(w):
    return (w["club"], zonder_accenten(w["tegen"]), w["aftrap"][:10])


def dag(w):
    return (w["club"], w["aftrap"][:10])


def voeg_fases_samen(oud, nieuw):
    """Behoud fases uit eerdere runs; een fase met dezelfde groep en naam wordt vervangen."""
    def naam_van(f):
        return f[2] if len(f) > 2 else ""

    def zelfde_fase(a, b):
        """Dezelfde fase als de groep en de dag gelijk zijn en de ene naam in de andere zit (de club of ons label is aangepast)."""
        return a[0] == b[0] and a[1][:10] == b[1][:10] and (naam_van(a) in naam_van(b) or naam_van(b) in naam_van(a))

    # Fases met het oude label 'doelgroep onbekend' hadden soms een verkeerde datum: de huidige run vervangt ze.
    def ruwe_tekst(f):
        """Oude fases waarvan het label de ruwe knoptekst is ('Verkoop start 28/10, 11:00 uur', '22-12-2026 | 9.00 uur')."""
        return bool(re.search(r"\d{1,2}[-/.]\d{1,2}[-/.,\s]|^(Verkoop start|Vanaf)", naam_van(f)))

    behouden = [f for f in oud["fases"] if not any(zelfde_fase(f, n) for n in nieuw["fases"])
                and "doelgroep onbekend" not in naam_van(f) and not ruwe_tekst(f)]
    per_fase = {(f[0], naam_van(f)): f for f in behouden}
    for f in nieuw["fases"]:
        per_fase[(f[0], naam_van(f))] = f
    return sorted(per_fase.values(), key=lambda f: f[1])


def bereken_schatting(wedstrijden):
    """Hoeveel dagen voor de wedstrijd ging de verkoop open (volgens onze eigen waarnemingen)? Per club."""
    per_club = {}
    for w in wedstrijden:
        if w.get("auto") and w.get("eerst_nu"):
            dagen = (datetime.date.fromisoformat(w["aftrap"][:10]) - datetime.date.fromisoformat(w["eerst_nu"])).days
            if dagen >= 0:
                per_club.setdefault(w["club"], []).append(dagen)
    uit = {}
    for club, lijst in per_club.items():
        lijst.sort()
        uit[club] = {"n": len(lijst), "mediaan": lijst[len(lijst) // 2], "min": lijst[0], "max": lijst[-1]}
    return uit


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    origineel = json.dumps(data, sort_keys=True)
    wedstrijden = data["WEDSTRIJDEN"]

    for module in clubs.ALLE:
        club = module.CLUB
        oud_auto = [w for w in wedstrijden if w.get("auto") and w["club"] == club]
        rest = [w for w in wedstrijden if not (w.get("auto") and w["club"] == club)]

        try:
            nieuw = module.haal_op()
        except Exception as fout:  # noqa: BLE001
            print(f"[{club}] WAARSCHUWING: ophalen mislukt ({str(fout).splitlines()[0][:150]}); oude gegevens blijven staan")
            continue
        if not nieuw:
            print(f"[{club}] WAARSCHUWING: geen wedstrijden gevonden; oude gegevens blijven staan")
            continue

        handm = {dag(w): w for w in rest if w["club"] == club}
        toe, weg = [], []
        for w in nieuw:
            w["tegen"] = gelijke_naam(w["tegen"])
            w["auto"] = True
            m = handm.get(dag(w))
            if m is not None:
                if len(m["aftrap"]) == 10:  # handmatige invoer zonder tijd is minder nauwkeurig
                    print(f"[{club}] VERVANGT handmatige invoer zonder tijd: {w['tegen']} {w['aftrap'][:10]}")
                    weg.append(m)
                else:
                    print(f"[{club}] dubbel met handmatige invoer, overgeslagen: {w['tegen']} {w['aftrap'][:10]}")
                    continue
            toe.append(w)

        if len(oud_auto) >= 4 and len(toe) < len(oud_auto) / 2:
            print(f"[{club}] WAARSCHUWING: ineens veel minder wedstrijden ({len(toe)} i.p.v. {len(oud_auto)}); oude gegevens blijven staan")
            continue

        nieuwe_dagen = {dag(w) for w in toe}
        for k, m in handm.items():  # handmatige invoer zonder tijd die de club niet meer noemt
            if len(m["aftrap"]) == 10 and k not in nieuwe_dagen and m not in weg:
                print(f"[{club}] VERWIJDERT verouderde handmatige invoer zonder tijd: {m['tegen']} op {k[1]}")
                weg.append(m)
        rest = [x for x in rest if not any(x is z for z in weg)]

        if club not in data["CLUBS"]:  # nieuwe club: ook in de clublijst van de pagina zetten
            data["CLUBS"][club] = {"naam": getattr(module, "NAAM", club), "land": getattr(module, "LAND", "NL"),
                                   "mijn": "vrij", "url": getattr(module, "PAGINA", "")}
            print(f"[{club}] nieuwe club toegevoegd aan de clublijst")

        oud_k = {sleutel(w): w for w in oud_auto}
        nieuw_k = {sleutel(w): w for w in toe}
        vandaag = datetime.date.today().isoformat()
        for k, w in nieuw_k.items():  # wanneer zagen we een wedstrijd voor het eerst te koop? (niet bij de allereerste run)
            oud = oud_k.get(k)
            if oud and oud.get("eerst_nu"):
                w["eerst_nu"] = oud["eerst_nu"]
            elif w.get("nu") and oud_auto and (oud is None or not oud.get("nu")):
                w["eerst_nu"] = vandaag
        for k in nieuw_k.keys() & oud_k.keys():
            nieuw_k[k]["fases"] = voeg_fases_samen(oud_k[k], nieuw_k[k])
        for k in nieuw_k.keys() - oud_k.keys():
            print(f"[{club}] NIEUW: {k[1]} op {k[2]}")
        for k in oud_k.keys() - nieuw_k.keys():
            print(f"[{club}] VERWIJDERD: {k[1]} op {k[2]}")
        for k in nieuw_k.keys() & oud_k.keys():
            if nieuw_k[k] != oud_k[k]:
                print(f"[{club}] GEWIJZIGD: {k[1]} op {k[2]}")
        wedstrijden = rest + toe

    data["WEDSTRIJDEN"] = wedstrijden
    data["SCHATTING"] = bereken_schatting(wedstrijden)
    if json.dumps(data, sort_keys=True) != origineel:
        data["bijgewerkt"] = datetime.date.today().isoformat()
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("data.json bijgewerkt")
    else:
        print("Geen wijzigingen")


if __name__ == "__main__":
    main()
