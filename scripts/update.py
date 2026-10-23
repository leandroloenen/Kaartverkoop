"""Dagelijkse update van data.json.

Elke club heeft een eigen 'verzamelaar' in scripts/clubs/. Deze draait ze allemaal,
voegt de resultaten samen met wat er al in data.json staat en schrijft het bestand
alleen terug als er iets veranderd is.

Regels:
- Wedstrijden die handmatig zijn ingevoerd (zonder "auto": true) blijven altijd ongemoeid.
- Wedstrijden die door een verzamelaar zijn toegevoegd krijgen "auto": true en worden
  bij de volgende run vervangen door de nieuwste versie.
- Faalt een verzamelaar of geeft hij niets terug, dan blijven de oude automatische
  gegevens van die club staan (zodat een kapotte website niets wist).
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


def voeg_fases_samen(oud, nieuw):
    """Behoud fases uit eerdere runs; een fase met dezelfde groep en naam wordt vervangen."""
    per_fase = {(f[0], f[2] if len(f) > 2 else ""): f for f in oud["fases"]}
    for f in nieuw["fases"]:
        per_fase[(f[0], f[2] if len(f) > 2 else "")] = f
    return sorted(per_fase.values(), key=lambda f: f[1])


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    origineel = json.dumps(data, sort_keys=True)
    wedstrijden = data["WEDSTRIJDEN"]

    for module in clubs.ALLE:
        club = module.CLUB
        oud_auto = [w for w in wedstrijden if w.get("auto") and w["club"] == club]
        rest = [w for w in wedstrijden if not (w.get("auto") and w["club"] == club)]
        handm = {sleutel(w): w for w in rest if w["club"] == club}

        try:
            nieuw = module.haal_op()
        except Exception as fout:  # noqa: BLE001
            print(f"[{club}] WAARSCHUWING: ophalen mislukt ({fout}); oude gegevens blijven staan")
            continue
        if not nieuw:
            print(f"[{club}] WAARSCHUWING: geen wedstrijden gevonden; oude gegevens blijven staan")
            continue

        if club not in data["CLUBS"]:  # nieuwe club: ook in de clublijst van de pagina zetten
            data["CLUBS"][club] = {"naam": getattr(module, "NAAM", club), "land": "NL", "mijn": "vrij",
                                   "url": getattr(module, "PAGINA", "")}
            print(f"[{club}] nieuwe club toegevoegd aan de clublijst")

        toe = []
        for w in nieuw:
            w["auto"] = True
            k = sleutel(w)
            if k in handm:
                if len(handm[k]["aftrap"]) == 10:  # handmatige invoer zonder tijd is minder nauwkeurig
                    print(f"[{club}] VERVANGT handmatige invoer zonder tijd: {w['tegen']} {k[2]}")
                    rest = [x for x in rest if x is not handm[k]]
                    del handm[k]
                else:
                    print(f"[{club}] dubbel met handmatige invoer, overgeslagen: {w['tegen']} {k[2]}")
                    continue
            toe.append(w)

        if len(oud_auto) >= 4 and len(toe) < len(oud_auto) / 2:
            print(f"[{club}] WAARSCHUWING: ineens veel minder wedstrijden ({len(toe)} i.p.v. {len(oud_auto)}); oude gegevens blijven staan")
            continue

        for k, w in list(handm.items()):  # handmatige invoer zonder tijd die de club niet meer noemt
            if len(w["aftrap"]) == 10 and k not in {sleutel(x) for x in toe}:
                print(f"[{club}] VERWIJDERT verouderde handmatige invoer zonder tijd: {k[1]} op {k[2]}")
                rest = [x for x in rest if x is not w]

        oud_k = {sleutel(w): w for w in oud_auto}
        nieuw_k = {sleutel(w): w for w in toe}
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
    if json.dumps(data, sort_keys=True) != origineel:
        data["bijgewerkt"] = datetime.date.today().isoformat()
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("data.json bijgewerkt")
    else:
        print("Geen wijzigingen")


if __name__ == "__main__":
    main()
