"""Bouwt de losse pagina's voor zoekmachines uit data.json: per club en per competitie, plus sitemap.xml en robots.txt.

De hoofdpagina (index.html) blijft zoals ze is. Dit programma zet er alleen zoekmachine-gegevens (titel, beschrijving) en
een lijst met links naar de subpagina's in, tussen de markeringen <!--SEO--> en <!--CLUBS-->.
Verhalen per club staan in clubs_info/<sleutel>.md (zie clubs_info/_voorbeeld.md).
"""
import datetime
import html
import json
import re
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
NL = ZoneInfo("Europe/Amsterdam")
DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"]
LANDEN = {"NL": "Nederland", "DE": "Duitsland", "ES": "Spanje", "EN": "Engeland", "IT": "Italië"}
e = html.escape
CFG = {}

CSS = """:root{--bg:#f3f1ec;--card:#fffdf8;--ink:#14213d;--mute:#5b6378;--line:#d9d5c8;--accent:#e8a500;--open:#1b7f4b}
@media (prefers-color-scheme:dark){:root{--bg:#0f1526;--card:#18203a;--ink:#eef0f7;--mute:#9aa3bd;--line:#2b3556;--accent:#f2b705;--open:#4cc38a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.55}
main{max-width:820px;margin:0 auto;padding:22px 16px 56px}a{color:var(--ink)}h1{font-size:clamp(1.7rem,5vw,2.4rem);line-height:1.2;margin:.4em 0}
h2{margin-top:1.8em}.mute{color:var(--mute)}.kaart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:10px 0}
.kaart b{font-size:1.05rem}.fase{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:4px 0;border-top:1px solid var(--line);font-size:.95rem}
.voorbij{opacity:.55}.label{display:inline-block;font-size:.8rem;font-weight:600;border:1px solid var(--line);border-radius:99px;padding:1px 9px;margin-left:6px}
.nu{color:var(--open)}nav.clubs a{display:inline-block;margin:2px 10px 2px 0}.terug{font-weight:600}footer{margin-top:3em;font-size:.85rem}"""


MENU_CSS = """.topmenu{display:flex;gap:6px;flex-wrap:wrap;align-items:center;max-width:820px;margin:0 auto;padding:12px 16px 0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
.topmenu .merk{font-weight:700;margin-right:auto;color:var(--ink);text-decoration:none}
.topmenu a.item{color:var(--ink);text-decoration:none;font-weight:600;padding:6px 14px;border-radius:99px;border:1px solid var(--line);background:var(--card)}
.topmenu a.item:hover{border-color:var(--accent)}.topmenu a.item.actief{background:var(--accent);border-color:var(--accent);color:#14213d}"""


def menu(prefix, actief=""):
    """Menu bovenaan elke pagina: Home, Tips (als er tips zijn) en Over (als die pagina bestaat)."""
    items = [("home", "Home", prefix or "./")]
    if CFG.get("tips"):
        items.append(("tips", "Tips", f"{prefix}tips/"))
    if CFG.get("email"):
        items.append(("over", "Over", f"{prefix}over/"))
    links = ""
    for k, t, h in items:
        extra = ' actief" aria-current="page' if k == actief else ""
        links += f'<a class="item{extra}" href="{h}">{t}</a>'
    return f'<nav class="topmenu" aria-label="Hoofdmenu"><a class="merk" href="{prefix or "./"}">{e(CFG.get("sitenaam", ""))}</a>{links}</nav>'


def slug(tekst):
    t = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode().lower().replace(".", "")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def aware(s):
    d = datetime.datetime.fromisoformat(s if len(s) > 10 else s + "T00:00")
    return d.replace(tzinfo=NL)


def datum_nl(s, met_tijd=True):
    d = aware(s)
    uit = f"{DAGEN[d.weekday()]} {d.day} {MAANDEN[d.month - 1]} {d.year}"
    return uit + (f" om {d:%H:%M}" if met_tijd and len(s) > 10 else "")


def mini_markdown(tekst):
    uit, lijst = [], False
    for blok in re.split(r"\n\s*\n", tekst.strip()):
        regels = [r for r in blok.splitlines() if r.strip() and not r.startswith("#") or r.startswith("##")]
        if not regels:
            continue
        if regels[0].startswith("## "):
            uit.append(f"<h3>{e(regels[0][3:].strip())}</h3>")
            regels = regels[1:]
        if not regels:
            continue
        def inline(x):
            x = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", e(x))
            # [tekst](adres): alleen https-adressen en adressen binnen de site
            return re.sub(r"\[(.+?)\]\(((?:https://|/)[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', x)
        if all(r.lstrip().startswith("- ") for r in regels):
            uit.append("<ul>" + "".join(f"<li>{inline(r.lstrip()[2:])}</li>" for r in regels) + "</ul>")
        else:
            uit.append("<p>" + inline(" ".join(r.strip() for r in regels)) + "</p>")
    return "\n".join(uit)


def lees_verhaal(pad):
    if not pad.exists():
        return {}, ""
    tekst = pad.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", tekst, re.S)
    if m:
        for regel in m.group(1).splitlines():
            k, _, v = regel.partition(":")
            meta[k.strip()] = v.strip()
        tekst = m.group(2)
    return meta, tekst


def kaartje(w, club_naam, club_url, vandaag):
    aftrap = datum_nl(w["aftrap"])
    labels = ""
    if w.get("nu"):
        labels += '<span class="label nu">Nu te koop</span>'
    if w.get("info"):
        labels += '<span class="label">Verkoopinfo volgt</span>'
    fases = ""
    for f in sorted(w.get("fases", []), key=lambda x: x[1]):
        voorbij = aware(f[1]) < vandaag
        fases += f'<div class="fase{" voorbij" if voorbij else ""}"><span>{e(f[2] if len(f) > 2 else f[0])}</span><span>{e(datum_nl(f[1]))}{" (gestart)" if voorbij else ""}</span></div>'
    noot = f'<div class="mute" style="font-size:.9rem">{e(w["noot"])}</div>' if w.get("noot") else ""
    return (f'<div class="kaart"><b>{e(club_naam)} – {e(w["tegen"])}</b>{labels}<div class="mute">{e(w["comp"])} · {e(aftrap)}</div>{fases}{noot}</div>')


def voet(prefix):
    tips = f'<a href="{prefix}tips/">Tips voor het kopen van kaarten</a> · ' if CFG.get("tips") else ""
    return (f'<p class="mute">{tips}<a href="{prefix}over/">Over deze site</a> · <a href="{prefix}privacy/">Privacyverklaring</a>'
            ' · <a href="#" onclick="window.cookieInstellingen&&cookieInstellingen();return false">Cookie-instellingen</a></p>')


def analytics_tag(prefix):
    if not CFG.get("ga"):
        return ""
    return f'<script defer src="{prefix}consent.js" data-ga="{e(CFG["ga"])}" data-privacy="{prefix}privacy/"></script>'


def pagina(titel, beschrijving, canonical, prefix, inhoud, jsonld="", nav="", actief=""):
    return f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title><meta name="description" content="{e(beschrijving)}"><link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(titel)}"><meta property="og:description" content="{e(beschrijving)}"><meta property="og:type" content="website"><meta property="og:url" content="{e(canonical)}">
<style>{CSS}\n{MENU_CSS}</style>{jsonld}{analytics_tag(prefix)}</head><body>{menu(prefix, actief)}<main>
<a class="terug" href="{prefix}">← Naar het volledige overzicht met filters</a>
{inhoud}
{nav}
<footer class="mute">{voet(prefix)}Dit overzicht is niet gelieerd aan de genoemde clubs. Controleer verkoopmomenten altijd op de officiële ticketsite van de club.</footer>
</main></body></html>"""


def contact_html():
    if CFG.get("email"):
        return f'<a href="mailto:{e(CFG["email"])}">{e(CFG["email"])}</a>'
    return "het contactadres op deze site"


def tekstpagina_over(aantal_clubs, aantal_wedstrijden, bijgewerkt):
    _, verhaal = lees_verhaal(ROOT / "pagina_info" / "over.md")
    waarom = ("<h2>Waarom deze site?</h2>" + mini_markdown(verhaal)) if verhaal.strip() else ""
    tips = '<p>Hulp nodig bij het kopen van kaarten? Lees onze <a href="../tips/">tips voor het kopen van wedstrijdkaarten</a>.</p>' if CFG.get("tips") else ""
    return f"""<h1>Over {e(CFG["sitenaam"])}</h1>
<p>{e(CFG["sitenaam"])} laat zien wanneer de kaartverkoop voor voetbalwedstrijden begint, en voor wie: seizoenkaarthouders, leden of vrije verkoop. Zo hoef je niet langs tientallen clubwebsites om te weten wanneer je moet opletten.</p>
{waarom}{tips}
<h2>Wat vind je hier?</h2>
<ul><li>Op dit moment staan er {aantal_clubs} clubs en {aantal_wedstrijden} komende thuiswedstrijden in het overzicht. Het overzicht wordt dagelijks bijgewerkt; laatst bijgewerkt op {e(datum_nl(bijgewerkt, False))}.</li>
<li>Waar een club geen startmoment bekendmaakt, laten wij zien of de verkoop al open is of nog moet beginnen. Soms staat er een schatting bij; dat staat er dan duidelijk bij.</li></ul>
<h2>Let op</h2>
<ul><li>Verkoopmomenten kunnen veranderen. Controleer ze altijd op de officiële ticketsite van de club voordat je erop rekent.</li>
<li>Wij verkopen zelf geen tickets en zijn niet gelieerd aan de genoemde clubs of competities. Namen van clubs gebruiken wij uitsluitend om te vertellen over de kaartverkoop.</li>
<li>De verhalen over clubs, steden en stadions zijn een algemene introductie. Capaciteiten, stadionnamen en kaartregels veranderen regelmatig.</li></ul>
<h2>Een fout gevonden of een club gemist?</h2>
<p>Laat het ons weten via {contact_html()}. Wij kijken er graag naar.</p>
<p><a href="../privacy/">Lees onze privacyverklaring</a>.</p>"""


def tekstpagina_privacy(bijgewerkt):
    wie = e(CFG.get("beheerder") or "de beheerder van deze site")
    return f"""<h1>Privacyverklaring</h1>
<p class="mute">Laatst bijgewerkt op {e(datum_nl(bijgewerkt, False))}</p>
<h2>Wie zijn wij?</h2>
<p>{e(CFG["sitenaam"])} wordt beheerd door {wie}. Voor vragen over privacy kun je contact opnemen via {contact_html()}.</p>
<h2>Welke gegevens verwerken wij?</h2>
<p>Op deze site kun je geen account aanmaken en geen formulieren invullen. Wij vragen je dus niet om persoonsgegevens.</p>
<ul>
<li><strong>Instellingen op je eigen apparaat.</strong> Als je bij "Mijn toegang per club" aangeeft bij welke clubs je lid bent, bewaart je browser dat op je eigen apparaat. Dat wordt niet naar ons gestuurd. Ook je keuze over cookies bewaart je browser op je eigen apparaat.</li>
<li><strong>Bezoekersstatistieken (alleen met toestemming).</strong> Als je op "Accepteren" klikt, gebruiken wij Google Analytics om te zien welke pagina's worden bezocht. Google plaatst daarvoor cookies (<code>_ga</code> en <code>_ga_…</code>) en verwerkt gegevens zoals je IP-adres, apparaat- en browsergegevens, een globale locatie en de pagina's die je bekijkt. In onze rapporten zien wij alleen samengevatte cijfers en geen IP-adressen. Klik je op "Weigeren", dan wordt Google Analytics niet geladen en meten wij niets.</li>
<li><strong>Hosting.</strong> Deze site wordt aangeboden via GitHub Pages. Om de site te kunnen tonen verwerkt GitHub technische gegevens, zoals je IP-adres, in zijn serverlogboeken. Ons domein wordt beheerd bij Cloudflare.</li>
</ul>
<h2>Waarvoor en op welke grondslag?</h2>
<ul><li>Bezoekersstatistiek: om te begrijpen hoe de site wordt gebruikt en haar te verbeteren. Grondslag: jouw toestemming.</li>
<li>Het tonen van de site (hosting): grondslag is ons gerechtvaardigd belang om de site te kunnen aanbieden.</li></ul>
<h2>Hoe lang bewaren wij gegevens?</h2>
<p>Gegevens uit Google Analytics bewaren wij maximaal {e(CFG.get("bewaartermijn") or "2 maanden")}. Daarna worden ze automatisch verwijderd.</p>
<h2>Delen en doorgifte</h2>
<p>Google en GitHub zijn gevestigd in de Verenigde Staten. Gegevens kunnen daardoor buiten de Europese Economische Ruimte worden verwerkt. Dat gebeurt op basis van waarborgen die de Europese Commissie erkent, zoals het EU-VS Data Privacy Framework of standaardcontractbepalingen. Wij verkopen geen gegevens en delen ze niet met anderen dan hier genoemd.</p>
<h2>Jouw rechten</h2>
<p>Je mag vragen om inzage, correctie of verwijdering van gegevens die wij van je hebben, en bezwaar maken tegen verwerking. Omdat wij zelf geen persoonsgegevens bijhouden, bepaalt Google bij Analytics de uitvoering. Je kunt je toestemming op elk moment intrekken via <a href="#" onclick="window.cookieInstellingen&&cookieInstellingen();return false">Cookie-instellingen</a>. Heb je een klacht? Neem dan contact met ons op, of dien een klacht in bij de Autoriteit Persoonsgegevens.</p>
<h2>Links naar andere sites</h2>
<p>Wij verwijzen naar de ticketsites van clubs. Voor die sites geldt het privacybeleid van de betreffende club.</p>"""


def main():
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    site = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    basis, sitenaam = site["basis_url"].rstrip("/"), site["sitenaam"]
    CFG.update({"ga": site.get("ga_id", "").strip(), "email": site.get("contact_email", "").strip(), "beheerder": site.get("beheerder", "").strip(),
                "sitenaam": sitenaam, "bewaartermijn": site.get("bewaartermijn", "2 maanden")})
    CFG["tips"] = any(not x.stem.startswith("_") for x in (ROOT / "tips_info").glob("*.md")) if (ROOT / "tips_info").exists() else False
    vandaag = datetime.datetime.now(NL)
    bijgewerkt = data.get("bijgewerkt", vandaag.date().isoformat())
    schatting = data.get("SCHATTING", {})

    toekomst = {}
    for w in data["WEDSTRIJDEN"]:
        if aware(w["aftrap"]).date() >= vandaag.date() and w["club"] in data["CLUBS"]:
            toekomst.setdefault(w["club"], []).append(w)
    clubs = {k: v for k, v in data["CLUBS"].items() if k in toekomst}
    slugs = {k: slug(v["naam"]) for k, v in clubs.items()}

    def nav_html(prefix):
        per_land = {}
        for k, v in sorted(clubs.items(), key=lambda kv: kv[1]["naam"]):
            per_land.setdefault(v.get("land", "NL"), []).append((k, v))
        uit = '<h2>Alle clubs</h2><nav class="clubs">'
        for land, lijst in per_land.items():
            uit += f"<p><strong>{e(LANDEN.get(land, land))}</strong><br>" + "".join(
                f'<a href="{prefix}club/{slugs[k]}/">{e(v["naam"])} tickets</a>' for k, v in lijst) + "</p>"
        return uit + "</nav>"

    pagina_urls = [basis + "/"]
    # ---------- clubpagina's
    for k, club in clubs.items():
        meta, verhaal = lees_verhaal(ROOT / "clubs_info" / f"{k}.md")
        if not verhaal:  # nog geen bestand onder de sleutel: probeer de naam van de club (bijvoorbeeld arsenal.md)
            meta, verhaal = lees_verhaal(ROOT / "clubs_info" / f"{slug(club['naam'])}.md")
        wedstrijden = sorted(toekomst[k], key=lambda w: w["aftrap"])[:12]
        naam = club["naam"]
        volgende = None
        for w in wedstrijden:
            for f in sorted(w.get("fases", []), key=lambda x: x[1]):
                if aware(f[1]) >= vandaag:
                    volgende = (w, f)
                    break
            if volgende:
                break
        if volgende:
            antwoord = f"De eerstvolgende bekende verkoopstart is {datum_nl(volgende[1][1])}: {volgende[1][2] if len(volgende[1]) > 2 else ''} voor {naam} – {volgende[0]['tegen']}."
        elif any(w.get("nu") for w in wedstrijden):
            antwoord = f"Voor een of meer thuiswedstrijden van {naam} is de verkoop al open. Zie de lijst hierboven."
        else:
            antwoord = f"Er is op dit moment geen verkoopstart voor {naam} bekend. Wij werken dit overzicht dagelijks bij."
        sc = schatting.get(k)
        if sc and sc["n"] >= 2:
            antwoord += f" Volgens onze waarnemingen opent {naam} de verkoop meestal ongeveer {sc['mediaan']} dagen voor de wedstrijd (op basis van {sc['n']} waarnemingen)."
        intro = (f"Op deze pagina zie je per thuiswedstrijd van {naam} wanneer de kaartverkoop begint, en voor wie "
                 f"(seizoenkaarthouders, leden of vrije verkoop). Laatst bijgewerkt op {datum_nl(bijgewerkt, False)}.")
        inhoud = f"<h1>{e(naam)} tickets: wanneer gaat de kaartverkoop open?</h1><p>{e(intro)}</p>"
        inhoud += "<h2>Komende wedstrijden en verkoopmomenten</h2>" + "".join(kaartje(w, naam, club.get("url", ""), vandaag) for w in wedstrijden)
        if club.get("url"):
            inhoud += f'<p>Officiële tickets koop je op <a href="{e(club["url"])}" rel="noopener">de ticketsite van {e(naam)}</a>.</p>'
        inhoud += f"<h2>Veelgestelde vragen</h2><h3>Wanneer gaat de kaartverkoop van {e(naam)} open?</h3><p>{e(antwoord)}</p>"
        if verhaal.strip():
            inhoud += "<h2>Over " + e(naam) + "</h2>" + mini_markdown(verhaal)
        url = f"{basis}/club/{slugs[k]}/"
        jsonld = ""
        if meta.get("stadion"):
            events = []
            for w in wedstrijden[:8]:
                events.append({"@type": "SportsEvent", "name": f"{naam} - {w['tegen']}", "startDate": aware(w["aftrap"]).isoformat(),
                               "eventStatus": "https://schema.org/EventScheduled", "url": url,
                               "location": {"@type": "Place", "name": meta["stadion"],
                                            "address": {"@type": "PostalAddress", "addressLocality": meta.get("stad", "")}}})
            jsonld = '<script type="application/ld+json">' + json.dumps(events, ensure_ascii=False) + "</script>"
        titel = f"{naam} tickets: kaartverkoop en verkoopmomenten | {sitenaam}"
        beschr = f"Wanneer gaan de {naam}-tickets in de verkoop? Per thuiswedstrijd de verkoopmomenten voor leden, seizoenkaarthouders en vrije verkoop. Dagelijks bijgewerkt."
        uit = ROOT / "club" / slugs[k]
        uit.mkdir(parents=True, exist_ok=True)
        (uit / "index.html").write_text(pagina(titel, beschr, url, "../../", inhoud, jsonld, nav_html("../../")), encoding="utf-8")
        pagina_urls.append(url)

    # ---------- competitiepagina's
    per_comp = {}
    for k, lijst in toekomst.items():
        for w in lijst:
            per_comp.setdefault(w["comp"], []).append((k, w))
    for comp, rijen in per_comp.items():
        if len(rijen) < 3:
            continue
        rijen.sort(key=lambda kw: kw[1]["aftrap"])
        cs = slug(comp)
        inhoud = f"<h1>{e(comp)} tickets: wanneer gaat de kaartverkoop open?</h1><p>Alle bekende verkoopmomenten voor {e(comp)}-wedstrijden op één plek, gesorteerd op datum van de wedstrijd. Laatst bijgewerkt op {e(datum_nl(bijgewerkt, False))}.</p>"
        inhoud += "".join(kaartje(w, clubs[k]["naam"], "", vandaag) for k, w in rijen[:40])
        inhoud += "<p class=\"mute\">Bekijk een club voor meer details:</p>" + "<nav class=\"clubs\">" + "".join(
            f'<a href="../../club/{slugs[k]}/">{e(clubs[k]["naam"])}</a>' for k in sorted({k for k, _ in rijen}, key=lambda x: clubs[x]["naam"])) + "</nav>"
        url = f"{basis}/competitie/{cs}/"
        titel = f"{comp} tickets: kaartverkoop en verkoopmomenten | {sitenaam}"
        beschr = f"Overzicht van de kaartverkoop voor {comp}-wedstrijden: wanneer gaan de tickets in de verkoop, voor leden of vrije verkoop? Dagelijks bijgewerkt."
        uit = ROOT / "competitie" / cs
        uit.mkdir(parents=True, exist_ok=True)
        (uit / "index.html").write_text(pagina(titel, beschr, url, "../../", inhoud, "", nav_html("../../")), encoding="utf-8")
        pagina_urls.append(url)

    # ---------- tips voor het kopen van kaarten (tips_info/*.md -> tips/<naam>/)
    tipsmap = ROOT / "tips_info"
    tipsbestanden = sorted(tipsmap.glob("*.md")) if tipsmap.exists() else []
    tipsbestanden = [p for p in tipsbestanden if not p.stem.startswith("_")]
    lijst_tips = []
    for pad in tipsbestanden:
        meta, tekst = lees_verhaal(pad)
        if not tekst.strip():
            continue
        try:
            volgorde = int(meta.get("volgorde", "99"))
        except ValueError:
            volgorde = 99
        lijst_tips.append({"slug": slug(re.sub(r"^\d+-", "", pad.stem)), "titel": meta.get("titel") or pad.stem, "beschrijving": meta.get("beschrijving", ""), "volgorde": volgorde, "tekst": tekst})
    lijst_tips.sort(key=lambda x: (x["volgorde"], x["titel"]))
    CFG["tips"] = bool(lijst_tips)
    if lijst_tips:
        def tips_nav(prefix, huidig=""):
            return ('<h2>Meer tips</h2><ul>' + "".join(f'<li><a href="{prefix}tips/{x["slug"]}/">{e(x["titel"])}</a></li>' for x in lijst_tips if x["slug"] != huidig) + "</ul>")
        intro = ("<h1>Tips voor het kopen van wedstrijdkaarten</h1><p>Elke club regelt de kaartverkoop net even anders. Op deze pagina's lees je "
                 "wat je doorgaans moet doen en waar je op moet letten, zodat je rechtstreeks bij de club kaarten kunt kopen.</p>"
                 + "".join(f'<div class="kaart"><b><a href="{x["slug"]}/">{e(x["titel"])}</a></b><div class="mute">{e(x["beschrijving"])}</div></div>' for x in lijst_tips))
        uit = ROOT / "tips"
        uit.mkdir(parents=True, exist_ok=True)
        url = f"{basis}/tips/"
        (uit / "index.html").write_text(pagina(f"Tips voor het kopen van wedstrijdkaarten | {sitenaam}",
            "Praktische tips voor het kopen van voetbaltickets: stappen, verkoopfases, waar je op moet letten en wat je doet als een wedstrijd is uitverkocht.", url, "../", intro, "", "", "tips"), encoding="utf-8")
        pagina_urls.append(url)
        for x in lijst_tips:
            uit = ROOT / "tips" / x["slug"]
            uit.mkdir(parents=True, exist_ok=True)
            url = f"{basis}/tips/{x['slug']}/"
            inhoud = f"<h1>{e(x['titel'])}</h1>" + mini_markdown(x["tekst"])
            (uit / "index.html").write_text(pagina(f"{x['titel']} | {sitenaam}", x["beschrijving"], url, "../../", inhoud, "", tips_nav("../../", x["slug"]), "tips"), encoding="utf-8")
            pagina_urls.append(url)

    # ---------- Over en Privacy
    aantal_w = sum(len(v) for v in toekomst.values())
    if CFG["email"]:
        for naam, inhoud, titel in (("over", tekstpagina_over(len(clubs), aantal_w, bijgewerkt), f"Over {sitenaam}"),
                                    ("privacy", tekstpagina_privacy(bijgewerkt), f"Privacyverklaring | {sitenaam}")):
            uit = ROOT / naam
            uit.mkdir(parents=True, exist_ok=True)
            url = f"{basis}/{naam}/"
            (uit / "index.html").write_text(pagina(titel, f"{titel}: wie wij zijn en hoe wij met gegevens omgaan.", url, "../", inhoud, "", "", "over" if naam == "over" else ""), encoding="utf-8")
            pagina_urls.append(url)
    else:
        print("LET OP: vul 'contact_email' in site.json in; zonder dat worden de pagina's Over en Privacy niet gemaakt")

    # ---------- hoofdpagina: zoekmachine-gegevens en links naar de subpagina's
    idx = ROOT / "index.html"
    if idx.exists():
        s = idx.read_text(encoding="utf-8")
        seo = (f'<!--SEO--><meta name="description" content="Wanneer gaan voetbaltickets in de verkoop? Overzicht van de kaartverkoop van clubs uit de Eredivisie, Bundesliga, La Liga en meer, per doelgroep en dagelijks bijgewerkt.">'
               f'<link rel="canonical" href="{e(basis)}/"><!--/SEO-->')
        s = re.sub(r"<!--SEO-->.*?<!--/SEO-->", lambda m: seo, s, flags=re.S) if "<!--SEO-->" in s else s.replace("</title>", "</title>" + seo, 1)
        blok = f'<!--CLUBS--><section class="rules">{nav_html("")}<footer class="mute" style="margin-top:2em">{voet("")}</footer></section><!--/CLUBS-->'
        titel_hoofd = f"{sitenaam}: wanneer gaan voetbaltickets in de verkoop?"
        s = re.sub(r"<title>.*?</title>", lambda m: f"<title>{e(titel_hoofd)}</title>", s, count=1, flags=re.S)
        mblok = f"<!--MENU--><style>{MENU_CSS}</style>{menu('', 'home')}<!--/MENU-->"
        s = re.sub(r"<!--MENU-->.*?<!--/MENU-->", lambda m: mblok, s, flags=re.S) if "<!--MENU-->" in s else s.replace("<body>", "<body>" + mblok, 1)
        tag = f"<!--GA-->{analytics_tag('')}<!--/GA-->"
        s = re.sub(r"<!--GA-->.*?<!--/GA-->", lambda m: tag, s, flags=re.S) if "<!--GA-->" in s else s.replace("</head>", tag + "</head>", 1)
        s = re.sub(r"<!--CLUBS-->.*?<!--/CLUBS-->", lambda m: blok, s, flags=re.S) if "<!--CLUBS-->" in s else s.replace("</main>", blok + "</main>", 1)
        idx.write_text(s, encoding="utf-8")

    # ---------- sitemap en robots
    lms = datetime.date.fromisoformat(bijgewerkt).isoformat()
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{e(u)}</loc><lastmod>{lms}</lastmod></url>\n" for u in pagina_urls) + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {basis}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(pagina_urls)} pagina's gebouwd ({len(clubs)} clubpagina's, {len(per_comp)} competities waarvan een deel genoeg wedstrijden heeft)")


if __name__ == "__main__":
    main()
