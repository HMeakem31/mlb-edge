"""
MLB Edge v2.3 — Matchup Engine
Advanced analytics: RISP splits, stolen bases, defense, shadows, physicals.
All from free MLB Stats API — zero signup, zero keys.
"""
import math
import requests
import time
from datetime import datetime
from typing import Dict, Optional, List
from config import MLB_API, REQUEST_TIMEOUT, API_DELAY, STADIUM_CF_AZIMUTH, STADIUM_COORDS

_session = requests.Session()
_session.headers.update({"User-Agent": "MLBEdge/2.3"})
_cache = {}

def _get(url, params=None, cache_key=None):
    if cache_key and cache_key in _cache:
        return _cache[cache_key]
    time.sleep(API_DELAY)
    try:
        r = _session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if cache_key:
            _cache[cache_key] = data
        return data
    except Exception:
        return {}


# ─── RISP + CLUTCH SPLITS ───────────────────────────────────────
def get_pitcher_risp(pitcher_id: int) -> Optional[Dict]:
    """Get pitcher stats with runners in scoring position. 1 API call."""
    if not pitcher_id:
        return None
    ck = f"p_risp_{pitcher_id}"
    data = _get(
        f"{MLB_API}/people/{pitcher_id}/stats",
        {"stats": "statSplits", "group": "pitching", "season": "2026",
         "sitCodes": "risp,ron,r0"},
        ck
    )
    result = {}
    for sg in data.get("stats", []):
        for sp in sg.get("splits", []):
            desc = sp.get("split", {}).get("description", "")
            s = sp.get("stat", {})
            key = desc.lower().replace(" ", "_").replace("-", "_")
            result[key] = {
                "avg": s.get("avg", ".000"),
                "ops": s.get("ops", ".000"),
                "whip": s.get("whip", "0.00"),
                "k": s.get("strikeOuts", 0),
                "bb": s.get("baseOnBalls", 0),
                "hr": s.get("homeRuns", 0),
                "ab": s.get("atBats", 0),
            }
    return result if result else None


def get_hitter_risp(hitter_id: int) -> Optional[Dict]:
    """Get hitter stats with RISP + home/away + late/close. 1 API call."""
    if not hitter_id:
        return None
    ck = f"h_risp_{hitter_id}"
    data = _get(
        f"{MLB_API}/people/{hitter_id}/stats",
        {"stats": "statSplits", "group": "hitting", "season": "2026",
         "sitCodes": "risp,lc,h,a"},
        ck
    )
    result = {}
    for sg in data.get("stats", []):
        for sp in sg.get("splits", []):
            desc = sp.get("split", {}).get("description", "")
            s = sp.get("stat", {})
            key = desc.lower().replace(" ", "_").replace("/", "_")
            result[key] = {
                "avg": s.get("avg", ".000"),
                "ops": s.get("ops", ".000"),
                "hr": s.get("homeRuns", 0),
                "rbi": s.get("rbi", 0),
                "sb": s.get("stolenBases", 0),
                "ab": s.get("atBats", 0),
            }
    return result if result else None


# ─── TEAM STOLEN BASE + DEFENSE ─────────────────────────────────
def get_team_baserunning(team_id: int) -> Dict:
    """Team stolen base stats (offense). 1 API call."""
    ck = f"t_br_{team_id}"
    data = _get(
        f"{MLB_API}/teams/{team_id}/stats",
        {"season": "2026", "group": "hitting", "stats": "season"},
        ck
    )
    for sg in data.get("stats", []):
        for sp in sg.get("splits", []):
            s = sp.get("stat", {})
            sb = s.get("stolenBases", 0)
            cs = s.get("caughtStealing", 0)
            total = sb + cs
            pct = sb / total if total > 0 else 0
            return {
                "sb": sb, "cs": cs, "sb_pct": round(pct, 3),
                "sb_per_game": round(sb / max(1, s.get("gamesPlayed", 1)), 2),
                "aggressive": pct > 0.78 and sb > 40,
                "threat_level": "high" if sb > 60 else ("medium" if sb > 35 else "low"),
            }
    return {"sb": 0, "cs": 0, "sb_pct": 0, "sb_per_game": 0,
            "aggressive": False, "threat_level": "low"}


def get_team_fielding(team_id: int) -> Dict:
    """Team defensive metrics. 1 API call."""
    ck = f"t_fld_{team_id}"
    data = _get(
        f"{MLB_API}/teams/{team_id}/stats",
        {"season": "2026", "group": "fielding", "stats": "season"},
        ck
    )
    for sg in data.get("stats", []):
        for sp in sg.get("splits", []):
            s = sp.get("stat", {})
            errors = s.get("errors", 0)
            fpct = s.get("fielding", ".980")
            dp = s.get("doublePlays", 0)
            sb_allowed = s.get("stolenBases", 0)
            cs_by = s.get("caughtStealing", 0)
            sb_total = sb_allowed + cs_by
            cs_pct = cs_by / sb_total if sb_total > 0 else 0
            gp = s.get("gamesPlayed", 1) or 1
            return {
                "errors": errors, "errors_per_game": round(errors / gp, 2),
                "fielding_pct": fpct, "double_plays": dp,
                "sb_allowed": sb_allowed, "cs_by_defense": cs_by,
                "cs_pct": round(cs_pct, 3),
                "defense_rating": _rate_defense(float(fpct or .980), errors / gp, cs_pct),
            }
    return {"errors": 0, "errors_per_game": 0, "fielding_pct": ".980",
            "double_plays": 0, "sb_allowed": 0, "cs_by_defense": 0,
            "cs_pct": 0, "defense_rating": "average"}


def _rate_defense(fpct, epg, cs_pct):
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


# ─── SHADOW IMPACT ───────────────────────────────────────────────
def calculate_shadow_impact(team_id: int, game_time_str: str) -> Dict:
    """
    Estimate shadow impact on batting visibility.
    Day games (before 5pm local) with sun angles 15-30° create shadows.
    Afternoon shadows cross the field and reduce batting avg ~.010-.015.
    """
    coords = STADIUM_COORDS.get(team_id)
    if not coords:
        return {"impact": "none", "detail": "No stadium data", "run_adj": 0}

    lat = coords[0]
    cf_az = STADIUM_CF_AZIMUTH.get(team_id, 180)

    # Parse game time — crude but functional
    try:
        # Handle various formats
        t = game_time_str.upper().replace(".", "")
        hour = None
        if "PM" in t or "AM" in t:
            parts = t.replace("PM", "").replace("AM", "").replace("ET", "").strip()
            h, m = parts.split(":") if ":" in parts else (parts, "0")
            hour = int(h)
            if "PM" in t and hour != 12:
                hour += 12
            if "AM" in t and hour == 12:
                hour = 0
        elif "T" in t:
            # ISO format
            tp = t.split("T")[1][:2]
            hour = int(tp)
        if hour is None:
            return {"impact": "none", "detail": "Unknown game time", "run_adj": 0}
    except Exception:
        return {"impact": "none", "detail": "Parse error", "run_adj": 0}

    # Night game = no shadow impact
    if hour >= 19 or hour < 12:
        return {"impact": "none", "detail": "Night game", "run_adj": 0}

    # Day game or afternoon game
    # Sun angle at game time (rough estimate based on month and latitude)
    month = datetime.now().month
    # In June, sun is high (50-70° at noon), drops to 15-25° by 5-6pm
    # Shadows become a factor when sun is 15-30° (last 2-3 hours before sunset)
    if 12 <= hour <= 14:
        # Early afternoon — sun high, minimal shadow
        impact = "minimal"
        detail = "Sun high, limited shadow effect"
        run_adj = -0.05
    elif 14 < hour <= 16:
        # Mid-afternoon — shadows starting to cross field
        # Stadiums facing NE have shadows from 3B side
        impact = "moderate"
        detail = "Shadows crossing field — batter visibility reduced"
        run_adj = -0.15
    elif 16 < hour < 19:
        # Late afternoon — peak shadow effect
        # This is where day games get tricky
        impact = "significant"
        detail = "Long shadows across batter's box — pitcher advantage"
        run_adj = -0.25
    else:
        impact = "none"
        detail = ""
        run_adj = 0

    # Dome/retractable — no shadows
    from config import DOME_STADIUMS, RETRACTABLE_ROOF
    if team_id in DOME_STADIUMS:
        return {"impact": "none", "detail": "Dome", "run_adj": 0}
    if team_id in RETRACTABLE_ROOF:
        impact = "possible"
        detail += " (retractable roof — may be closed)"
        run_adj *= 0.5

    # Compute which innings have shadow impact based on game time
    # Game starts at ~hour:00. Each inning ≈ 25-30 min.
    shadow_inning_ranges = []
    if impact == "significant":
        # Late afternoon: shadows peak innings 5-9
        start_inning = max(1, int((hour - 12) * 2 - 6))
        shadow_inning_ranges.append(f"Innings 5-9 (peak shadow, ~{hour+1}:00-{hour+3}:00)")
    elif impact == "moderate":
        shadow_inning_ranges.append(f"Innings 3-6 (crossing field, ~{hour+0.5:.0f}:30-{hour+2.0:.0f}:00)")
    elif impact == "minimal":
        shadow_inning_ranges.append("Minimal — sun high, shadows short")
    
    return {
        "impact": impact,
        "detail": detail,
        "run_adj": round(run_adj, 2),
        "game_hour": hour,
        "is_day_game": hour < 18,
        "innings_range": " · ".join(shadow_inning_ranges) if shadow_inning_ranges else "Night game — no shadow impact",
    }


# ─── AGGREGATE MATCHUP PROFILE ──────────────────────────────────
def build_matchup_extras(game: dict, away_id: int, home_id: int,
                         away_pitcher_id: int, home_pitcher_id: int) -> Dict:
    """
    Build all advanced matchup data in minimum API calls.
    Returns a dict with all extras to attach to the game record.
    """
    # Pitcher RISP (2 calls)
    away_p_risp = get_pitcher_risp(away_pitcher_id)
    home_p_risp = get_pitcher_risp(home_pitcher_id)

    # Team baserunning (2 calls, cached)
    away_br = get_team_baserunning(away_id)
    home_br = get_team_baserunning(home_id)

    # Team fielding (2 calls, cached)
    away_fld = get_team_fielding(away_id)
    home_fld = get_team_fielding(home_id)

    # Shadow impact (0 calls — pure math)
    game_time = game.get("game_time", "")
    shadow = calculate_shadow_impact(home_id, game_time)

    # Stolen base matchup: team speed vs opposing defense
    sb_matchup = {
        "away_sb_threat": away_br.get("threat_level", "low"),
        "home_cs_defense": home_fld.get("cs_pct", 0),
        "home_sb_threat": home_br.get("threat_level", "low"),
        "away_cs_defense": away_fld.get("cs_pct", 0),
        "sb_edge": _sb_edge(away_br, home_fld, home_br, away_fld),
    }

    return {
        "away_pitcher_risp": away_p_risp,
        "home_pitcher_risp": home_p_risp,
        "away_baserunning": away_br,
        "home_baserunning": home_br,
        "away_fielding": away_fld,
        "home_fielding": home_fld,
        "shadow": shadow,
        "sb_matchup": sb_matchup,
    }


def _sb_edge(a_br, h_fld, h_br, a_fld):
    """Who has the baserunning edge? Returns 'away'/'home'/'even'."""
    a_score = 0
    h_score = 0
    # Away team's speed vs home defense
    if a_br.get("aggressive"):
        a_score += 1
    if h_fld.get("cs_pct", 0) < 0.22:
        a_score += 1  # home can't throw out runners
    # Home team's speed vs away defense
    if h_br.get("aggressive"):
        h_score += 1
    if a_fld.get("cs_pct", 0) < 0.22:
        h_score += 1
    if a_score > h_score:
        return "away"
    if h_score > a_score:
        return "home"
    return "even"


def format_extras_for_report(extras: Dict, away_name: str, home_name: str) -> Dict:
    """Format extras into display-ready strings."""
    parts = {}

    # RISP
    for side, key, name in [("away", "away_pitcher_risp", away_name),
                             ("home", "home_pitcher_risp", home_name)]:
        risp = extras.get(key, {})
        if risp and risp.get("scoring_position"):
            sp = risp["scoring_position"]
            parts[f"{side}_risp"] = f'.{sp["avg"].replace(".", "")} AVG / .{sp["ops"].replace(".", "")} OPS w/ RISP'

    # Defense
    for side, key, name in [("away", "away_fielding", away_name),
                             ("home", "home_fielding", home_name)]:
        fld = extras.get(key, {})
        parts[f"{side}_def"] = (
            f'{fld.get("defense_rating", "?").replace("_", " ").title()} '
            f'({fld.get("fielding_pct", "?")} FPct, '
            f'{fld.get("errors_per_game", 0):.1f} E/G, '
            f'{fld.get("cs_pct", 0):.0%} CS)'
        )

    # Baserunning
    for side, key, name in [("away", "away_baserunning", away_name),
                             ("home", "home_baserunning", home_name)]:
        br = extras.get(key, {})
        parts[f"{side}_sb"] = (
            f'{br.get("sb", 0)} SB ({br.get("sb_pct", 0):.0%}) · '
            f'{br.get("sb_per_game", 0):.1f}/G · '
            f'Threat: {br.get("sb_threat", br.get("threat_level", "?")).title()}'
        )

    # Shadow
    sh = extras.get("shadow", {})
    if sh.get("impact") not in ("none", None):
        parts["shadow"] = f'{sh["impact"].title()} — {sh.get("detail", "")}'
        if sh.get("run_adj", 0) != 0:
            parts["shadow"] += f' ({sh["run_adj"]:+.2f}R)'
        ir = sh.get("innings_range", "")
        if ir:
            parts["shadow"] += f'<br><span style="font-size:0.68rem;color:var(--muted)">📅 {ir}</span>'

    return parts
