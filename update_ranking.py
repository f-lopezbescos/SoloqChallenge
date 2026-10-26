import os, json, time, requests
from datetime import datetime, timezone

HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
ROUTING = "europe"   # europe para EUW/EUNE/TR/RU; americas para NA/BR/LAN; asia para KR/JP
PLATFORM = "euw1"

ACCOUNTS = [  # (nombre, tag)
    ("Jugador1", "EUW"), ("Jugador2", "EUW"), ("Jugador3", "EUW"), ("Jugador4", "EUW"),
    ("Jugador5", "EUW"), ("Jugador6", "EUW"), ("Jugador7", "EUW"), ("Jugador8", "EUW"),
]

TIERS = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","EMERALD","DIAMOND","MASTER","GRANDMASTER","CHALLENGER"]
DIVS = {"IV": 0, "III": 1, "II": 2, "I": 3}

def get(url):
    for _ in range(3):
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 5)))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Demasiados reintentos")

def score(tier, div, lp):
    t = TIERS.index(tier)
    return 2800 + lp if t >= 7 else t * 400 + DIVS[div] * 100 + lp

players = []
for name, tag in ACCOUNTS:
    acc = get(f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}")
    entries = get(f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-puuid/{acc['puuid']}")
    solo = next((e for e in entries if e["queueType"] == "RANKED_SOLO_5x5"), None)
    if solo:
        players.append({"name": f"{name}#{tag}", "tier": solo["tier"], "rank": solo["rank"],
                        "lp": solo["leaguePoints"], "games": solo["wins"] + solo["losses"],
                        "wins": solo["wins"], "score": score(solo["tier"], solo["rank"], solo["leaguePoints"])})
    else:
        players.append({"name": f"{name}#{tag}", "tier": "UNRANKED", "rank": "", "lp": 0,
                        "games": 0, "wins": 0, "score": -1})
    time.sleep(0.2)

players.sort(key=lambda p: p["score"], reverse=True)
with open("data.json", "w", encoding="utf-8") as f:
    json.dump({"updated": datetime.now(timezone.utc).isoformat(), "players": players}, f, ensure_ascii=False, indent=2)
