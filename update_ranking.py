import os, sys, json, time, requests
from datetime import datetime, timezone

HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
ROUTING = "europe"   # europe para EUW/EUNE/TR/RU
PLATFORM = "euw1"

ACCOUNTS = [  # (nombre, tag)
    ("Fr4nux", "EUW"),
    # ("Jugador2", "EUW"),
]

TIERS = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","EMERALD","DIAMOND","MASTER","GRANDMASTER","CHALLENGER"]
DIVS = {"IV": 0, "III": 1, "II": 2, "I": 3}


def get(url):
    for _ in range(3):
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 5)) + 1)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Límite de peticiones persistente")


def score(tier, div, lp):
    t = TIERS.index(tier)
    return 2800 + lp if t >= 7 else t * 400 + DIVS[div] * 100 + lp


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


now = datetime.now(timezone.utc).isoformat(timespec="seconds")
history = load("history.json", {})
players = []

try:
    for name, tag in ACCOUNTS:
        acc = get(f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}")
        entries = get(f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-puuid/{acc['puuid']}")
        solo = next((e for e in entries if e["queueType"] == "RANKED_SOLO_5x5"), None)
        label = f"{name}#{tag}"
        if solo:
            players.append({
                "name": label, "tier": solo["tier"], "rank": solo["rank"],
                "lp": solo["leaguePoints"], "wins": solo["wins"], "losses": solo["losses"],
                "games": solo["wins"] + solo["losses"],
                "score": score(solo["tier"], solo["rank"], solo["leaguePoints"]),
            })
        else:
            players.append({"name": label, "tier": "UNRANKED", "rank": "", "lp": 0,
                            "wins": 0, "losses": 0, "games": 0, "score": -1})
        time.sleep(0.2)
except Exception as e:
    print(f"ERROR: {e}. Se conservan los datos anteriores.")
    sys.exit(1)

# Historial: solo se añade una entrada si hay cambios
for p in players:
    if p["score"] < 0:
        continue
    snaps = history.setdefault(p["name"], [])
    snap = {"t": now, "score": p["score"], "tier": p["tier"], "rank": p["rank"],
            "lp": p["lp"], "w": p["wins"], "l": p["losses"]}
    last = snaps[-1] if snaps else None
    if not last or (last["score"], last["w"], last["l"]) != (snap["score"], snap["w"], snap["l"]):
        snaps.append(snap)

players.sort(key=lambda p: p["score"], reverse=True)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump({"updated": now, "players": players}, f, ensure_ascii=False, indent=2)
with open("history.json", "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False)
