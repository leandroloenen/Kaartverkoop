"""Verkenning van ticketpagina's (zo vaak als nodig te draaien, handmatig gestart).

Twee manieren:
1. Brede verkenning:  python scripts/verken.py
   Leest scripts/verken_lijst.txt (naam | adres) en noteert per pagina wat er op de achtergrond wordt geladen.
2. Verdieping:        python scripts/verken.py scripts/verken_diep_lijst.txt
   Leest scripts/verken_diep_lijst.txt (naam | patronen | tekst). Het adres van elke club haalt het uit
   verken_lijst.txt. Van de verzoeken waarvan het adres een van de 'patronen' bevat, wordt het complete
   antwoord bewaard, en met 'tekst' ook de volledige zichtbare pagina-tekst.

Uitvoer staat in verkenning.json (of verkenning_diep.json). Gevoelig ogende waarden worden weggelaten.
Datums en tijden blijven bewust staan, die hebben we nodig.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parent.parent
BREDE_LIJST = ROOT / "scripts" / "verken_lijst.txt"

RUIS = ("google-analytics", "googletagmanager", "doubleclick", "facebook", "hotjar", "clarity.ms", "sentry",
        "cookiebot", "onetrust", "adobedtm", "gstatic", "googleapis.com/css", "fonts.", "newrelic", "tiktok",
        "linkedin", "twitter", "youtube", "cloudflareinsights", "usercentrics", "hubspot", "sleeknote")
PLATFORMEN = ("tymes4", "onebox", "vivenu", "eventim", "ticketmaster", "tmtickets", "paylogic", "queue-it",
              "seetickets", "ticketone", "secutix", "oneboxtds", "stadiumportal", "ticketco", "fanatics", "accesso")
GEVOELIG = re.compile(r"secret|password|wachtwoord|token|apikey|api_key|authorization|credential|signature|key", re.I)
LANGE_WAARDE = re.compile(r"\S{24,}")
DATUM_TIJD = re.compile(r"^\d{4}-\d{2}-\d{2}([T ][\d:.,]+)?(Z|[+-]\d{2}:?\d{2})?$")


def maskeer(obj):
    """Haal alles weg wat op een toegangscode lijkt, maar laat datums en tijden staan."""
    if isinstance(obj, dict):
        return {k: ("[weggelaten]" if GEVOELIG.search(str(k)) else maskeer(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [maskeer(v) for v in obj[:200]]
    if isinstance(obj, str):
        if DATUM_TIJD.match(obj):
            return obj
        return "[lange waarde weggelaten]" if len(obj) >= 24 and " " not in obj else obj
    return obj


def veilig_voorbeeld(tekst, lengte=500):
    try:
        return json.dumps(maskeer(json.loads(tekst)), ensure_ascii=False)[:lengte]
    except Exception:  # noqa: BLE001
        return LANGE_WAARDE.sub("[lange waarde weggelaten]", tekst)[:lengte]


def schoon_url(url):
    """Houd host en pad over; van de parameters alleen de namen (waarden kunnen sleutels bevatten)."""
    d = urlsplit(url)
    namen = ",".join(k for k, _ in parse_qsl(d.query, keep_blank_values=True))
    return f"{d.scheme}://{d.netloc}{d.path}" + (f"?{namen}" if namen else "")


def lees_regels(pad):
    uit = []
    for regel in Path(pad).read_text(encoding="utf-8").splitlines():
        regel = regel.strip()
        if regel and not regel.startswith("#"):
            uit.append([k.strip() for k in regel.split("|")])
    return uit


def verken(browser, naam, adres, patronen=(), volledige_tekst=False):
    gegevens = {"naam": naam, "adres": schoon_url(adres), "verzoeken": [], "json_voorbeelden": [], "diepte": [], "fout": None}
    verzoeken, voorbeelden, diepte, hosts = [], [], [], set()

    def bij_antwoord(r):
        try:
            if r.request.resource_type not in ("xhr", "fetch") or any(x in r.url for x in RUIS):
                return
            soort = r.headers.get("content-type", "")
            verzoeken.append({"methode": r.request.method, "status": r.status, "url": schoon_url(r.url),
                              "soort": soort.split(";")[0], "lengte": r.headers.get("content-length", "")})
            if r.status == 200 and any(p in r.url for p in patronen) and len(diepte) < 8:
                actie = dict(parse_qsl(urlsplit(r.url).query)).get("operationName", "")
                diepte.append({"url": schoon_url(r.url), "operatie": actie, "inhoud": veilig_voorbeeld(r.text(), 40000)})
            elif "json" in soort and r.status == 200 and len(voorbeelden) < 6:
                voorbeelden.append({"url": schoon_url(r.url), "begin": veilig_voorbeeld(r.text())})
        except Exception:  # noqa: BLE001
            pass

    context = browser.new_context(locale="nl-NL")
    page = context.new_page()
    page.on("response", bij_antwoord)
    page.on("request", lambda q: hosts.add(urlsplit(q.url).netloc))
    try:
        page.goto(adres, wait_until="domcontentloaded", timeout=45000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(3000)
        for _ in range(4 if volledige_tekst else 0):  # naar beneden scrollen zodat lijsten volledig laden
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1200)
        gegevens["eind_adres"] = schoon_url(page.url)
        gegevens["titel"] = page.title()
        tekst = re.sub(r"\n{3,}", "\n\n", page.inner_text("body"))
        gegevens["scherm_tekst"] = LANGE_WAARDE.sub("[lange waarde weggelaten]", tekst)[:(20000 if volledige_tekst else 2500)]
    except Exception as fout:  # noqa: BLE001
        gegevens["fout"] = str(fout).splitlines()[0][:200]
    finally:
        context.close()
    gegevens["verzoeken"] = verzoeken[:25]
    gegevens["json_voorbeelden"] = voorbeelden
    gegevens["diepte"] = diepte
    alles = " ".join(v["url"].lower() for v in verzoeken) + " " + gegevens.get("eind_adres", "").lower()
    gegevens["herkende_systemen"] = sorted({p for p in PLATFORMEN for h in hosts if p in h.lower()}
                                           | {p for p in PLATFORMEN if p in alles})
    gegevens["wachtrij"] = any("queue" in h.lower() for h in hosts)
    return gegevens


def main():
    from playwright.sync_api import sync_playwright

    lijstpad = Path(sys.argv[1]) if len(sys.argv) > 1 else BREDE_LIJST
    diep = "diep" in lijstpad.name
    uit_pad = ROOT / ("verkenning_diep.json" if diep else "verkenning.json")
    taken = []
    if diep:
        adressen = {r[0].lower(): r[1] for r in lees_regels(BREDE_LIJST) if len(r) >= 2}
        for r in lees_regels(lijstpad):
            naam = r[0]
            patronen = tuple(p.strip() for p in (r[1] if len(r) > 1 else "").split(",") if p.strip())
            tekst = len(r) > 2 and r[2].lower() == "tekst"
            taken.append((naam, adressen.get(naam.lower(), ""), patronen, tekst))
    else:
        taken = [(r[0], r[1], (), False) for r in lees_regels(lijstpad) if len(r) >= 2]

    resultaat = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for i, (naam, adres, patronen, tekst) in enumerate(taken, 1):
            print(f"[{i}/{len(taken)}] {naam}", flush=True)
            if not adres:
                resultaat.append({"naam": naam, "fout": "adres niet gevonden in verken_lijst.txt"})
                continue
            resultaat.append(verken(browser, naam, adres, patronen, tekst))
        browser.close()
    uit_pad.write_text(json.dumps(resultaat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(resultaat)} pagina's verkend; resultaat in {uit_pad.name}")


if __name__ == "__main__":
    sys.exit(main())
