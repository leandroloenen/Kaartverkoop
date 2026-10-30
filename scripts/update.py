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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clubs  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data.json"


def sleutel(w):
    return (w["club"], w["tegen"], w["aftrap"][:10])


def dag(w):
    return (w["club"], w["aftrap"][:10])


def voeg_fases_samen(oud, nieuw):
    """Behoud fases uit eerdere runs; een fase met dezelfde groep en naam wordt vervangen."""
    per_fase = {(f[0], f[2] if len(f) > 2 else ""): f for f in oud["fases"]}
    for f in nieuw["fases"]:
        per_fase[(f[0], f[2] if len(f) > 2 else "")] = f
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
