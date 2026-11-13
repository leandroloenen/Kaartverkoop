"""Vertaalt de Nederlandse labels en notities uit data.json naar het Engels voor de Engelse versie van de site.

De leesprogramma's schrijven hun teksten in het Nederlands. Voor de Engelse pagina's vertalen we ze hier met een lijst
vaste zinnen en een aantal woordregels. Teksten die we niet kennen blijven Nederlands staan en worden aan het eind van de
bouw gemeld (zie ONBEKEND), zodat je ze hier kunt aanvullen.
"""
import re

ONBEKEND = set()

# Hele zinnen (na het weghalen van witruimte aan de randen)
ZINNEN = {
    "Start verkoop (doelgroep niet vermeld)": "Sales start (audience not stated)",
    "Seizoenkaarthouders (korting op 2 tickets)": "Season ticket holders (2 discounted tickets)",
    "Tickets voor Tribuna Sud zijn alleen voor houders van de SassuoloCard.": "Tribuna Sud tickets are only for SassuoloCard holders.",
    "Seizoenkaarthouders (fase 1)": "Season ticket holders (phase 1)",
    "Daarna volgen fases voor Fidelity Card-houders, Premium Members en de vrije verkoop; de data daarvan staan niet in het bericht.": "Later phases for Fidelity Card holders, Premium Members and general sale follow; their dates are not in the announcement.",
    "Bestelperiode leden opent": "Members' ordering period opens",
    "Bestelperiode leden sluit": "Members' ordering period closes",
    "Dag en tijd van de wedstrijd zijn nog niet bekend.": "Day and time of the match are not yet known.",
    "Seizoen Club Card-houders": "Season Club Card holders",
    "Betalende leden": "Paying members",
    "Club Card-houders en supportersvereniging": "Club Card holders and supporters' association",
    "Seizoenkaart- en clubkaarthouders (extra kaarten)": "Season ticket and club card holders (extra tickets)",
    "Seizoenkaarthouders hebben gratis toegang tot hun eigen plaats.": "Season ticket holders get free entry to their own seat.",
    "Start verkoop": "Sales start",
    "Kaarten zijn nu te koop voor leden en Club Card-houders.": "Tickets are on sale now for members and Club Card holders.",
    "Leden, seizoenkaarthouders en fanclubs": "Members, season ticket holders and fan clubs",
    "De ledenvoorverkoop is nu open.": "The members' presale is open now.",
    "Vrije verkoop is nu open.": "General sale is open now.",
    "Dag en tijd van de wedstrijd zijn nog niet bekend; dit is de eerste dag van het speelweekend.": "Day and time of the match are not yet known; this is the first day of the match weekend.",
    "Volgens de club start eerst een voorverkoop voor leden; de datum volgt.": "According to the club, a members' presale comes first; the date will follow.",
    "Tickets beschikbaar in de ticketshop; mogelijk eerst alleen voor leden.": "Tickets are available in the ticket shop; possibly members only at first.",
    "Seizoenkaarthouders en leden": "Season ticket holders and members",
    "Vrije verkoop": "General sale",
    "Leden": "Members",
    "Voorverkoop (beperkt)": "Limited presale",
    "Ledenvoorverkoop": "Members' presale",
    "Verkoop start (volgens de club)": "Sale starts (according to the club)",
    "Alleen leden die al vóór 1 juli lid waren, mogen kopen.": "Only members who joined before 1 July may buy.",
    "Of er vrije verkoop komt, is nog niet bekend.": "It is not yet known whether there will be a general sale.",
    "Vrije verkoop (geverifieerd account)": "General sale (verified account)",
    "Club Card-houders": "Club Card holders",
    "Leden Supportersvereniging": "Supporters' Association members",
    "Seizoenkaarthouders": "Season ticket holders",
    "Mags Member-loting (inschrijving opent)": "Mags Member ballot (entry opens)",
    "Mags Member-verkoop": "Mags Member sale",
    "Alleen voor Mags Members; seizoenkaarthouders kunnen kaarten doorsturen of wederverkopen.": "Mags Members only; season ticket holders can forward or resell tickets.",
    "Verkoopmomenten staan in een nieuwsbericht per wedstrijd en worden hier (nog) niet getoond.": "Sale dates are published in a news item per match and are not shown here (yet).",
    "Losse kaarten zijn uitverkocht; via Resale komen soms kaarten vrij.": "Single tickets are sold out; tickets sometimes become available via Resale.",
    "Losse kaarten zijn uitverkocht; via Resale komen soms kaarten vrij. Voor deze wedstrijd is een Club Card verplicht.": "Single tickets are sold out; tickets sometimes become available via Resale. A Club Card is required for this match.",
    "Losse kaarten zijn nu te koop.": "Single tickets are on sale now.",
    "Losse kaarten zijn nu te koop. Voor deze wedstrijd is een Club Card verplicht.": "Single tickets are on sale now. A Club Card is required for this match.",
    "Verkoopmomenten niet getoond.": "Sale dates not shown.",
    "Verkoopmomenten niet getoond. Voor deze wedstrijd is een Club Card verplicht.": "Sale dates not shown. A Club Card is required for this match.",
    "Verkoop start binnenkort; datum nog niet bekend.": "Sales start soon; date not known yet.",
    "Kaartverkoop nog niet gestart.": "Ticket sales have not started yet.",
    "Verkoopstatus niet getoond op de clubpagina.": "Sale status is not shown on the club's page.",
    "Abonnees Sud en Aquilotti (voorrang)": "Sud and Aquilotti season ticket holders (priority)",
    "Voor Tribuna Tevere is een Fidelity Card (Eagle of Millenovecento) nodig.": "A Fidelity Card (Eagle or Millenovecento) is required for the Tribuna Tevere.",
    "Tussenfase voor abonnees 2025/26 en Fidelity Card-houders: tijden niet getoond. Voor Tribuna Tevere is een Fidelity Card (Eagle of Millenovecento) nodig.": "Intermediate phase for 2025/26 season ticket holders and Fidelity Card holders: times not shown. A Fidelity Card (Eagle or Millenovecento) is required for the Tribuna Tevere.",
    "Verkoop is open (startmoment niet getoond).": "On sale (start time not shown).",
    "Nu in de verkoop; startmoment onbekend.": "On sale now; start time unknown.",
    "Nog niet in de verkoop; je kunt je aanmelden voor een bericht.": "Not on sale yet; you can sign up for a notification.",
    "Kaarten zijn niet vrij beschikbaar (alleen hospitality).": "Tickets are not generally available (hospitality only).",
    "Voor de Curva-vakken is een Dea Card (clubkaart) nodig.": "A Dea Card (club card) is required for the Curva sections.",
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
    "Seizoenkaarthouders (voorrang)": "Season ticket holders (priority)",
    "Supporter Card-houders (met korting)": "Supporter Card holders (discounted)",
    "Tardini Card-houders (geen seizoenkaart)": "Tardini Card holders (non-season ticket holders)",
    "Kaarten uit de voorverkoop zijn inclusief de waterbus naar Sant'Elena.": "Presale tickets include the water bus to Sant'Elena.",
    "Tijden in Nederlandse tijd (omgerekend uit Brits).": "Times are in Dutch time (converted from UK time).",
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
    (r"Supporters met boekingsgeschiedenis", "Supporters with booking history"),
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
