"""Vertaalt de Nederlandse labels en notities uit data.json naar het Engels voor de Engelse versie van de site.

De leesprogramma's schrijven hun teksten in het Nederlands. Voor de Engelse pagina's vertalen we ze hier met een lijst
vaste zinnen en een aantal woordregels. Teksten die we niet kennen blijven Nederlands staan en worden aan het eind van de
bouw gemeld (zie ONBEKEND), zodat je ze hier kunt aanvullen.
"""
import re

ONBEKEND = set()

# Hele zinnen (na het weghalen van witruimte aan de randen)
ZINNEN = {
    "Verkoop is open (startmoment niet getoond).": "Sales are open (the club does not show the start time).",
    "Nu in de verkoop; startmoment onbekend.": "On sale now; start time unknown.",
    "Nu in de verkoop (de shop toont geen startdatum).": "On sale now (the shop does not show a start date).",
    "Nog niet in de verkoop.": "Not on sale yet.",
    "Nog niet in de verkoop; je kunt je aanmelden voor een bericht.": "Not on sale yet; you can sign up for a notification.",
    "In de voorverkoop (startmoment en doelgroep niet getoond).": "In presale (start time and audience not shown).",
    "Verkoopmomenten nog niet bekendgemaakt.": "Sale dates not announced yet.",
    "Uitverkocht.": "Sold out.",
    "Alleen nog resale beschikbaar.": "Only resale tickets are still available.",
    "Daarna volgt vrije verkoop zolang er kaarten zijn.": "General sale follows afterwards, as long as tickets are available.",
    "De club vermeldt alleen de dag waarop de voorverkoop begint.": "The club only states the day on which the presale starts.",
    "De club noemt alleen de dagen, geen uren. Kaarten zijn er alleen voor leden.": "The club only gives the days, not the times. Tickets are for members only.",
    "Kaarten zijn er eerst alleen voor leden.": "Tickets are first available to members only.",
    "Kaarten zijn er alleen voor leden (My Leeds). Seizoenkaarthouders hebben hun eigen plek.": "Tickets are for members only (My Leeds). Season ticket holders have their own seats.",
    "Kaarten zijn er alleen voor MyForest-leden. De hoogste lidmaatschappen kunnen als eerste kopen.": "Tickets are for MyForest members only. The highest membership levels can buy first.",
    "Kaarten voor leden; zie de ticketsite van Chelsea voor het verkoopmoment.": "Tickets for members; see the Chelsea ticket site for the sale time.",
    "De verkoop gaat per niveau van thuispunten (loyaliteitspunten).": "Sales open per level of home points (loyalty points).",
    "Staat uitgelicht op de ticketpagina; de club toont niet alle wedstrijden.": "Featured on the ticket page; the club does not show all matches.",
    "Starttijd voor leden volgens de club: 10.00 uur UK-tijd.": "Start time for members according to the club: 10.00 UK time.",
    "Verkoopmomenten volgens de club (Italiaanse tijd is gelijk aan Nederlandse tijd).": "Sale times according to the club (Italian time is the same as Dutch time).",
    "Max. 6 kaarten per lid of fan, zolang er kaarten zijn.": "Max. 6 tickets per member or fan, as long as tickets are available.",
    "Clubkaart verplicht, 1 kaart per kaart. Kidsclub: 2 kaarten per lid.": "Club card required, 1 ticket per card. Kids club: 2 tickets per member.",
    "Clubkaart verplicht, 1 kaart per kaart.": "Club card required, 1 ticket per card.",
    "Seizoenkaart: 1 kaart per kaart, max. 2 per account. Leden: 2 kaarten.": "Season ticket: 1 ticket per card, max. 2 per account. Members: 2 tickets.",
    "Club Card verplicht (geen aparte vrije verkoop).": "Club Card required (no separate general sale).",
    "Geen vrije verkoop genoemd: ook de reguliere verkoop is voor (seizoen)clubkaarthouders.": "No general sale mentioned: regular sales are also for (season) club card holders.",
    "Voorverkoop via toewijzingsregeling; geen reguliere verkoop genoemd.": "Presale through an allocation scheme; no regular sale mentioned.",
    "Feyenoord verkoopt in blokken van meerdere wedstrijden tegelijk.": "Feyenoord sells in blocks of several matches at a time.",
    "Toewijzingsregeling.": "Allocation scheme.",
    "Alleen vrije verkoop": "General sale only",
    "Mitgliederverkauf (ledenverkoop).": "Mitgliederverkauf (members' sale).",
}

# Losse woorden en delen van zinnen. Volgorde is belangrijk: lange eerst.
REGELS = [
    (r"Seizoenkaarthouders \(per wedstrijd\)", "Season ticket holders (match by match)"),
    (r"Seizoenkaarthouders \(extra kaarten\)", "Season ticket holders (extra tickets)"),
    (r"-leden\b", " members"),
    (r"\(Seizoen\)clubkaarthouders", "(Season) club card holders"),
    (r"\bSeizoenkaarthouders\b", "Season ticket holders"),
    (r"\bSeizoenkaarthouder\b", "Season ticket holder"),
    (r"\bClubkaarthouders\b", "Club card holders"),
    (r"\bClubkaarthouder\b", "Club card holder"),
    (r"\bKidsclubleden\b", "Kids club members"),
    (r"\bSupportersvereniging\b", "Supporters' association"),
    (r"\bVrije verkoop\b", "General sale"),
    (r"\bvrije verkoop\b", "general sale"),
    (r"\bgeverifieerd account\b", "verified account"),
    (r"\bStart verkoop\b", "Sale starts"),
    (r"\bVoorverkoop\b", "Presale"),
    (r"\bvoorverkoop\b", "presale"),
    (r"\bdoelgroep niet vermeld\b", "audience not stated"),
    (r"\bAanvraagvenster voor leden\b", "Application window for members"),
    (r"\bVerkoopvenster\b", "Sale window"),
    (r"\bFase (\d):", r"Phase \1:"),
    (r"loting opent voor leden die vorig seizoen (\d+)\+ thuiswedstrijden kochten", r"ballot opens for members who bought \1+ home games last season"),
    (r"loting opent voor alle leden", "ballot opens for all members"),
    (r"loting: aanvragen openen", "ballot: applications open"),
    (r"Loting voor leden: aanvragen openen", "Members' ballot: applications open"),
    (r"Loting: uitslag en aankoopvenster opent", "Ballot: results and purchase window open"),
    (r"Tweede verkoop \(leden\)", "Second sale (members)"),
    (r"Forever Blue\+ leden: loting", "Forever Blue+ members: ballot"),
    (r"Forever Blue leden: verkoopvenster", "Forever Blue members: sale window"),
    (r"wie het eerst komt, het eerst", "first come, first served"),
    (r"Leden met (\d+\+) thuispunten", r"Members with \1 home points"),
    (r"Leden met (\d+\+) thuispunt", r"Members with \1 home point"),
    (r"Leden met Cherry Tuesday \((\d+\+) thuispunten\)", r"Members: Cherry Tuesday (\1 home points)"),
    (r"Leden met eerdere aankoopgeschiedenis", "Members with a previous purchase history"),
    (r"Kopers van eerdere wedstrijden: tickets doorgeven aan nieuwe supporters", "Previous buyers: assign tickets to new supporters"),
    (r"\bLeden\b", "Members"),
    (r"\bleden\b", "members"),
    (r"\bLid\b", "Member"),
    (r"\bper houder\b", "per holder"),
    (r"\bper kaart\b", "per card"),
    (r"tussen (\d+) en (\d+) ([a-z]{3})\b", r"between \1 and \2 \3"),
    (r"\b(\d+) of (\d+) ([a-z]{3})\b", r"\1 or \2 \3"),
    (r"(\d+)\.(\d{2}) uur UK-tijd", r"\1.\2 UK time"),
    (r"\buur UK-tijd\b", "UK time"),
    (r"\bUK-tijd\b", "UK time"),
    (r"\bvoor leden\b", "for members"),
    (r"\bUitverkocht of bijna uitverkocht\.", "Sold out or almost sold out."),
    (r"\bUitverkocht\b", "Sold out"),
]

MAANDEN = {"okt": "Oct", "mrt": "Mar", "mei": "May", "jan": "Jan", "feb": "Feb", "apr": "Apr", "jun": "Jun", "jul": "Jul", "aug": "Aug",
           "sep": "Sep", "nov": "Nov", "dec": "Dec"}
NL_WOORDEN = re.compile(r"\b(het|een|voor|van|leden|lid|verkoop|kaart|kaarten|niet|alleen|geen|wordt|zijn|bij|houder|houders|uur)\b", re.I)


def vertaal(tekst):
    """Geef de Engelse versie van een Nederlandse tekst; onbekende tekst blijft staan en wordt onthouden."""
    if not tekst:
        return tekst
    kaal = tekst.strip()
    if kaal in ZINNEN:
        return ZINNEN[kaal]
    uit = kaal
    for patroon, vervanging in REGELS:
        uit = re.sub(patroon, vervanging, uit)
    # maandafkortingen die nu in een Engelse zin staan (bijvoorbeeld "between 1 and 5 okt")
    uit = re.sub(r"\b(okt|mrt|mei)\b", lambda m: MAANDEN[m.group(1)], uit)
    if uit == kaal and NL_WOORDEN.search(kaal):
        ONBEKEND.add(kaal)
    elif NL_WOORDEN.search(uit) and uit != kaal:
        ONBEKEND.add(kaal)
    return uit


def vertaal_data(data):
    """Maak een kopie van data.json met Engelse labels en notities."""
    import copy

    nieuw = copy.deepcopy(data)
    for g in nieuw.get("GROEPEN", {}).values():
        g["l"] = vertaal(g["l"])
    nieuw["TOEGANG"] = {k: vertaal(v) for k, v in nieuw.get("TOEGANG", {}).items()}
    nieuw["BANDEN"] = {"very-limited": "Very hard", "limited": "Limited", "variable": "Varies per match", "often-available": "Often general sale"}
    for w in nieuw.get("WEDSTRIJDEN", []):
        if w.get("noot"):
            w["noot"] = vertaal(w["noot"])
        for f in w.get("fases", []):
            if len(f) > 2:
                f[2] = vertaal(f[2])
    return nieuw
