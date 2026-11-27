"""Wedstrijdlijst van football-data.org: zorgt dat elke thuiswedstrijd op de site staat, ook als de club
de kaartverkoop nog niet heeft aangekondigd. Rijen uit deze bron krijgen "fx": true en de tekst
'Verkoopinfo volgt'. Zodra een clubverzamelaar dezelfde wedstrijd (zelfde club, zelfde dag) levert,
verdwijnt de fx-rij en geldt de echte verkoopinfo.

Het token komt uit de omgevingsvariabele FOOTBALL_DATA_TOKEN (GitHub-secret). Zonder token doet dit
programma niets."""
import datetime
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

API = "https://api.football-data.org/v4/competitions/{code}/matches?status=SCHEDULED,TIMED"
COMPETITIES = {"PL": "Premier League", "ELC": "Championship", "BL1": "Bundesliga", "SA": "Serie A", "PD": "La Liga",
               "FL1": "Ligue 1", "DED": "Eredivisie", "PPL": "Primeira Liga", "CL": "Champions League"}
HORIZON_DAGEN = 75
PAUZE = 7  # seconden tussen verzoeken (gratis plan: 10 per minuut)
NOOT = "Verkoopinfo volgt: de club heeft de kaartverkoop voor deze wedstrijd nog niet bekendgemaakt."
NOOT_TIJD = " Aanvangstijd nog niet bevestigd."

STOP = {"fc", "afc", "cf", "sc", "ac", "as", "ss", "us", "rc", "rcd", "ca", "sl", "cp", "fk", "bk", "vfb", "vfl", "tsg", "fsv",
        "sv", "calcio", "ssc", "bc", "osc", "losc", "olympique", "de", "del", "the", "club", "clube", "balompie", "hove", "albion",
        "hotspur", "and", "e"}

# Alleen nodig als de API de club anders noemt dan wij (sleutel = clubsleutel in data.json).
ALIAS = {"inter": ["internazionale", "fc internazionale milano"], "psg": ["psg", "paris sg"], "lyon": ["lyon", "lyonnais"],
         "newcastle": ["newcastle"], "leeds": ["leeds"], "forest": ["nottingham forest", "nottingham"],
         "benfica": ["sport lisboa benfica"], "sporting": ["sporting portugal"], "braga": ["sporting braga"], "nec": ["nec nijmegen"], "az": ["az alkmaar"],
         "mancity": ["man city"], "tottenham": ["tottenham"], "brighton": ["brighton"], "wolfsburg": ["wolfsburg"],
         "union": ["union berlin"], "bvb": ["borussia dortmund"], "milan": ["milan"]}


def norm(tekst):
    t = "".join(c for c in unicodedata.normalize("NFD", tekst or "") if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"[^a-z0-9]+", " ", t.replace(".", ""))
    delen = [d for d in t.split() if d not in STOP and not re.fullmatch(r"\d{2,4}", d) and d != "1"]
    return " ".join(delen)


def _haal(code, token):
    req = urllib.request.Request(API.format(code=code), headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _club_index(clubs):
    """norm-naam -> clubsleutel"""
    idx = {}
    for sleutel, c in clubs.items():
        for vorm in [norm(c["naam"])] + [norm(a) for a in ALIAS.get(sleutel, [])]:
            if vorm:
                idx.setdefault(vorm, sleutel)
    return idx


def _vind(team, idx):
    for v in (team.get("name"), team.get("shortName"), team.get("tla")):
        k = idx.get(norm(v))
        if k:
            return k
    return None


def haal_fixtures(clubs, nl_tz):
    """Geeft (rijen, gezien_clubs). Rijen: wedstrijden (thuis) van clubs die op onze site staan."""
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    if not token:
        print("[football-data] geen token ingesteld; wedstrijdlijst overgeslagen")
        return [], set()
    idx = _club_index(clubs)
    nu = datetime.datetime.now(datetime.timezone.utc)
    grens = nu + datetime.timedelta(days=HORIZON_DAGEN)
    rijen, gezien, onbekend = [], set(), {}
    for i, (code, comp) in enumerate(COMPETITIES.items()):
        if i:
            time.sleep(PAUZE)
        try:
            data = _haal(code, token)
        except urllib.error.HTTPError as f:
            print(f"[football-data] {code}: HTTP {f.code} ({'niet in je gratis plan of token fout' if f.code in (401, 403) else 'tijdelijk probleem'}); overgeslagen")
            continue
        except Exception as f:  # noqa: BLE001
            print(f"[football-data] {code}: mislukt ({str(f)[:100]}); overgeslagen")
            continue
        aantal = 0
        for m in data.get("matches", []):
            thuis, uit = m.get("homeTeam") or {}, m.get("awayTeam") or {}
            if not thuis.get("name") or not uit.get("name"):
                continue
            k = _vind(thuis, idx)
            if not k:
                onbekend[thuis.get("name")] = code
                continue
            gezien.add(k)
            try:
                d = datetime.datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if d > grens or d < nu:
                continue
            tegen_k = _vind(uit, idx)
            tegen = clubs[tegen_k]["naam"] if tegen_k else (uit.get("shortName") or uit["name"])
            lokaal = d.astimezone(nl_tz)
            zonder_tijd = m.get("status") == "SCHEDULED"
            rijen.append({"club": k, "tegen": tegen, "comp": comp,
                          "aftrap": lokaal.strftime("%Y-%m-%d") if zonder_tijd else lokaal.strftime("%Y-%m-%dT%H:%M"),
                          "fases": [], "nu": False, "info": True,
                          "noot": NOOT + (NOOT_TIJD if zonder_tijd else ""), "bron": "", "fx": True})
            aantal += 1
        print(f"[football-data] {code} ({comp}): {aantal} thuiswedstrijden binnen {HORIZON_DAGEN} dagen")
    if onbekend:
        print("[football-data] teams zonder match met onze clublijst (alleen ter info): " + ", ".join(sorted(onbekend)))
    return rijen, gezien
