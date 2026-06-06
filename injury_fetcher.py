"""
MLB Edge v2.3 — Deep Hitter Profile Engine
Season stats + LHP/RHP splits + RISP + home/away + recent form + lineup position + Statcast.
One API call per hitter. Cached. Enriched with Savant xBA/xSLG data.
"""
import time
import requests
from typing import Dict, List, Optional
from config import MLB_API, REQUEST_TIMEOUT, API_DELAY

_session = requests.Session()
_session.headers.update({"User-Agent": "MLBEdge/2.3"})
_cache = {}


def get_hitter_full(player_id: int) -> Optional[dict]:
    """
    Fetch complete hitter profile in ONE API call:
    season stats + vs LHP/RHP + RISP + home/away + last 5 game log.
    """
    if not player_id:
        return None
    if player_id in _cache:
        return _cache[player_id]

    time.sleep(API_DELAY)
    try:
        r = _session.get(f"{MLB_API}/people/{player_id}", params={
            "season": "2026",
            "hydrate": "stats(group=[hitting],type=[season,statSplits,gameLog],sitCodes=[vl,vr,risp,h,a],limit=5)"
        }, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        d = r.json()
        people = d.get("people", [])
        if not people:
            return None

        p = people[0]
        result = {
            "id": player_id,
            "name": p.get("fullName", "?"),
            "height": p.get("height", "?"),
            "weight": p.get("weight", 0),
            "age": p.get("currentAge", 0),
            "bat_side": p.get("batSide", {}).get("code", "?"),
            "position": p.get("primaryPosition", {}).get("abbreviation", "?"),
            "season": {}, "splits": {}, "game_log": [],
        }

        def sf(v, d=0):
            try: return float(v) if v else d
            except: return d

        for sg in p.get("stats", []):
            stype = sg.get("type", {}).get("displayName", "")
            group = sg.get("group", {}).get("displayName", "")
            if group != "hitting":
                continue

            if stype == "season":
                splits = sg.get("splits", [])
                if splits:
                    s = splits[0].get("stat", {})
                    result["season"] = {
                        "avg": s.get("avg", ".000"), "obp": s.get("obp", ".000"),
                        "slg": s.get("slg", ".000"), "ops": s.get("ops", ".000"),
                        "hr": s.get("homeRuns", 0), "rbi": s.get("rbi", 0),
                        "sb": s.get("stolenBases", 0), "ab": s.get("atBats", 0),
                        "hits": s.get("hits", 0), "bb": s.get("baseOnBalls", 0),
                        "so": s.get("strikeOuts", 0), "doubles": s.get("doubles", 0),
                        "pa": s.get("plateAppearances", 0),
                    }

            elif stype == "statSplits":
                for sp in sg.get("splits", []):
                    desc = sp.get("split", {}).get("description", "")
                    s = sp.get("stat", {})
                    key = desc.lower().replace(" ", "_")
                    result["splits"][key] = {
                        "avg": s.get("avg", ".000"), "ops": s.get("ops", ".000"),
                        "slg": s.get("slg", ".000"), "hr": s.get("homeRuns", 0),
                        "ab": s.get("atBats", 0), "rbi": s.get("rbi", 0),
                        "so": s.get("strikeOuts", 0), "hits": s.get("hits", 0),
                    }

            elif stype == "gameLog":
                for gl in sg.get("splits", []):
                    s = gl.get("stat", {})
                    result["game_log"].append({
                        "date": gl.get("date", "?"),
                        "opponent": gl.get("opponent", {}).get("name", "?"),
                        "hits": s.get("hits", 0), "ab": s.get("atBats", 0),
                        "hr": s.get("homeRuns", 0), "rbi": s.get("rbi", 0),
                        "bb": s.get("baseOnBalls", 0), "so": s.get("strikeOuts", 0),
                    })

        _cache[player_id] = result
        return result
    except Exception:
        return None


def get_lineup_from_boxscore(team_id: int, recent_games: list) -> List[dict]:
    """
    Extract batting order from most recent completed game boxscore.
    Returns list of {id, name, position, order} in batting order.
    """
    if not recent_games:
        return []
    # Find most recent game with this team
    game_pk = None
    side = None
    for g in recent_games[:3]:
        away_id = g.get("teams", {}).get("away", {}).get("team", {}).get("id")
        home_id = g.get("teams", {}).get("home", {}).get("team", {}).get("id")
        if away_id == team_id:
            game_pk = g.get("gamePk")
            side = "away"
            break
        elif home_id == team_id:
            game_pk = g.get("gamePk")
            side = "home"
            break

    if not game_pk:
        return []

    time.sleep(API_DELAY)
    try:
        r = _session.get(f"{MLB_API}/game/{game_pk}/boxscore", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        box = r.json()
        team_data = box.get("teams", {}).get(side, {})
        batting_order = team_data.get("battingOrder", [])
        players = team_data.get("players", {})
        lineup = []
        for i, bid in enumerate(batting_order, 1):
            pdata = players.get(f"ID{bid}", {})
            person = pdata.get("person", {})
            lineup.append({
                "id": bid,
                "name": person.get("fullName", "?"),
                "position": pdata.get("position", {}).get("abbreviation", "?"),
                "order": i,
            })
        return lineup
    except Exception:
        return []


def build_hitter_props(team_id: int, team_name: str, opp_pitcher_stats: dict,
                       opp_pitcher_hand: str, batter_expected: dict,
                       recent_games: list, top_n: int = 5) -> List[dict]:
    """
    Build deep hitter prop analysis for a team's top batters.
    Combines: season stats + platoon splits + RISP + recent form + Statcast + lineup position.
    """
    # Get batting order from most recent boxscore
    lineup = get_lineup_from_boxscore(team_id, recent_games)
    if not lineup:
        return []

    # Pitcher profile for matchup
    pitcher_hr9 = float(opp_pitcher_stats.get("hr9", 1.0) or 1.0) if opp_pitcher_stats else 1.0
    pitcher_go_ao = float(opp_pitcher_stats.get("go_ao_ratio", 1.0) or 1.0) if opp_pitcher_stats else 1.0
    pitcher_hand = opp_pitcher_hand or "R"
    pitcher_k9 = float(opp_pitcher_stats.get("k9", 8.0) or 8.0) if opp_pitcher_stats else 8.0
    is_flyball = pitcher_go_ao < 0.90

    props = []
    for batter in lineup[:4]:  # top 9 in order
        pid = batter["id"]
        profile = get_hitter_full(pid)
        if not profile or not profile.get("season", {}).get("ab", 0):
            continue

        season = profile["season"]
        splits = profile["splits"]
        game_log = profile.get("game_log", [])
        savant = batter_expected.get(pid, {})

        ab = season.get("ab", 0)
        if ab < 20:
            continue

        # ── Build prop score ──
        score = 0
        reasons = []
        flags = []

        # 1. Platoon advantage
        split_key = "vs_left" if pitcher_hand == "L" else "vs_right"
        plat = splits.get(split_key, {})
        plat_ops = float(plat.get("ops", ".000").replace(",", "") or 0)
        season_ops = float(season.get("ops", ".000").replace(",", "") or 0)
        if plat_ops > season_ops + 0.050 and plat.get("ab", 0) >= 15:
            score += 2
            reasons.append(f"Platoon edge: .{plat['ops'].replace('.','')[:3]} OPS vs {pitcher_hand}HP (season .{season['ops'].replace('.','')[:3]})")
        elif plat_ops > season_ops and plat.get("ab", 0) >= 15:
            score += 1
            reasons.append(f"vs {pitcher_hand}HP: .{plat['ops'].replace('.','')[:3]} OPS")

        # 2. RISP clutch
        risp = splits.get("scoring_position", {})
        risp_avg = float(risp.get("avg", ".000").replace(",", "") or 0)
        season_avg = float(season.get("avg", ".000").replace(",", "") or 0)
        if risp_avg > 0.300 and risp.get("ab", 0) >= 10:
            score += 1
            reasons.append(f"RISP: .{risp['avg'].replace('.','')[:3]} AVG ({risp.get('rbi',0)} RBI)")

        # 3. Recent form (last 5 games)
        if game_log:
            recent_hits = sum(g.get("hits", 0) for g in game_log[:5])
            recent_ab = sum(g.get("ab", 0) for g in game_log[:5])
            recent_hr = sum(g.get("hr", 0) for g in game_log[:5])
            if recent_ab >= 10:
                recent_avg = recent_hits / recent_ab
                if recent_avg > 0.300:
                    score += 2
                    flags.append("🔥 HOT")
                    reasons.append(f"Last 5: {recent_hits}/{recent_ab} (.{str(round(recent_avg,3)).replace('0.','')[:3]})")
                elif recent_avg > 0.250:
                    score += 1
                    reasons.append(f"Last 5: {recent_hits}/{recent_ab} (.{str(round(recent_avg,3)).replace('0.','')[:3]})")
                elif recent_avg < 0.150:
                    score -= 1
                    flags.append("❄️ COLD")
                    reasons.append(f"Last 5: {recent_hits}/{recent_ab} — slumping")
                if recent_hr >= 2:
                    flags.append("💣 Power surge")
                    reasons.append(f"Last 5: {recent_hr} HR")

        # 4. Statcast xBA regression
        if savant:
            ba = savant.get("ba", 0) or 0
            xba = savant.get("xba", 0) or 0
            xslg = savant.get("xslg", 0) or 0
            slg = savant.get("slg", 0) or 0
            if xba and ba and xba - ba > 0.020:
                score += 1
                reasons.append(f"Statcast: xBA .{str(xba).replace('0.','')[:3]} > BA .{str(ba).replace('0.','')[:3]} (unlucky)")
            if xslg and slg and xslg - slg > 0.030:
                reasons.append(f"Power due: xSLG .{str(xslg).replace('0.','')[:3]} > SLG .{str(slg).replace('0.','')[:3]}")

        # 5. HR opportunity
        hr_opp = False
        hr_reasons = []
        if is_flyball:
            hr_reasons.append(f"Fly ball pitcher (GO/AO {pitcher_go_ao:.2f})")
        if pitcher_hr9 > 1.3:
            hr_reasons.append(f"HR-prone ({pitcher_hr9:.1f} HR/9)")
        if savant.get("xslg") and savant["xslg"] > 0.480:
            hr_reasons.append(f"Elite xSLG .{str(savant['xslg']).replace('0.','')[:3]}")
        if season.get("hr", 0) >= 10:
            hr_reasons.append(f"{season['hr']} HR this season")
        if len(hr_reasons) >= 2:
            hr_opp = True
            score += 1

        # 6. Lineup position value
        order = batter.get("order", 9)
        if order <= 3:
            score += 1
            reasons.append(f"Bats #{order} — premium lineup spot")
        elif order <= 5:
            reasons.append(f"Bats #{order} — middle of order")

        # ── Recommendation ──
        if score < 2:
            continue  # not interesting enough

        if hr_opp and score >= 3:
            rec = "Hits OVER + HR Watch"
        elif hr_opp:
            rec = "HR Watch"
        elif score >= 4:
            rec = "Hits OVER"
        elif score >= 3:
            rec = "Hits OVER (lean)"
        else:
            rec = "Monitor"

        confidence = "high" if score >= 4 else ("medium" if score >= 3 else "low")

        props.append({
            "player_id": pid,
            "name": profile["name"],
            "position": profile["position"],
            "bat_side": profile["bat_side"],
            "order": order,
            "season_avg": season.get("avg", "?"),
            "season_ops": season.get("ops", "?"),
            "season_hr": season.get("hr", 0),
            "platoon_ops": plat.get("ops", "?") if plat.get("ab", 0) >= 10 else "N/A",
            "risp_avg": risp.get("avg", "?") if risp.get("ab", 0) >= 5 else "N/A",
            "recent_form": f"{recent_hits}/{recent_ab}" if game_log and recent_ab >= 10 else "N/A",
            "xba": savant.get("xba"),
            "xslg": savant.get("xslg"),
            "score": score,
            "reasons": reasons,
            "flags": flags,
            "hr_opportunity": hr_opp,
            "hr_reasons": hr_reasons,
            "recommendation": rec,
            "confidence": confidence,
        })

    props.sort(key=lambda x: x["score"], reverse=True)
    return props[:top_n]
