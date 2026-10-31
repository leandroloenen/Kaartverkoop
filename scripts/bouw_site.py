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

CSS = """:root{--bg:#f3f1ec;--card:#fffdf8;--ink:#14213d;--mute:#5b6378;--line:#d9d5c8;--accent:#e8a500;--open:#1b7f4b}
@media (prefers-color-scheme:dark){:root{--bg:#0f1526;--card:#18203a;--ink:#eef0f7;--mute:#9aa3bd;--line:#2b3556;--accent:#f2b705;--open:#4cc38a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.55}
main{max-width:820px;margin:0 auto;padding:22px 16px 56px}a{color:var(--ink)}h1{font-size:clamp(1.7rem,5vw,2.4rem);line-height:1.2;margin:.4em 0}
h2{margin-top:1.8em}.mute{color:var(--mute)}.kaart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:10px 0}
.kaart b{font-size:1.05rem}.fase{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:4px 0;border-top:1px solid var(--line);font-size:.95rem}
.voorbij{opacity:.55}.label{display:inline-block;font-size:.8rem;font-weight:600;border:1px solid var(--line);border-radius:99px;padding:1px 9px;margin-left:6px}
.nu{color:var(--open)}nav.clubs a{display:inline-block;margin:2px 10px 2px 0}.terug{font-weight:600}footer{margin-top:3em;font-size:.85rem}"""


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
            uit.append(f"<h2>{e(regels[0][3:].strip())}</h2>")
            regels = regels[1:]
        if not regels:
            continue
        def inline(x):
            return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", e(x))
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


def pagina(titel, beschrijving, canonical, prefix, inhoud, jsonld="", nav=""):
    return f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title><meta name="description" content="{e(beschrijving)}"><link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(titel)}"><meta property="og:description" content="{e(beschrijving)}"><meta property="og:type" content="website"><meta property="og:url" content="{e(canonical)}">
<style>{CSS}</style>{jsonld}</head><body><main>
<a class="terug" href="{prefix}">← Naar het volledige overzicht met filters</a>
{inhoud}
{nav}
<footer class="mute">Dit overzicht is niet gelieerd aan de genoemde clubs. Controleer verkoopmomenten altijd op de officiële ticketsite van de club.</footer>
</main></body></html>"""


def main():
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    site = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    basis, sitenaam = site["basis_url"].rstrip("/"), site["sitenaam"]
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

    # ---------- hoofdpagina: zoekmachine-gegevens en links naar de subpagina's
    idx = ROOT / "index.html"
    if idx.exists():
        s = idx.read_text(encoding="utf-8")
        seo = (f'<!--SEO--><meta name="description" content="Wanneer gaan voetbaltickets in de verkoop? Overzicht van de kaartverkoop van clubs uit de Eredivisie, Bundesliga, La Liga en meer, per doelgroep en dagelijks bijgewerkt.">'
               f'<link rel="canonical" href="{e(basis)}/"><!--/SEO-->')
        s = re.sub(r"<!--SEO-->.*?<!--/SEO-->", lambda m: seo, s, flags=re.S) if "<!--SEO-->" in s else s.replace("</title>", "</title>" + seo, 1)
        blok = f'<!--CLUBS--><section class="rules">{nav_html("")}</section><!--/CLUBS-->'
        s = re.sub(r"<!--CLUBS-->.*?<!--/CLUBS-->", lambda m: blok, s, flags=re.S) if "<!--CLUBS-->" in s else s.replace("</main>", blok + "</main>", 1)
        idx.write_text(s, encoding="utf-8")

    # ---------- sitemap en robots
    lms = datetime.date.fromisoformat(bijgewerkt).isoformat()
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{e(u)}</loc><lastmod>{lms}</lastmod></url>\n" for u in pagina_urls) + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {basis}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(pagina_urls)} pagina's gebouwd ({len(clubs)} clubs, {len(pagina_urls) - 1 - len(clubs)} competities)")


if __name__ == "__main__":
    main()
