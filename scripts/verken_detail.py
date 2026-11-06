"""Detailverkenning: opent per club een overzichtspagina en daarna een paar wedstrijdpagina's, en bewaart de tekst.

Gebruik:  python scripts/verken_detail.py
Leest scripts/verken_detail_lijst.txt, regels van de vorm
    naam | startadres | modus | aantal | json=WOORD
met als modus:
    geen            alleen de startpagina zelf lezen
    link:PATROON    alle links op de pagina waarvan het adres PATROON bevat openen (tot 'aantal')
    klik:PATROON    knoppen of links waarvan de tekst PATROON bevat aanklikken (tot 'aantal')
Met json=WOORD (optioneel, laatste kolom) bewaren we het complete JSON-antwoord dat dat woord bevat.
Uitvoer: verkenning_detail.json. Gevoelig ogende waarden worden weggelaten; datums en tijden blijven staan.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verken import LANGE_WAARDE, RUIS, lees_regels, schoon_url, veilig_voorbeeld  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LIJST = ROOT / "scripts" / "verken_detail_lijst.txt"
UIT = ROOT / "verkenning_detail.json"
TEKSTLENGTE = 15000
SLEUTELWOORDEN = re.compile(r"sale|venta|vendita|verkauf|date|fecha|data|opens|socio|member|abbon", re.I)


def pagina_lezen(page, wacht=3000, scroll=2):
    try:
        page.wait_for_load_state("networkidle", timeout=12000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(wacht)
    for _ in range(scroll):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(900)
    tekst = re.sub(r"\n{3,}", "\n\n", page.inner_text("body"))
    return {"adres": schoon_url(page.url), "titel": page.title(),
            "tekst": LANGE_WAARDE.sub("[lange waarde weggelaten]", tekst)[:TEKSTLENGTE]}


def verken_club(browser, naam, adres, modus, aantal, json_woord=""):
    uit = {"naam": naam, "startadres": schoon_url(adres), "modus": modus, "paginas": [], "links": [], "json_volledig": [], "fout": None}
    context = browser.new_context(locale="en-GB")
    page = context.new_page()
    json_antwoorden = []

    def bij_antwoord(r):
        try:
            if r.request.resource_type in ("xhr", "fetch") and r.status == 200 and not any(x in r.url for x in RUIS) \
                    and "json" in r.headers.get("content-type", "") and (len(json_antwoorden) < 6 or json_woord):
                tekst = r.text()
                if json_woord and json_woord in tekst and len(uit["json_volledig"]) < 2:
                    uit["json_volledig"].append({"url": schoon_url(r.url), "inhoud": veilig_voorbeeld(tekst, 90000)})
                if SLEUTELWOORDEN.search(tekst) and len(json_antwoorden) < 6:
                    json_antwoorden.append({"url": schoon_url(r.url), "begin": veilig_voorbeeld(tekst, 6000)})
        except Exception:  # noqa: BLE001
            pass

    page.on("response", bij_antwoord)
    try:
        page.goto(adres, wait_until="domcontentloaded", timeout=45000)
        start = pagina_lezen(page, scroll=3)
        start["tekst"] = start["tekst"][:5000]  # de startpagina kennen we al; hier gaat het om de details
        uit["paginas"].append(start)
        soort, _, patroon = modus.partition(":")
        # alle links van dezelfde site noteren, zodat we later kunnen zien welke pagina's er zijn
        hrefs = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a => [a.href, (a.innerText||'').trim().slice(0,60)])""")
        gezien = set()
        for h, t in hrefs:
            if urlsplit(h).netloc == urlsplit(adres).netloc and h not in gezien and len(uit["links"]) < 80:
                gezien.add(h)
                uit["links"].append([schoon_url(h), t])
        if soort == "link" and patroon:
            doelen = [h for h, _ in hrefs if re.search(patroon, h)]
            doelen = list(dict.fromkeys(doelen))[:aantal]
            for doel in doelen:
                try:
                    page.goto(doel, wait_until="domcontentloaded", timeout=45000)
                    uit["paginas"].append(pagina_lezen(page))
                except Exception as fout:  # noqa: BLE001
                    uit["paginas"].append({"adres": schoon_url(doel), "fout": str(fout).splitlines()[0][:200]})
        elif soort == "klik" and patroon:
            regex = re.compile(patroon, re.I)
            for n in range(aantal):
                page.goto(adres, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_timeout(2500)
                knoppen = page.get_by_role("link", name=regex).or_(page.get_by_role("button", name=regex))
                if knoppen.count() <= n:
                    break
                aantal_paginas = len(context.pages)
                knoppen.nth(n).click(timeout=10000)
                page.wait_for_timeout(2500)
                doel = context.pages[-1] if len(context.pages) > aantal_paginas else page
                uit["paginas"].append(pagina_lezen(doel))
                if doel is not page:
                    doel.close()
    except Exception as fout:  # noqa: BLE001
        uit["fout"] = str(fout).splitlines()[0][:200]
    finally:
        uit["json_antwoorden"] = json_antwoorden
        context.close()
    return uit


def main():
    from playwright.sync_api import sync_playwright

    taken = []
    for r in lees_regels(LIJST):
        if len(r) >= 2:
            woord = next((x[5:] for x in r[4:] if x.startswith("json=")), "")
            taken.append((r[0], r[1], r[2] if len(r) > 2 and r[2] else "geen", int(r[3]) if len(r) > 3 and r[3].isdigit() else 3, woord))
    resultaat = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for i, (naam, adres, modus, aantal, woord) in enumerate(taken, 1):
            print(f"[{i}/{len(taken)}] {naam}", flush=True)
            resultaat.append(verken_club(browser, naam, adres, modus, aantal, woord))
        browser.close()
    UIT.write_text(json.dumps(resultaat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(resultaat)} clubs verkend; resultaat in {UIT.name}")


if __name__ == "__main__":
    sys.exit(main())
