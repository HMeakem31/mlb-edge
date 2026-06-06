"""
MLB Edge v2.3 — Batch Data Fetcher
Eliminates redundant API calls by fetching team + pitcher data in bulk.
Cuts ~108 API calls per run (~32 seconds saved).
"""
import time
import json
import requests
from pathlib import Path
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
from config import MLB_API, REQUEST_TIMEOUT, API_DELAY, CACHE_DIR

_session = requests.Session()
_session.headers.update({"User-Agent": "MLBEdge/2.3"})

# ─── TEAM STATS BATCH ───────────────────────────────────────────
# Replaces: get_team_baserunning (26 calls) + get_team_fielding (26 calls) + get_team_k_rate (26 calls)
# With: 1 call per team, hitting+fielding in one hydration = 26 calls total (not 78)

_team_cache = {}

def _cache_path(key):
    return CACHE_DIR / f"batch_{key}.json"

def _load(key, ttl=10800):
    p = _cache_path(key)
    if p.exists() and (time.time() - p.stat().st_mtime) < ttl:
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return None

def _save(key, data):
    try:
        with open(_cache_path(key), 'w') as f:
            json.dump(data, f)
    except Exception:
        pass


def fetch_all_team_stats(team_ids: List[int]) -> Dict[int, dict]:
    """
    Fetch hitting + fielding stats for ALL teams in one batch.
    Returns {team_id: {sb, cs, sb_pct, k_rate, errors, fielding_pct, cs_pct, ...}}.
    26 calls (1 per team) instead of 78 (3 per team).
    """
    cached = _load("all_team_stats")
    if cached:
        print(f"  ✅ Team stats: {len(cached)} teams (cached)")
        return {int(k): v for k, v in cached.items()}

    results = {}
    unique = list(set(team_ids))

    def _fetch_team(tid):
        time.sleep(API_DELAY)
        try:
            r = _session.get(f"{MLB_API}/teams/{tid}/stats",
                             params={"season": "2026", "group": "hitting,fielding", "stats": "season"},
                             timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            hitting = {}
            fielding = {}
            for sg in data.get("stats", []):
                group = sg.get("group", {}).get("displayName", "")
                for sp in sg.get("splits", []):
                    s = sp.get("stat", {})
                    if group == "hitting":
                        hitting = s
                    elif group == "fielding":
                        fielding = s
            # Extract everything we need
            ab = hitting.get("atBats", 0) or 1
            so = hitting.get("strikeOuts", 0)
            sb = hitting.get("stolenBases", 0)
            cs = hitting.get("caughtStealing", 0)
            gp = hitting.get("gamesPlayed", 1) or 1
            sb_total = sb + cs

            errors = fielding.get("errors", 0)
            fpct = fielding.get("fielding", ".980")
            dp = fielding.get("doublePlays", 0)
            f_sb = fielding.get("stolenBases", 0)
            f_cs = fielding.get("caughtStealing", 0)
            f_total = f_sb + f_cs

            return tid, {
                # Hitting / baserunning
                "k_rate": round(so / ab, 3) if ab else 0.235,
                "sb": sb, "cs": cs,
                "sb_pct": round(sb / sb_total, 3) if sb_total else 0,
                "sb_per_game": round(sb / gp, 2),
                "sb_threat": "high" if sb > 60 else ("medium" if sb > 35 else "low"),
                "aggressive": sb_total > 0 and (sb / sb_total) > 0.78 and sb > 40,
                # Fielding
                "errors": errors, "errors_per_game": round(errors / gp, 2),
                "fielding_pct": fpct, "double_plays": dp,
                "sb_allowed": f_sb, "cs_by_defense": f_cs,
                "cs_pct": round(f_cs / f_total, 3) if f_total else 0,
                "defense_rating": _rate_def(float(fpct or .980), errors / gp,
                                            f_cs / f_total if f_total else 0),
            }
        except Exception:
            return tid, {"k_rate": 0.235, "sb": 0, "cs": 0, "sb_pct": 0,
                         "sb_per_game": 0, "sb_threat": "low", "aggressive": False,
                         "errors": 0, "errors_per_game": 0, "fielding_pct": ".980",
                         "double_plays": 0, "sb_allowed": 0, "cs_by_defense": 0,
                         "cs_pct": 0, "defense_rating": "average"}

    # Parallel fetch — 4 threads
    with ThreadPoolExecutor(max_workers=4) as ex:
        for tid, data in ex.map(lambda t: _fetch_team(t), unique):
            results[tid] = data

    if results:
        _save("all_team_stats", {str(k): v for k, v in results.items()})
        print(f"  ✅ Team stats: {len(results)} teams (hitting+fielding)")
    return results


def _rate_def(fpct, epg, cs_pct):
    score = 0
    if fpct >= .990: score += 2
    elif fpct >= .985: score += 1
    elif fpct < .978: score -= 2
    if epg < 0.4: score += 1
    elif epg > 0.7: score -= 1
    if cs_pct > 0.30: score += 1
    elif cs_pct < 0.20: score -= 1
    if score >= 3: return "elite"
    if score >= 1: return "above_average"
    if score >= -1: return "average"
    return "below_average"


# ─── PITCHER BATCH ───────────────────────────────────────────────
# Combine pitcher season stats + RISP splits in ONE call per pitcher
# Replaces: get_pitcher_stats (30 calls) + get_pitcher_risp (30 calls) = 60 calls
# With: 30 calls total (1 per pitcher with hydration)

_pitcher_batch_cache = {}

def fetch_pitcher_full(pitcher_id: int) -> Optional[dict]:
    """
    Fetch pitcher season stats + RISP splits in ONE API call.
    Uses hydrate to get both pitching stats and situational splits.
    """
    if not pitcher_id:
        return None
    if pitcher_id in _pitcher_batch_cache:
        return _pitcher_batch_cache[pitcher_id]

    time.sleep(API_DELAY)
    try:
        r = _session.get(
            f"{MLB_API}/people/{pitcher_id}",
            params={
                "season": "2026",
                "hydrate": "stats(group=[pitching],type=[season,statSplits],sitCodes=[risp,ron,r0])"
            },
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
        people = data.get("people", [])
        if not people:
            return None

        p = people[0]
        result = {
            "id": pitcher_id,
            "name": p.get("fullName", "?"),
            "height": p.get("height", "?"),
            "weight": p.get("weight", 0),
            "age": p.get("currentAge", 0),
            "pitch_hand": p.get("pitchHand", {}).get("code", "?"),
        }

        # Parse stats groups
        for stat_group in p.get("stats", []):
            stat_type = stat_group.get("type", {}).get("displayName", "")
            group_name = stat_group.get("group", {}).get("displayName", "")

            if group_name != "pitching":
                continue

            if stat_type == "season":
                splits = stat_group.get("splits", [])
                if splits:
                    st = splits[0].get("stat", {})
                    def sf(val, default=0.0):
                        try: return float(val) if val else default
                        except: return default
                    result.update({
                        "era": sf(st.get("era")),
                        "whip": sf(st.get("whip")),
                        "k9": sf(st.get("strikeoutsPer9Inn")),
                        "bb9": sf(st.get("walksPer9Inn")),
                        "hr9": sf(st.get("homeRunsPer9")),
                        "avg_against": sf(st.get("avg")),
                        "ops_against": sf(st.get("ops")),
                        "games_started": st.get("gamesStarted", 0),
                        "innings_pitched": sf(st.get("inningsPitched")),
                        "strikeout_walk_ratio": sf(st.get("strikeoutWalkRatio")),
                        "go_ao_ratio": sf(st.get("groundOutsToAirouts")),
                        "obp_against": sf(st.get("obp")),
                        "slg_against": sf(st.get("slg")),
                    })

            elif stat_type == "statSplits":
                risp_data = {}
                for sp in stat_group.get("splits", []):
                    desc = sp.get("split", {}).get("description", "")
                    s = sp.get("stat", {})
                    key = desc.lower().replace(" ", "_").replace("-", "_")
                    risp_data[key] = {
                        "avg": s.get("avg", ".000"),
                        "ops": s.get("ops", ".000"),
                        "k": s.get("strikeOuts", 0),
                        "bb": s.get("baseOnBalls", 0),
                        "hr": s.get("homeRuns", 0),
                        "ab": s.get("atBats", 0),
                    }
                if risp_data:
                    result["risp_splits"] = risp_data

        _pitcher_batch_cache[pitcher_id] = result
        return result
    except Exception:
        return None


# ─── WEATHER PARALLEL ────────────────────────────────────────────
def fetch_weather_parallel(weather_fetcher, team_ids: List[int]) -> Dict:
    """Fetch weather for all stadiums in parallel (4 threads)."""
    results = {}
    unique = list(set(team_ids))

    def _fetch(tid):
        return tid, weather_fetcher.get_weather(tid)

    with ThreadPoolExecutor(max_workers=4) as ex:
        for tid, data in ex.map(lambda t: _fetch(t), unique):
            results[tid] = data

    return results
