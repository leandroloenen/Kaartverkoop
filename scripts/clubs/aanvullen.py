"""Hulpfunctie: voeg verkoopfases uit nieuwsartikelen toe aan wedstrijden die al uit de ticketshop komen.

Een club kan maar één verzamelaar hebben (anders overschrijven ze elkaar). Daarom haalt de verzamelaar van de shop
de wedstrijden op en vullen we ze hier aan met wat de clubsite in artikelen over de kaartverkoop meldt.
"""
import unicodedata


def _kaal(naam):
    n = "".join(c for c in unicodedata.normalize("NFD", naam or "") if unicodedata.category(c) != "Mn").lower()
    for woord in ("fc ", "sc ", "sv ", "rotterdam", "den haag", "sittard", "eindhoven", "zwolle", "enschede"):
        n = n.replace(woord, "")
    return n.strip(" .")


def zelfde_tegenstander(a, b):
    a, b = _kaal(a), _kaal(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def verrijk(basis, extra):
    """Voeg fases uit 'extra' toe aan de wedstrijd in 'basis' met dezelfde tegenstander en dag. Onbekende wedstrijden slaan we over."""
    for e in extra:
        for w in basis:
            if w["aftrap"][:10] == e["aftrap"][:10] and zelfde_tegenstander(w["tegen"], e["tegen"]):
                bekend = {(f[0], f[1][:10]) for f in w["fases"]}
                nieuw = [f for f in e["fases"] if (f[0], f[1][:10]) not in bekend]
                w["fases"] = sorted(w["fases"] + nieuw, key=lambda f: f[1])
                if nieuw and w.get("noot", "").startswith("Nu in de verkoop; startmoment onbekend"):
                    w["noot"] = ""
                if e.get("bron") and not w.get("bron"):
                    w["bron"] = e["bron"]
                break
    return basis
