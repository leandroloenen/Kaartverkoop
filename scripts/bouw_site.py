"""Bouwt de losse pagina's voor zoekmachines uit data.json, in het Nederlands (hoofdmap) en in het Engels (map en/).

Per taal: een pagina per club, per competitie, een overzicht van alle clubs, tips, Over en Privacy. Daarnaast de hoofdpagina,
data_en.json (de Engelse versie van data.json), sitemap.xml (met hreflang) en robots.txt.
Teksten per club staan in clubs_info/<sleutel>.md (Nederlands) en clubs_info_en/<sleutel>.md (Engels). Hetzelfde geldt voor
tips_info en pagina_info. Een Engelse pagina zonder vertaalde tekst laat die tekst weg; er komt nooit Nederlands op een Engelse pagina.
"""
import datetime
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vertaal  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NL = ZoneInfo("Europe/Amsterdam")
DAGEN = {"nl": ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
         "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
MAANDEN = {"nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"],
           "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
LIGAS = ["Eredivisie", "Premier League", "Bundesliga", "La Liga", "Serie A", "Eerste Divisie", "Championship", "2. Bundesliga", "La Liga 2", "Ligue 1"]
MAPPEN = {"nl": {"clubs": "clubs_info", "tips": "tips_info", "pagina": "pagina_info"},
          "en": {"clubs": "clubs_info_en", "tips": "tips_info_en", "pagina": "pagina_info_en"}}
e = html.escape
CFG = {}
TAAL = "nl"
PAGINAS = []  # (taal, pad, pad in de andere taal of None): voor sitemap en hreflang

TXT = {
    "nl": {
        "home": "Home", "clubs": "Clubs", "tips": "Tips", "over": "Over", "hoofdmenu": "Hoofdmenu", "menu_open": "Menu openen", "taal_kies": "Taal kiezen",
        "terug": "← Naar het volledige overzicht met filters",
        "disclaimer": "Dit overzicht is niet gelieerd aan de genoemde clubs. Controleer verkoopmomenten altijd op de officiële ticketsite van de club.",
        "tijdnoot": "",
        "voet_tips": "Tips voor het kopen van kaarten", "voet_over": "Over deze site", "voet_privacy": "Privacyverklaring", "voet_cookie": "Cookie-instellingen",
        "nu": "Nu te koop", "info": "Verkoopinfo volgt", "gestart": " (gestart)", "om": " om ",
        "alle_clubs": "Alle clubs", "wedstrijd_1": "wedstrijd", "wedstrijd_n": "wedstrijden",
        "club_h1": "{naam} tickets: wanneer gaat de kaartverkoop open?",
        "club_intro": "Op deze pagina zie je per thuiswedstrijd van {naam} wanneer de kaartverkoop begint, en voor wie (seizoenkaarthouders, leden of vrije verkoop). Laatst bijgewerkt op {datum}.",
        "club_h2_wedstrijden": "Komende wedstrijden en verkoopmomenten",
        "club_officieel": 'Officiële tickets koop je op <a href="{url}" rel="noopener">de ticketsite van {naam}</a>.',
        "faq": "Veelgestelde vragen", "faq_q": "Wanneer gaat de kaartverkoop van {naam} open?",
        "ant_volgende": "De eerstvolgende bekende verkoopstart is {datum}: {label} voor {naam} – {tegen}.",
        "ant_open": "Voor een of meer thuiswedstrijden van {naam} is de verkoop al open. Zie de lijst hierboven.",
        "ant_geen": "Er is op dit moment geen verkoopstart voor {naam} bekend. Wij werken dit overzicht dagelijks bij.",
        "ant_schatting": " Volgens onze waarnemingen opent {naam} de verkoop meestal ongeveer {mediaan} dagen voor de wedstrijd (op basis van {n} waarnemingen).",
        "club_over": "Over {naam}",
        "club_titel": "{naam} tickets: kaartverkoop en verkoopmomenten | {site}",
        "club_beschr": "Wanneer gaan de {naam}-tickets in de verkoop? Per thuiswedstrijd de verkoopmomenten voor leden, seizoenkaarthouders en vrije verkoop. Dagelijks bijgewerkt.",
        "comp_h1": "{comp} tickets: wanneer gaat de kaartverkoop open?",
        "comp_intro": "Alle bekende verkoopmomenten voor {comp}-wedstrijden op één plek, gesorteerd op datum van de wedstrijd. Laatst bijgewerkt op {datum}.",
        "comp_meer": "Bekijk een club voor meer details:",
        "comp_titel": "{comp} tickets: kaartverkoop en verkoopmomenten | {site}",
        "comp_beschr": "Overzicht van de kaartverkoop voor {comp}-wedstrijden: wanneer gaan de tickets in de verkoop, voor leden of vrije verkoop? Dagelijks bijgewerkt.",
        "clubs_intro": "Kies een club om te zien wanneer de kaartverkoop voor de komende thuiswedstrijden begint.",
        "clubs_titel": "Alle clubs | {site}",
        "clubs_beschr": "Alle clubs op een rij: per club zie je wanneer de kaartverkoop voor de komende thuiswedstrijden begint.",
        "tips_h1": "Tips voor het kopen van wedstrijdkaarten",
        "tips_intro": "Elke club regelt de kaartverkoop net even anders. Op deze pagina's lees je wat je doorgaans moet doen en waar je op moet letten, zodat je rechtstreeks bij de club kaarten kunt kopen.",
        "tips_titel": "Tips voor het kopen van wedstrijdkaarten | {site}",
        "tips_beschr": "Praktische tips voor het kopen van voetbaltickets: stappen, verkoopfases, waar je op moet letten en wat je doet als een wedstrijd is uitverkocht.",
        "tips_meer": "Meer tips",
        "over_titel": "Over {site}", "privacy_titel": "Privacyverklaring | {site}",
        "pagina_beschr": "{titel}: wie wij zijn en hoe wij met gegevens omgaan.",
        "contact_fallback": "het contactadres op deze site",
        "onderhoud_waarschuwing": "LET OP: vul 'contact_email' in site.json in; zonder dat worden de pagina's Over en Privacy niet gemaakt",
        "home_titel": "{site}: wanneer gaan voetbaltickets in de verkoop?",
        "home_beschr": "Wanneer gaan voetbaltickets in de verkoop? Overzicht van de kaartverkoop van clubs uit de Eredivisie, Bundesliga, La Liga en meer, per doelgroep en dagelijks bijgewerkt.",
    },
    "en": {
        "home": "Home", "clubs": "Clubs", "tips": "Tips", "over": "About", "hoofdmenu": "Main menu", "menu_open": "Open menu", "taal_kies": "Choose language",
        "terug": "← Back to the full overview with filters",
        "disclaimer": "This overview is not affiliated with the clubs mentioned. Always check sale moments on the club's official ticket site.",
        "tijdnoot": "All times are Central European Time (CET/CEST), the time in the Netherlands.",
        "voet_tips": "Tips for buying tickets", "voet_over": "About this site", "voet_privacy": "Privacy policy", "voet_cookie": "Cookie settings",
        "nu": "On sale now", "info": "Sale info to follow", "gestart": " (started)", "om": " at ",
        "alle_clubs": "All clubs", "wedstrijd_1": "match", "wedstrijd_n": "matches",
        "club_h1": "{naam} tickets: when do ticket sales open?",
        "club_intro": "On this page you can see, for each home match of {naam}, when ticket sales start and for whom (season ticket holders, members or general sale). Last updated on {datum}.",
        "club_h2_wedstrijden": "Upcoming matches and sale moments",
        "club_officieel": 'You can buy official tickets on <a href="{url}" rel="noopener">the {naam} ticket site</a>.',
        "faq": "Frequently asked questions", "faq_q": "When do {naam} ticket sales open?",
        "ant_volgende": "The next known sale start is {datum}: {label} for {naam} – {tegen}.",
        "ant_open": "For one or more home matches of {naam}, sales are already open. See the list above.",
        "ant_geen": "No sale start is known for {naam} at the moment. We update this overview daily.",
        "ant_schatting": " According to our observations, {naam} usually opens sales about {mediaan} days before the match (based on {n} observations).",
        "club_over": "About {naam}",
        "club_titel": "{naam} tickets: ticket sales and sale dates | {site}",
        "club_beschr": "When do {naam} tickets go on sale? For each home match, the sale moments for members, season ticket holders and general sale. Updated daily.",
        "comp_h1": "{comp} tickets: when do ticket sales open?",
        "comp_intro": "All known sale moments for {comp} matches in one place, sorted by match date. Last updated on {datum}.",
        "comp_meer": "See a club for more details:",
        "comp_titel": "{comp} tickets: ticket sales and sale dates | {site}",
        "comp_beschr": "Overview of ticket sales for {comp} matches: when do tickets go on sale, for members or general sale? Updated daily.",
        "clubs_intro": "Choose a club to see when ticket sales for the upcoming home matches begin.",
        "clubs_titel": "All clubs | {site}",
        "clubs_beschr": "All clubs at a glance: for each club you can see when ticket sales for the upcoming home matches begin.",
        "tips_h1": "Tips for buying match tickets",
        "tips_intro": "Every club handles ticket sales a little differently. These pages explain what you usually need to do and what to watch out for, so you can buy tickets directly from the club.",
        "tips_titel": "Tips for buying match tickets | {site}",
        "tips_beschr": "Practical tips for buying football tickets: steps, sale phases, what to watch out for and what to do if a match is sold out.",
        "tips_meer": "More tips",
        "over_titel": "About {site}", "privacy_titel": "Privacy policy | {site}",
        "pagina_beschr": "{titel}: who we are and how we handle data.",
        "contact_fallback": "the contact address on this site",
        "onderhoud_waarschuwing": "NOTE: fill in 'contact_email' in site.json; without it the About and Privacy pages are not built",
        "home_titel": "{site}: when do football tickets go on sale?",
        "home_beschr": "When do football tickets go on sale? Overview of ticket sales of clubs in the Eredivisie, Bundesliga, La Liga and more, per audience and updated daily.",
    },
}


def tr(sleutel, **kw):
    s = TXT[TAAL][sleutel]
    return s.format(**kw) if kw else s


CSS = """:root{--bg:#f3f1ec;--card:#fffdf8;--ink:#14213d;--mute:#5b6378;--line:#d9d5c8;--accent:#e8a500;--open:#1b7f4b}
@media (prefers-color-scheme:dark){:root{--bg:#0f1526;--card:#18203a;--ink:#eef0f7;--mute:#9aa3bd;--line:#2b3556;--accent:#f2b705;--open:#4cc38a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.55}
main{max-width:820px;margin:0 auto;padding:22px 16px 56px}a{color:var(--ink)}h1{font-size:clamp(1.7rem,5vw,2.4rem);line-height:1.2;margin:.4em 0}
h2{margin-top:1.8em}.mute{color:var(--mute)}.kaart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:10px 0}
.kaart b{font-size:1.05rem}.fase{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:4px 0;border-top:1px solid var(--line);font-size:.95rem}
.voorbij{opacity:.55}.label{display:inline-block;font-size:.8rem;font-weight:600;border:1px solid var(--line);border-radius:99px;padding:1px 9px;margin-left:6px}
.nu{color:var(--open)}nav.clubs a{display:inline-block;margin:2px 10px 2px 0}.terug{font-weight:600}footer{margin-top:3em;font-size:.85rem}"""


MENU_CSS = """.topmenu{position:relative;display:flex;align-items:center;justify-content:space-between;gap:10px;max-width:820px;margin:0 auto;padding:12px 16px 0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
.topmenu .merk{font-weight:700;color:var(--ink);text-decoration:none;min-width:0}
.topmenu .mbtn{flex:none;display:flex;align-items:center;justify-content:center;width:42px;height:40px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
.topmenu .mbtn:hover{border-color:var(--accent)}
.topmenu .mpanel{display:none;position:absolute;right:0;top:calc(100% + 6px);min-width:190px;flex-direction:column;gap:2px;padding:6px;background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:50}
.topmenu .mpanel.open{display:flex}
.topmenu a.item{color:var(--ink);text-decoration:none;font-weight:600;padding:10px 14px;border-radius:8px}
.topmenu a.item:hover{background:var(--bg)}.topmenu a.item.actief{background:var(--accent);color:#14213d}
.compvak{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:14px 0}
.compvak h3{margin:0 0 10px;font-size:1.1rem}.compvak h3 a{color:inherit;text-decoration:none;border-bottom:2px solid var(--accent)}
.chips{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px}
.chip{display:flex;flex-direction:column;gap:2px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink);text-decoration:none}
.chip:hover{border-color:var(--accent)}.chip b{font-size:.95rem}.chip span{font-size:.8rem;color:var(--mute)}
@media (max-width:480px){.chips{grid-template-columns:1fr 1fr}}
.topmenu .rechts{display:flex;align-items:center;gap:8px}
.topmenu .dd{position:relative}
.topmenu .tbtn{display:flex;align-items:center;gap:6px;height:40px;padding:0 12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;font:inherit;font-weight:700;font-size:.9rem}
.topmenu .tbtn:hover{border-color:var(--accent)}
.topmenu .tpanel{display:none;position:absolute;right:0;top:calc(100% + 6px);min-width:150px;flex-direction:column;gap:2px;padding:6px;background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:50}
.topmenu .tpanel.open{display:flex}
.topmenu .tpanel a{color:var(--ink);text-decoration:none;font-weight:600;padding:10px 14px;border-radius:8px}
.topmenu .tpanel a:hover{background:var(--bg)}.topmenu .tpanel a.actief{background:var(--accent);color:#14213d}"""


MENU_JS = ("<script>(function(){var dd=document.querySelectorAll('.topmenu .dd');if(!dd.length)return;"
           "function z(x){dd.forEach(function(d){var p=d.querySelector('.mpanel,.tpanel'),b=d.querySelector('button');"
           "var o=(d===x)&&!p.classList.contains('open');p.classList.toggle('open',o);b.setAttribute('aria-expanded',o?'true':'false')})}"
           "dd.forEach(function(d){d.querySelector('button').addEventListener('click',function(ev){ev.stopPropagation();z(d)})});"
           "document.addEventListener('click',function(e){if(!e.target.closest('.topmenu'))z(null)});"
           "document.addEventListener('keydown',function(e){if(e.key==='Escape')z(null)})})();</script>")
MENU_ICOON = ('<svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" fill="none"/></svg>')
PIJL = '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3l4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>'


def basis_taal(taal=None):
    taal = taal or TAAL
    return CFG["basis"] + ("/en" if taal == "en" else "")


def prefix_van(pad):
    return "../" * len([x for x in pad.split("/") if x])


def taal_hrefs(pad, alt_pad, prefix):
    """Relatieve adressen van de Nederlandse en Engelse versie van deze pagina (None als er geen vertaling is)."""
    if TAAL == "nl":
        nl = (prefix + pad) or "./"
        en = f"{prefix}en/{alt_pad}" if alt_pad is not None else f"{prefix}en/"
    else:
        en = (prefix + pad) or "./"
        nl = f"{prefix}../{alt_pad}" if alt_pad is not None else f"{prefix}../"
    return nl, en


def menu(prefix, actief="", pad="", alt_pad=None):
    """Menu rechtsboven: taalknop (NL/EN) en knop met drie streepjes (Home, Clubs, Tips, Over)."""
    items = [("home", tr("home"), prefix or "./"), ("clubs", tr("clubs"), f"{prefix}club/")]
    if CFG.get("tips"):
        items.append(("tips", tr("tips"), f"{prefix}tips/"))
    if CFG.get("email"):
        items.append(("over", tr("over"), f"{prefix}over/"))
    links = ""
    for k, t, h in items:
        extra = ' actief" aria-current="page' if k == actief else ""
        links += f'<a class="item{extra}" href="{h}">{t}</a>'
    nl, en = taal_hrefs(pad, alt_pad, prefix)
    act_nl = ' class="actief" aria-current="true"' if TAAL == "nl" else ""
    act_en = ' class="actief" aria-current="true"' if TAAL == "en" else ""
    talen = (f'<a href="{nl}" hreflang="nl" lang="nl"{act_nl}>Nederlands</a>'
             f'<a href="{en}" hreflang="en" lang="en"{act_en}>English</a>')
    thuis = prefix or "./"
    return (f'<nav class="topmenu" aria-label="{tr("hoofdmenu")}"><a class="merk" href="{thuis}">{e(CFG.get("sitenaam", ""))}</a>'
            f'<div class="rechts"><div class="dd"><button class="tbtn" type="button" aria-label="{tr("taal_kies")}" aria-expanded="false">{TAAL.upper()}{PIJL}</button>'
            f'<div class="tpanel">{talen}</div></div>'
            f'<div class="dd"><button class="mbtn" type="button" aria-label="{tr("menu_open")}" aria-expanded="false">{MENU_ICOON}</button>'
            f'<div class="mpanel">{links}</div></div></div></nav>{MENU_JS}')


def slug(tekst):
    t = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode().lower().replace(".", "")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def aware(s):
    d = datetime.datetime.fromisoformat(s if len(s) > 10 else s + "T00:00")
    return d.replace(tzinfo=NL)


def datum(s, met_tijd=True):
    d = aware(s)
    uit = f"{DAGEN[TAAL][d.weekday()]} {d.day} {MAANDEN[TAAL][d.month - 1]} {d.year}"
    return uit + (f"{tr('om')}{d:%H:%M}" if met_tijd and len(s) > 10 else "")


def mini_markdown(tekst):
    uit = []
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
    aftrap = datum(w["aftrap"])
    labels = ""
    if w.get("nu"):
        labels += f'<span class="label nu">{tr("nu")}</span>'
    if w.get("info"):
        labels += f'<span class="label">{tr("info")}</span>'
    fases = ""
    for f in sorted(w.get("fases", []), key=lambda x: x[1]):
        voorbij = aware(f[1]) < vandaag
        fases += (f'<div class="fase{" voorbij" if voorbij else ""}"><span>{e(f[2] if len(f) > 2 else f[0])}</span>'
                  f'<span>{e(datum(f[1]))}{tr("gestart") if voorbij else ""}</span></div>')
    noot = f'<div class="mute" style="font-size:.9rem">{e(w["noot"])}</div>' if w.get("noot") else ""
    return (f'<div class="kaart"><b>{e(club_naam)} – {e(w["tegen"])}</b>{labels}<div class="mute">{e(w["comp"])} · {e(aftrap)}</div>{fases}{noot}</div>')


def voet(prefix):
    tips = f'<a href="{prefix}tips/">{tr("voet_tips")}</a> · ' if CFG.get("tips") else ""
    return (f'<p class="mute">{tips}<a href="{prefix}over/">{tr("voet_over")}</a> · <a href="{prefix}privacy/">{tr("voet_privacy")}</a>'
            f' · <a href="#" onclick="window.cookieInstellingen&&cookieInstellingen();return false">{tr("voet_cookie")}</a></p>')


def analytics_tag(prefix):
    if not CFG.get("ga"):
        return ""
    wortel = prefix + ("../" if TAAL == "en" else "")
    return f'<script defer src="{wortel}consent.js" data-ga="{e(CFG["ga"])}" data-privacy="{prefix}privacy/" data-lang="{TAAL}"></script>'


def hreflang_tags(pad, alt_pad):
    if alt_pad is None:
        return ""
    if TAAL == "nl":
        nl, en = f"{CFG['basis']}/{pad}", f"{CFG['basis']}/en/{alt_pad}"
    else:
        en, nl = f"{CFG['basis']}/en/{pad}", f"{CFG['basis']}/{alt_pad}"
    return (f'<link rel="alternate" hreflang="nl" href="{e(nl)}"><link rel="alternate" hreflang="en" href="{e(en)}">'
            f'<link rel="alternate" hreflang="x-default" href="{e(nl)}">')


def pagina(titel, beschrijving, pad, inhoud, jsonld="", nav="", actief="", alt_pad="=", terug=True):
    """Een volledige pagina. 'pad' is het adres binnen de taalmap (bijvoorbeeld club/ajax/); alt_pad hetzelfde in de andere taal."""
    alt = pad if alt_pad == "=" else alt_pad
    prefix = prefix_van(pad)
    canonical = f"{basis_taal()}/{pad}"
    PAGINAS.append((TAAL, pad, alt))
    terugregel = f'<a class="terug" href="{prefix or "./"}">{tr("terug")}</a>\n' if terug else ""
    tijdnoot = f'<p class="mute" style="margin-top:1.4em">{tr("tijdnoot")}</p>' if tr("tijdnoot") else ""
    return f"""<!DOCTYPE html>
<html lang="{TAAL}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title><meta name="description" content="{e(beschrijving)}"><link rel="canonical" href="{e(canonical)}">{hreflang_tags(pad, alt)}
<meta property="og:title" content="{e(titel)}"><meta property="og:description" content="{e(beschrijving)}"><meta property="og:type" content="website"><meta property="og:url" content="{e(canonical)}">
<style>{CSS}\n{MENU_CSS}</style>{jsonld}{analytics_tag(prefix)}</head><body>{menu(prefix, actief, pad, alt)}<main>
{terugregel}{inhoud}
{nav}
<footer class="mute">{voet(prefix)}{tr("disclaimer")}{tijdnoot}</footer>
</main></body></html>"""


def contact_html():
    if CFG.get("email"):
        return f'<a href="mailto:{e(CFG["email"])}">{e(CFG["email"])}</a>'
    return tr("contact_fallback")


def tekstpagina_over(aantal_clubs, aantal_wedstrijden, bijgewerkt, waarom_md):
    nm = e(CFG["sitenaam"])
    if TAAL == "nl":
        waarom = ("<h2>Waarom deze site?</h2>" + mini_markdown(waarom_md)) if waarom_md.strip() else ""
        tips = '<p>Hulp nodig bij het kopen van kaarten? Lees onze <a href="../tips/">tips voor het kopen van wedstrijdkaarten</a>.</p>' if CFG.get("tips") else ""
        return f"""<h1>Over {nm}</h1>
<p>{nm} laat zien wanneer de kaartverkoop voor voetbalwedstrijden begint, en voor wie: seizoenkaarthouders, leden of vrije verkoop. Zo hoef je niet langs tientallen clubwebsites om te weten wanneer je moet opletten.</p>
{waarom}{tips}
<h2>Wat vind je hier?</h2>
<ul><li>Op dit moment staan er {aantal_clubs} clubs en {aantal_wedstrijden} komende thuiswedstrijden in het overzicht. Het overzicht wordt dagelijks bijgewerkt; laatst bijgewerkt op {e(datum(bijgewerkt, False))}.</li>
<li>Waar een club geen startmoment bekendmaakt, laten wij zien of de verkoop al open is of nog moet beginnen. Soms staat er een schatting bij; dat staat er dan duidelijk bij.</li></ul>
<h2>Let op</h2>
<ul><li>Verkoopmomenten kunnen veranderen. Controleer ze altijd op de officiële ticketsite van de club voordat je erop rekent.</li>
<li>Wij verkopen zelf geen tickets en zijn niet gelieerd aan de genoemde clubs of competities. Namen van clubs gebruiken wij uitsluitend om te vertellen over de kaartverkoop.</li>
<li>De verhalen over clubs, steden en stadions zijn een algemene introductie. Capaciteiten, stadionnamen en kaartregels veranderen regelmatig.</li></ul>
<h2>Een fout gevonden of een club gemist?</h2>
<p>Laat het ons weten via {contact_html()}. Wij kijken er graag naar.</p>
<p><a href="../privacy/">Lees onze privacyverklaring</a>.</p>"""
    waarom = ("<h2>Why this site?</h2>" + mini_markdown(waarom_md)) if waarom_md.strip() else ""
    tips = '<p>Need help buying tickets? Read our <a href="../tips/">tips for buying match tickets</a>.</p>' if CFG.get("tips") else ""
    return f"""<h1>About {nm}</h1>
<p>{nm} shows when ticket sales for football matches start, and for whom: season ticket holders, members or general sale. That way you do not have to visit dozens of club websites to know when to pay attention.</p>
{waarom}{tips}
<h2>What can you find here?</h2>
<ul><li>At the moment the overview contains {aantal_clubs} clubs and {aantal_wedstrijden} upcoming home matches. The overview is updated daily; last updated on {e(datum(bijgewerkt, False))}.</li>
<li>Where a club does not announce a start moment, we show whether sales are already open or still to begin. Sometimes an estimate is shown; it is then clearly marked as such.</li></ul>
<h2>Please note</h2>
<ul><li>Sale moments can change. Always check them on the club's official ticket site before relying on them.</li>
<li>We do not sell tickets ourselves and are not affiliated with the clubs or competitions mentioned. We use club names solely to describe their ticket sales.</li>
<li>The stories about clubs, cities and stadiums are a general introduction. Capacities, stadium names and ticket rules change regularly.</li></ul>
<h2>Found a mistake or missing a club?</h2>
<p>Let us know via {contact_html()}. We are happy to look into it.</p>
<p><a href="../privacy/">Read our privacy policy</a>.</p>"""


def tekstpagina_privacy(bijgewerkt):
    nm = e(CFG["sitenaam"])
    cookies = '<a href="#" onclick="window.cookieInstellingen&&cookieInstellingen();return false">{}</a>'
    if TAAL == "nl":
        wie = e(CFG.get("beheerder") or "de beheerder van deze site")
        return f"""<h1>Privacyverklaring</h1>
<p class="mute">Laatst bijgewerkt op {e(datum(bijgewerkt, False))}</p>
<h2>Wie zijn wij?</h2>
<p>{nm} wordt beheerd door {wie}. Voor vragen over privacy kun je contact opnemen via {contact_html()}.</p>
<h2>Welke gegevens verwerken wij?</h2>
<p>Op deze site kun je geen account aanmaken en geen formulieren invullen. Wij vragen je dus niet om persoonsgegevens.</p>
<ul>
<li><strong>Instellingen op je eigen apparaat.</strong> Je keuze over cookies bewaart je browser op je eigen apparaat. Dat wordt niet naar ons gestuurd.</li>
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
<p>Je mag vragen om inzage, correctie of verwijdering van gegevens die wij van je hebben, en bezwaar maken tegen verwerking. Omdat wij zelf geen persoonsgegevens bijhouden, bepaalt Google bij Analytics de uitvoering. Je kunt je toestemming op elk moment intrekken via {cookies.format("Cookie-instellingen")}. Heb je een klacht? Neem dan contact met ons op, of dien een klacht in bij de Autoriteit Persoonsgegevens.</p>
<h2>Links naar andere sites</h2>
<p>Wij verwijzen naar de ticketsites van clubs. Voor die sites geldt het privacybeleid van de betreffende club.</p>"""
    wie = e(CFG.get("beheerder") or "the operator of this site")
    return f"""<h1>Privacy policy</h1>
<p class="mute">Last updated on {e(datum(bijgewerkt, False))}</p>
<h2>Who are we?</h2>
<p>{nm} is operated by {wie}. For questions about privacy you can contact us via {contact_html()}.</p>
<h2>Which data do we process?</h2>
<p>On this site you cannot create an account or fill in forms. We therefore do not ask you for personal data.</p>
<ul>
<li><strong>Settings on your own device.</strong> Your browser stores your choice about cookies on your own device. This is not sent to us.</li>
<li><strong>Visitor statistics (only with consent).</strong> If you click "Accept", we use Google Analytics to see which pages are visited. Google places cookies for this (<code>_ga</code> and <code>_ga_…</code>) and processes data such as your IP address, device and browser data, an approximate location and the pages you view. In our reports we only see summarised figures and no IP addresses. If you click "Decline", Google Analytics is not loaded and we do not measure anything.</li>
<li><strong>Hosting.</strong> This site is served through GitHub Pages. To show the site, GitHub processes technical data, such as your IP address, in its server logs. Our domain is managed at Cloudflare.</li>
</ul>
<h2>For what purpose and on what legal basis?</h2>
<ul><li>Visitor statistics: to understand how the site is used and to improve it. Legal basis: your consent.</li>
<li>Showing the site (hosting): the legal basis is our legitimate interest in being able to offer the site.</li></ul>
<h2>How long do we keep data?</h2>
<p>We keep Google Analytics data for a maximum of {e(CFG.get("bewaartermijn_en") or CFG.get("bewaartermijn") or "2 months")}. After that it is deleted automatically.</p>
<h2>Sharing and transfers</h2>
<p>Google and GitHub are based in the United States. Data may therefore be processed outside the European Economic Area. This happens on the basis of safeguards recognised by the European Commission, such as the EU-US Data Privacy Framework or standard contractual clauses. We do not sell data and do not share it with anyone other than those named here.</p>
<h2>Your rights</h2>
<p>You may ask for access to, correction or deletion of the data we hold about you, and object to processing. Because we do not keep personal data ourselves, Google carries out the request for Analytics. You can withdraw your consent at any time via {cookies.format("Cookie settings")}. Do you have a complaint? Please contact us, or file a complaint with the Dutch Data Protection Authority (Autoriteit Persoonsgegevens).</p>
<h2>Links to other sites</h2>
<p>We link to the ticket sites of clubs. The privacy policy of the club in question applies to those sites.</p>"""


def laad_tips(taal):
    """Lees de tips van een taal (tips_info of tips_info_en); geeft een lijst, gesorteerd op volgorde."""
    tipsmap = ROOT / MAPPEN[taal]["tips"]
    bestanden = [p for p in (sorted(tipsmap.glob("*.md")) if tipsmap.exists() else []) if not p.stem.startswith("_")]
    lijst = []
    for pad in bestanden:
        meta, tekst = lees_verhaal(pad)
        if not tekst.strip():
            continue
        try:
            volgorde = int(meta.get("volgorde", "99"))
        except ValueError:
            volgorde = 99
        lijst.append({"stem": pad.stem, "slug": meta.get("slug") or slug(re.sub(r"^\d+-", "", pad.stem)), "titel": meta.get("titel") or pad.stem,
                      "beschrijving": meta.get("beschrijving", ""), "volgorde": volgorde, "tekst": tekst})
    lijst.sort(key=lambda x: (x["volgorde"], x["titel"]))
    return lijst


def verhaal_voor(k, naam, taal):
    for sleutel in (k, slug(naam)):
        meta, tekst = lees_verhaal(ROOT / MAPPEN[taal]["clubs"] / f"{sleutel}.md")
        if tekst.strip():
            return meta, tekst
    return {}, ""


# Teksten op de hoofdpagina die voor de Engelse versie worden vervangen (de rest staat in het script van index.html)
INDEX_EN = [
    ('<html lang="nl">', '<html lang="en">'),
    ("<h1>Wanneer gaan de tickets in de verkoop?</h1>", "<h1>When do tickets go on sale?</h1>"),
    ("Per wedstrijd zie je onder elkaar wanneer de verkoop start voor elke doelgroep. Filter hieronder op competitie, club of datum.",
     "For every match you can see below each other when sales start for each audience. Filter below by competition, club or date. All times are Central European Time (CET/CEST)."),
    ('aria-label="Competitie"><option value="">Alle competities</option>', 'aria-label="Competition"><option value="">All competitions</option>'),
    ('aria-label="Club"><option value="">Alle clubs</option>', 'aria-label="Club"><option value="">All clubs</option>'),
    (" Toon al gestarte verkoop", " Show sales that already started"),
    ('Wedstrijd tussen <input type="date" id="fVan" aria-label="Vanaf datum"> en <input type="date" id="fTot" aria-label="Tot en met datum">',
     'Match between <input type="date" id="fVan" aria-label="From date"> and <input type="date" id="fTot" aria-label="Until date">'),
]


def bouw_taal(taal, data, tips, index_bron, vandaag, bijgewerkt):
    """Bouw alle pagina's van een taal. Nederlands komt in de hoofdmap, Engels in en/."""
    global TAAL
    TAAL = taal
    UIT = ROOT if taal == "nl" else ROOT / "en"
    ander = "en" if taal == "nl" else "nl"
    sitenaam = CFG["sitenaam"]
    CFG["tips"] = bool(tips[taal])
    schatting = data.get("SCHATTING", {})

    def schrijf(pad, inhoud_html):
        map_ = UIT / pad if pad else UIT
        map_.mkdir(parents=True, exist_ok=True)
        (map_ / "index.html").write_text(inhoud_html, encoding="utf-8")

    toekomst = {}
    for w in data["WEDSTRIJDEN"]:
        if aware(w["aftrap"]).date() >= vandaag.date() and w["club"] in data["CLUBS"]:
            toekomst.setdefault(w["club"], []).append(w)
    clubs = {k: v for k, v in data["CLUBS"].items() if k in toekomst}
    slugs = {k: slug(v["naam"]) for k, v in clubs.items()}

    def hoofdcompetitie(k):
        """De competitie van een club: de landelijke competitie als die er is, anders de competitie met de meeste wedstrijden."""
        tel = {}
        for w in toekomst[k]:
            tel[w["comp"]] = tel.get(w["comp"], 0) + 1
        liga = [c for c in tel if c in LIGAS]
        kies = liga or list(tel)
        return max(kies, key=lambda c: (tel[c], c)) if kies else "Overig"

    def nav_html(prefix):
        """Per competitie een vak met de clubs eronder."""
        per_comp_clubs = {}
        for k in clubs:
            per_comp_clubs.setdefault(hoofdcompetitie(k), []).append(k)
        tellers = {}
        for lijst in toekomst.values():
            for w in lijst:
                tellers[w["comp"]] = tellers.get(w["comp"], 0) + 1
        volgorde = sorted(per_comp_clubs, key=lambda c: (LIGAS.index(c) if c in LIGAS else 99, c))
        uit = f'<h2>{tr("alle_clubs")}</h2>'
        for comp in volgorde:
            kop = e(comp)
            if tellers.get(comp, 0) >= 3:
                kop = f'<a href="{prefix}competitie/{slug(comp)}/">{kop}</a>'
            chips = "".join(
                f'<a class="chip" href="{prefix}club/{slugs[k]}/"><b>{e(clubs[k]["naam"])}</b>'
                f'<span>{len(toekomst[k])} {tr("wedstrijd_1") if len(toekomst[k]) == 1 else tr("wedstrijd_n")}</span></a>'
                for k in sorted(per_comp_clubs[comp], key=lambda x: clubs[x]["naam"]))
            uit += f'<section class="compvak"><h3>{kop}</h3><div class="chips">{chips}</div></section>'
        return uit

    # ---------- clubpagina's
    for k, club in clubs.items():
        meta, verhaal = verhaal_voor(k, club["naam"], taal)
        meta_nl = meta if taal == "nl" else verhaal_voor(k, club["naam"], "nl")[0]
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
            antwoord = tr("ant_volgende", datum=datum(volgende[1][1]), label=volgende[1][2] if len(volgende[1]) > 2 else "", naam=naam, tegen=volgende[0]["tegen"])
        elif any(w.get("nu") for w in wedstrijden):
            antwoord = tr("ant_open", naam=naam)
        else:
            antwoord = tr("ant_geen", naam=naam)
        sc = schatting.get(k)
        if sc and sc["n"] >= 2:
            antwoord += tr("ant_schatting", naam=naam, mediaan=sc["mediaan"], n=sc["n"])
        inhoud = f"<h1>{e(tr('club_h1', naam=naam))}</h1><p>{e(tr('club_intro', naam=naam, datum=datum(bijgewerkt, False)))}</p>"
        inhoud += f"<h2>{tr('club_h2_wedstrijden')}</h2>" + "".join(kaartje(w, naam, club.get("url", ""), vandaag) for w in wedstrijden)
        if club.get("url"):
            inhoud += "<p>" + tr("club_officieel", url=e(club["url"]), naam=e(naam)) + "</p>"
        inhoud += f"<h2>{tr('faq')}</h2><h3>{e(tr('faq_q', naam=naam))}</h3><p>{e(antwoord)}</p>"
        if verhaal.strip():
            inhoud += "<h2>" + e(tr("club_over", naam=naam)) + "</h2>" + mini_markdown(verhaal)
        pad = f"club/{slugs[k]}/"
        url = f"{basis_taal()}/{pad}"
        jsonld = ""
        if meta_nl.get("stadion"):
            events = []
            for w in wedstrijden[:8]:
                events.append({"@type": "SportsEvent", "name": f"{naam} - {w['tegen']}", "startDate": aware(w["aftrap"]).isoformat(),
                               "eventStatus": "https://schema.org/EventScheduled", "url": url,
                               "location": {"@type": "Place", "name": meta_nl["stadion"],
                                            "address": {"@type": "PostalAddress", "addressLocality": meta_nl.get("stad", "")}}})
            jsonld = '<script type="application/ld+json">' + json.dumps(events, ensure_ascii=False) + "</script>"
        schrijf(pad, pagina(tr("club_titel", naam=naam, site=sitenaam), tr("club_beschr", naam=naam), pad, inhoud, jsonld, nav_html("../../"), "clubs"))

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
        inhoud = f"<h1>{e(tr('comp_h1', comp=comp))}</h1><p>{e(tr('comp_intro', comp=comp, datum=datum(bijgewerkt, False)))}</p>"
        inhoud += "".join(kaartje(w, clubs[k]["naam"], "", vandaag) for k, w in rijen[:40])
        inhoud += f'<p class="mute">{tr("comp_meer")}</p><nav class="clubs">' + "".join(
            f'<a href="../../club/{slugs[k]}/">{e(clubs[k]["naam"])}</a>' for k in sorted({k for k, _ in rijen}, key=lambda x: clubs[x]["naam"])) + "</nav>"
        pad = f"competitie/{cs}/"
        schrijf(pad, pagina(tr("comp_titel", comp=comp, site=sitenaam), tr("comp_beschr", comp=comp), pad, inhoud, "", nav_html("../../")))

    # ---------- tips voor het kopen van kaarten
    mijn_tips = tips[taal]
    stems_ander = {x["stem"]: x["slug"] for x in tips[ander]}
    if mijn_tips:
        def tips_nav(prefix, huidig=""):
            return (f'<h2>{tr("tips_meer")}</h2><ul>' + "".join(f'<li><a href="{prefix}tips/{x["slug"]}/">{e(x["titel"])}</a></li>' for x in mijn_tips if x["slug"] != huidig) + "</ul>")
        intro = (f"<h1>{tr('tips_h1')}</h1><p>{tr('tips_intro')}</p>"
                 + "".join(f'<div class="kaart"><b><a href="{x["slug"]}/">{e(x["titel"])}</a></b><div class="mute">{e(x["beschrijving"])}</div></div>' for x in mijn_tips))
        schrijf("tips/", pagina(tr("tips_titel", site=sitenaam), tr("tips_beschr"), "tips/", intro, "", "", "tips", alt_pad="tips/" if tips[ander] else None))
        for x in mijn_tips:
            pad = f"tips/{x['slug']}/"
            alt = f"tips/{stems_ander[x['stem']]}/" if x["stem"] in stems_ander else None
            inhoud = f"<h1>{e(x['titel'])}</h1>" + mini_markdown(x["tekst"])
            schrijf(pad, pagina(f"{x['titel']} | {sitenaam}", x["beschrijving"], pad, inhoud, "", tips_nav("../../", x["slug"]), "tips", alt_pad=alt))

    # ---------- Over en Privacy
    aantal_w = sum(len(v) for v in toekomst.values())
    if CFG["email"]:
        _, waarom = lees_verhaal(ROOT / MAPPEN[taal]["pagina"] / "over.md")
        for naam, inhoud, titel in (("over", tekstpagina_over(len(clubs), aantal_w, bijgewerkt, waarom), tr("over_titel", site=sitenaam)),
                                    ("privacy", tekstpagina_privacy(bijgewerkt), tr("privacy_titel", site=sitenaam))):
            pad = f"{naam}/"
            schrijf(pad, pagina(titel, tr("pagina_beschr", titel=titel), pad, inhoud, "", "", "over" if naam == "over" else ""))
    elif taal == "nl":
        print(tr("onderhoud_waarschuwing"))

    # ---------- overzichtspagina met alle clubs (daar linkt het menu naartoe)
    if clubs:
        inhoud = f'<h1>{tr("alle_clubs")}</h1><p class="mute">{tr("clubs_intro")}</p>' + nav_html("../").replace(f'<h2>{tr("alle_clubs")}</h2>', "")
        schrijf("club/", pagina(tr("clubs_titel", site=sitenaam), tr("clubs_beschr"), "club/", inhoud, "", "", "clubs"))

    # ---------- hoofdpagina: zoekmachine-gegevens, menu en links naar de subpagina's
    if index_bron:
        s = index_bron
        PAGINAS.append((taal, "", ""))
        basis_t = basis_taal()
        titel_hoofd = tr("home_titel", site=sitenaam)
        seo = (f'<!--SEO--><meta name="description" content="{e(tr("home_beschr"))}"><link rel="canonical" href="{e(basis_t)}/">{hreflang_tags("", "")}<!--/SEO-->')
        s = re.sub(r"<!--SEO-->.*?<!--/SEO-->", lambda m: seo, s, flags=re.S) if "<!--SEO-->" in s else s.replace("</title>", "</title>" + seo, 1)
        s = re.sub(r"<title>.*?</title>", lambda m: f"<title>{e(titel_hoofd)}</title>", s, count=1, flags=re.S)
        blok = f'<!--CLUBS--><section class="rules">{nav_html("")}<footer class="mute" style="margin-top:2em">{voet("")}</footer></section><!--/CLUBS-->'
        mblok = f"<!--MENU--><style>{MENU_CSS}</style>{menu('', 'home', '', '')}<!--/MENU-->"
        s = re.sub(r"<!--MENU-->.*?<!--/MENU-->", lambda m: mblok, s, flags=re.S) if "<!--MENU-->" in s else s.replace("<body>", "<body>" + mblok, 1)
        tag = f"<!--GA-->{analytics_tag('')}<!--/GA-->"
        s = re.sub(r"<!--GA-->.*?<!--/GA-->", lambda m: tag, s, flags=re.S) if "<!--GA-->" in s else s.replace("</head>", tag + "</head>", 1)
        s = re.sub(r"<!--CLUBS-->.*?<!--/CLUBS-->", lambda m: blok, s, flags=re.S) if "<!--CLUBS-->" in s else s.replace("</main>", blok + "</main>", 1)
        if taal == "en":
            for nl_tekst, en_tekst in INDEX_EN:
                if nl_tekst not in s:
                    print("LET OP: tekst niet gevonden op de hoofdpagina:", nl_tekst[:60])
                s = s.replace(nl_tekst, en_tekst, 1)
        UIT.mkdir(parents=True, exist_ok=True)
        (UIT / "index.html").write_text(s, encoding="utf-8")
    return len(clubs), len(per_comp)


def schrijf_sitemap(lms):
    basis = CFG["basis"]
    regels, gezien = [], set()
    for taal, pad, alt in PAGINAS:
        url = basis + ("/en/" if taal == "en" else "/") + pad
        if url in gezien:
            continue
        gezien.add(url)
        extra = ""
        if alt is not None:
            nl = f"{basis}/{pad if taal == 'nl' else alt}"
            en = f"{basis}/en/{alt if taal == 'nl' else pad}"
            extra = (f'<xhtml:link rel="alternate" hreflang="nl" href="{e(nl)}"/><xhtml:link rel="alternate" hreflang="en" href="{e(en)}"/>'
                     f'<xhtml:link rel="alternate" hreflang="x-default" href="{e(nl)}"/>')
        regels.append(f"<url><loc>{e(url)}</loc><lastmod>{lms}</lastmod>{extra}</url>\n")
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                                      'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "".join(regels) + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {basis}/sitemap.xml\n", encoding="utf-8")
    return len(gezien)


def main():
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    site = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    basis = site["basis_url"].rstrip("/")
    bew = site.get("bewaartermijn", "2 maanden")
    CFG.update({"basis": basis, "ga": site.get("ga_id", "").strip(), "email": site.get("contact_email", "").strip(),
                "beheerder": site.get("beheerder", "").strip(), "sitenaam": site["sitenaam"], "bewaartermijn": bew,
                "bewaartermijn_en": re.sub(r"\bmaanden\b", "months", re.sub(r"\bmaand\b", "month", re.sub(r"\bjaar\b", "year", bew)))})
    vandaag = datetime.datetime.now(NL)
    bijgewerkt = data.get("bijgewerkt", vandaag.date().isoformat())
    idx = ROOT / "index.html"
    index_bron = idx.read_text(encoding="utf-8") if idx.exists() else ""
    data_en = vertaal.vertaal_data(data)
    (ROOT / "data_en.json").write_text(json.dumps(data_en, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tips = {"nl": laad_tips("nl"), "en": laad_tips("en")}
    n_clubs = n_comp = 0
    for taal, d in (("nl", data), ("en", data_en)):
        n_clubs, n_comp = bouw_taal(taal, d, tips, index_bron, vandaag, bijgewerkt)
    aantal = schrijf_sitemap(datetime.date.fromisoformat(bijgewerkt).isoformat())
    print(f"{aantal} pagina's gebouwd in twee talen ({n_clubs} clubs, {n_comp} competities waarvan een deel genoeg wedstrijden heeft)")
    if vertaal.ONBEKEND:
        print("NIET VERTAALD (voeg toe aan scripts/vertaal.py):")
        for x in sorted(vertaal.ONBEKEND):
            print("  -", x)


if __name__ == "__main__":
    main()
