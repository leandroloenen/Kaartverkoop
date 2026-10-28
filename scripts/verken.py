"""Verkenning van ticketpagina's (eenmalig te draaien).

Dit programma doet wat jij eerder handmatig in de Netwerk-tab deed, maar dan voor een hele lijst
pagina's tegelijk: het opent elke ticketpagina in een onzichtbare browser en schrijft op wat de pagina
op de achtergrond ophaalt (welke adressen, welk soort gegevens) en welke tekst er op het scherm staat.
Daaruit kunnen we zien welke clubs hetzelfde systeem gebruiken.

Invoer:  scripts/verken_lijst.txt   (per regel: naam | adres)
Uitvoer: verkenning.json            (alleen openbare informatie; geen cookies of inloggegevens)
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parent.parent
LIJST = ROOT / "scripts" / "verken_lijst.txt"
UIT = ROOT / "verkenning.json"

RUIS = ("google-analytics", "googletagmanager", "doubleclick", "facebook", "hotjar", "clarity.ms", "sentry",
        "cookiebot", "onetrust", "adobedtm", "gstatic", "googleapis.com/css", "fonts.", "newrelic", "tiktok",
        "linkedin", "twitter", "youtube", "cloudflareinsights", "usercentrics", "hubspot", "sleeknote")
PLATFORMEN = ("tymes4", "onebox", "vivenu", "eventim", "ticketmaster", "tmtickets", "paylogic", "queue-it",
              "seetickets", "ticketone", "secutix", "oneboxtds", "stadiumportal", "ticketco", "fanatics", "accesso")


GEVOELIG = re.compile(r"secret|password|wachtwoord|token|apikey|api_key|authorization|credential|signature|key", re.I)
LANGE_WAARDE = re.compile(r"\S{24,}")


def maskeer(obj):
    """Haal alles weg wat op een toegangscode lijkt: gevoelige veldnamen en lange waarden zonder spaties."""
    if isinstance(obj, dict):
        return {k: ("[weggelaten]" if GEVOELIG.search(str(k)) else maskeer(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [maskeer(v) for v in obj[:20]]
    if isinstance(obj, str):
        return "[lange waarde weggelaten]" if len(obj) >= 24 and " " not in obj else obj
    return obj


def veilig_voorbeeld(tekst):
    try:
        return json.dumps(maskeer(json.loads(tekst)), ensure_ascii=False)[:500]
    except Exception:  # noqa: BLE001
        return LANGE_WAARDE.sub("[lange waarde weggelaten]", tekst)[:500]


def schoon_url(url):
    """Houd host en pad over; van de parameters alleen de namen (waarden kunnen sleutels bevatten)."""
    d = urlsplit(url)
    namen = ",".join(k for k, _ in parse_qsl(d.query, keep_blank_values=True))
    return f"{d.scheme}://{d.netloc}{d.path}" + (f"?{namen}" if namen else "")


def lees_lijst():
    uit = []
    for regel in LIJST.read_text(encoding="utf-8").splitlines():
        regel = regel.strip()
        if not regel or regel.startswith("#"):
            continue
        naam, _, adres = regel.partition("|")
        uit.append((naam.strip(), adres.strip()))
    return uit


def verken(browser, naam, adres):
    gegevens = {"naam": naam, "adres": schoon_url(adres), "verzoeken": [], "json_voorbeelden": [], "fout": None}
    verzoeken, voorbeelden, hosts = [], [], set()

    def bij_antwoord(r):
        try:
            if r.request.resource_type not in ("xhr", "fetch") or any(x in r.url for x in RUIS):
                return
            soort = r.headers.get("content-type", "")
            verzoeken.append({"methode": r.request.method, "status": r.status, "url": schoon_url(r.url),
                              "soort": soort.split(";")[0], "lengte": r.headers.get("content-length", "")})
            if "json" in soort and r.status == 200 and len(voorbeelden) < 6:
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
        gegevens["eind_adres"] = schoon_url(page.url)
        gegevens["titel"] = page.title()
        gegevens["scherm_tekst"] = LANGE_WAARDE.sub("[lange waarde weggelaten]", re.sub(r"\n{3,}", "\n\n", page.inner_text("body")))[:2500]
    except Exception as fout:  # noqa: BLE001
        gegevens["fout"] = str(fout).splitlines()[0][:200]
    finally:
        context.close()
    gegevens["verzoeken"] = verzoeken[:25]
    gegevens["json_voorbeelden"] = voorbeelden
    gegevens["herkende_systemen"] = sorted({p for p in PLATFORMEN for h in hosts if p in h.lower()}
                                           | {p for p in PLATFORMEN if p in page_of(gegevens)})
    gegevens["wachtrij"] = any("queue" in h.lower() for h in hosts)
    return gegevens


def page_of(g):
    return " ".join(v["url"].lower() for v in g["verzoeken"]) + " " + g.get("eind_adres", "").lower()


def main():
    from playwright.sync_api import sync_playwright

    lijst = lees_lijst()
    resultaat = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for i, (naam, adres) in enumerate(lijst, 1):
            print(f"[{i}/{len(lijst)}] {naam}", flush=True)
            resultaat.append(verken(browser, naam, adres))
        browser.close()
    UIT.write_text(json.dumps(resultaat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(resultaat)} pagina's verkend; resultaat in {UIT.name}")


if __name__ == "__main__":
    sys.exit(main())
