"""
MLB Edge v2.3 — Player Prop Engine
Pitcher K props + hitter hit props from existing data. Zero extra API calls.
"""
import requests
import time
from typing import Dict, List, Optional
from config import MLB_API, REQUEST_TIMEOUT, API_DELAY

_session = requests.Session()
_session.headers.update({"User-Agent": "MLBEdge/2.3"})
_roster_cache = {}


def get_lineup(team_id: int) -> List[dict]:
    """Get today's starting lineup with player IDs. 1 API call, cached."""
    if team_id in _roster_cache:
        return _roster_cache[team_id]
    time.sleep(API_DELAY)
    try:
        r = _session.get(f"{MLB_API}/teams/{team_id}/roster",
                         params={"rosterType": "active", "season": "2026"},
                         timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        players = []
        for p in data.get("roster", []):
            pos = p.get("position", {}).get("abbreviation", "")
            if pos == "P":
                continue  # skip pitchers
            person = p.get("person", {})
            players.append({
                "id": person.get("id"),
                "name": person.get("fullName", "?"),
                "position": pos,
                "bat_side": person.get("batSide", {}).get("code", "?"),
            })
        _roster_cache[team_id] = players
        return players
    except Exception:
        return []


def calculate_k_prop(pitcher_stats: dict, opp_team_k_rate: float,
                     pitcher_name: str = "") -> Optional[dict]:
    """
    Project pitcher strikeout total from K/9 vs opposing team K rate.
    pitcher_stats: from PitcherAnalyzer.get_pitcher_stats()
    opp_team_k_rate: opposing team's K/AB rate (0-1)
    """
    if not pitcher_stats:
        return None

    k9 = float(pitcher_stats.get("k9", 0) or 0)
    ip = float(pitcher_stats.get("innings_pitched", 0) or 0)
    gs = pitcher_stats.get("games_started", 0) or 1

    if ip < 10 or k9 < 3:
        return None

    ip_per_start = ip / max(1, gs)

    # Project K per start: K/9 * estimated innings * opponent K rate modifier
    league_avg_k_rate = 0.235  # ~23.5% K rate league average
    k_rate_modifier = opp_team_k_rate / league_avg_k_rate if league_avg_k_rate > 0 else 1.0

    # Expected innings (cap at 6 for projection)
    proj_ip = min(6.0, ip_per_start)

    # Projected Ks
    proj_k = (k9 / 9) * proj_ip * k_rate_modifier
    proj_k = round(proj_k, 1)

    # Determine the likely prop line (typically 0.5 increments)
    likely_line = round(proj_k * 2) / 2  # round to nearest 0.5

    # Confidence based on sample + projection strength
    if proj_k >= likely_line + 0.5 and k9 >= 9.0 and opp_team_k_rate > 0.24:
        confidence = "high"
        rec = "OVER"
    elif proj_k >= likely_line + 0.3:
        confidence = "medium"
        rec = "OVER"
    elif proj_k <= likely_line - 0.5 and k9 < 7.5:
        confidence = "medium"
        rec = "UNDER"
    else:
        confidence = "low"
        rec = "NO EDGE"

    return {
        "pitcher": pitcher_name or pitcher_stats.get("name", "?"),
        "k9": k9,
        "proj_ip": round(proj_ip, 1),
        "opp_k_rate": round(opp_team_k_rate, 3),
        "proj_k": proj_k,
        "likely_line": likely_line,
        "recommendation": rec,
        "confidence": confidence,
        "k_rate_modifier": round(k_rate_modifier, 2),
    }


def get_team_k_rate(team_id: int) -> float:
    """Get team's strikeout rate (K/AB). 1 API call, uses existing team stats."""
    try:
        time.sleep(API_DELAY)
        r = _session.get(f"{MLB_API}/teams/{team_id}/stats",
                         params={"season": "2026", "group": "hitting", "stats": "season"},
                         timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        d = r.json()
        for sg in d.get("stats", []):
            for sp in sg.get("splits", []):
                s = sp.get("stat", {})
                ab = s.get("atBats", 0)
                so = s.get("strikeOuts", 0)
                return so / ab if ab > 0 else 0.235
    except Exception:
        pass
    return 0.235  # league average fallback


def find_hot_hitters(team_id: int, batter_expected: dict,
                     opp_pitcher_xwoba: float = None,
                     opp_pitcher_stats: dict = None) -> List[dict]:
    """
    Find the best hitter props for today using Statcast expected stats.
    Identifies batters whose xBA > BA (unlucky — due for regression UP).
    Also identifies HR opportunities based on pitcher fly ball tendency.
    """
    lineup = get_lineup(team_id)
    hot = []

    # Pitcher fly ball / ground ball tendency for HR analysis
    pitcher_fb_pitcher = False
    pitcher_hr9 = 0
    pitcher_go_ao = 999
    if opp_pitcher_stats:
        pitcher_hr9 = float(opp_pitcher_stats.get("hr9", 1.0) or 1.0)
        pitcher_go_ao = float(opp_pitcher_stats.get("go_ao_ratio", 1.0) or 1.0)
        pitcher_fb_pitcher = pitcher_go_ao < 0.90  # fly ball pitcher
    
    for player in lineup[:12]:  # top 12 position players
        pid = player.get("id")
        if not pid or pid not in batter_expected:
            continue

        bx = batter_expected[pid]
        ba = bx.get("ba")
        xba = bx.get("xba")
        woba = bx.get("woba")
        xwoba = bx.get("xwoba")
        slg = bx.get("slg")
        xslg = bx.get("xslg")
        pa = bx.get("pa", 0)

        if not ba or not xba or pa < 50:
            continue

        luck = round(xba - ba, 3)  # positive = unlucky
        woba_luck = round((xwoba or 0) - (woba or 0), 3)
        slg_luck = round((xslg or 0) - (slg or 0), 3) if xslg and slg else 0

        # Score: how likely is this hitter to exceed expectations?
        score = 0
        reasons = []

        # Hit prop signals
        if luck > 0.020:
            score += 2
            reasons.append(f"xBA {xba:.3f} > BA {ba:.3f} (unlucky +{luck:.3f})")
        elif luck > 0.010:
            score += 1
            reasons.append(f"xBA slightly above BA (+{luck:.3f})")

        if woba_luck > 0.020:
            score += 1
            reasons.append(f"xwOBA {xwoba:.3f} > wOBA {woba:.3f}")

        # Facing weak pitcher
        if opp_pitcher_xwoba and opp_pitcher_xwoba > 0.320:
            score += 1
            reasons.append(f"vs weak SP (xwOBA against {opp_pitcher_xwoba:.3f})")

        # HR opportunity analysis
        hr_opportunity = False
        hr_reasons = []
        if slg_luck > 0.030:
            hr_reasons.append(f"xSLG {xslg:.3f} > SLG {slg:.3f} — power due")
        if pitcher_fb_pitcher:
            hr_reasons.append(f"vs fly ball pitcher (GO/AO {pitcher_go_ao:.2f})")
        if pitcher_hr9 > 1.3:
            hr_reasons.append(f"vs HR-prone pitcher ({pitcher_hr9:.1f} HR/9)")
        if xslg and xslg > 0.480:
            hr_reasons.append(f"Elite power: xSLG {xslg:.3f}")

        if len(hr_reasons) >= 2:
            hr_opportunity = True
            score += 1
            reasons.append("🏠 HR opportunity: " + " + ".join(hr_reasons[:2]))

        if score >= 2:
            rec = "Hits OVER"
            if hr_opportunity and slg_luck > 0.020:
                rec = "Hits OVER + HR Watch"
            elif hr_opportunity:
                rec = "HR Watch"

            hot.append({
                "player_id": pid,
                "name": bx.get("name", player.get("name", "?")),
                "position": player.get("position", "?"),
                "ba": ba, "xba": xba,
                "slg": slg, "xslg": xslg,
                "woba": woba, "xwoba": xwoba,
                "luck_gap": luck,
                "score": score,
                "reasons": reasons,
                "recommendation": rec,
                "confidence": "high" if score >= 3 else "medium",
                "hr_opportunity": hr_opportunity,
                "hr_reasons": hr_reasons,
                "pa": pa,
            })

    hot.sort(key=lambda x: x["score"], reverse=True)
    return hot[:5]  # top 5


def build_game_props(game: dict, away_id: int, home_id: int,
                     away_pitcher_stats: dict, home_pitcher_stats: dict,
                     pitcher_expected: dict, batter_expected: dict) -> dict:
    """
    Build all prop projections for a game.
    Returns dict with k_props and hit_props.
    """
    # K Props: each starter vs opposing team K rate
    away_k_rate = get_team_k_rate(away_id)
    home_k_rate = get_team_k_rate(home_id)

    away_k_prop = calculate_k_prop(
        home_pitcher_stats, away_k_rate,
        game.get("home_pitcher_name", "")
    )
    home_k_prop = calculate_k_prop(
        away_pitcher_stats, home_k_rate,
        game.get("away_pitcher_name", "")
    )

    # Hit props: find unlucky batters facing weak pitchers
    away_pitcher_xwoba = None
    home_pitcher_xwoba = None
    if game.get("away_pitcher_id") and game["away_pitcher_id"] in pitcher_expected:
        away_pitcher_xwoba = pitcher_expected[game["away_pitcher_id"]].get("xwoba")
    if game.get("home_pitcher_id") and game["home_pitcher_id"] in pitcher_expected:
        home_pitcher_xwoba = pitcher_expected[game["home_pitcher_id"]].get("xwoba")

    # Home batters vs away pitcher
    home_hot = find_hot_hitters(home_id, batter_expected, away_pitcher_xwoba)
    # Away batters vs home pitcher
    away_hot = find_hot_hitters(away_id, batter_expected, home_pitcher_xwoba)

    return {
        "k_props": {
            "home_pitcher": away_k_prop,  # home pitcher's K prop (facing away batters)
            "away_pitcher": home_k_prop,  # away pitcher's K prop (facing home batters)
        },
        "hit_props": {
            "home_hitters": home_hot,
            "away_hitters": away_hot,
        },
    }
