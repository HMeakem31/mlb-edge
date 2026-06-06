"""
MLB Edge v2.0 — Advanced Analytics Engine
Calculates bullpen fatigue, recent trends, BvP edges, and composite game scores.
"""
from typing import Dict, List, Optional

def extract_team_stats_from_game(game: dict, team_id: int) -> dict:
    """Extract batting and pitching stats from a single game's linescore."""
    teams = game.get("teams", {})
    side = "away" if teams.get("away", {}).get("team", {}).get("id") == team_id else "home"
    team_data = teams.get(side, {})
    
    runs = team_data.get("runs", 0) or 0
    hits = team_data.get("hits", 0) or 0
    errors = team_data.get("errors", 0) or 0
    
    # Get opposing team's runs (for ERA calculation)
    opp_side = "home" if side == "away" else "away"
    opp_runs = teams.get(opp_side, {}).get("runs", 0) or 0
    
    linescore = game.get("linescore", {})
    innings = linescore.get("innings", [])
    total_innings = len(innings) if innings else 9
    
    return {
        "runs": runs,
        "hits": hits,
        "errors": errors,
        "earned_runs_against": opp_runs,
        "innings_pitched": total_innings,
        "side": side,
    }

def calculate_bullpen_fatigue(recent_games: list, team_id: int) -> Dict:
    """
    Calculate bullpen fatigue from recent games using linescore data.
    If starter went < 6 innings, bullpen was used more heavily.
    Proxy: total relief innings across recent games.
    """
    if not recent_games:
        return {"total_ip": 0, "fatigue_score": 0, "relievers_used": 0,
                "high_leverage_ip": 0, "back_to_back": False, "status": "unknown"}
    
    total_relief_ip = 0
    games_analyzed = 0
    high_leverage_ip = 0
    
    for game in recent_games:
        try:
            stats = extract_team_stats_from_game(game, team_id)
            innings = stats.get("innings_pitched", 9)
            
            # Estimate: starter typically goes 5-6 innings
            # Anything beyond that is bullpen
            starter_ip = min(5.5, innings)
            relief_ip = max(0, innings - starter_ip)
            total_relief_ip += relief_ip
            games_analyzed += 1
            
            # Extra innings = extra bullpen usage
            if innings > 9:
                extra = innings - 9
                total_relief_ip += extra
                high_leverage_ip += extra
        except Exception:
            continue
    
    # REALISTIC scaling: 15+ relief IP over 3 games = tired
    avg_relief_per_game = total_relief_ip / max(1, games_analyzed)
    fatigue_score = min(100, (avg_relief_per_game / 5) * 100)  # 5 relief IP/game = 100%
    
    if fatigue_score < 25:
        status = "fresh"
    elif fatigue_score < 45:
        status = "moderate"
    elif fatigue_score < 65:
        status = "tired"
    else:
        status = "exhausted"
    
    return {
        "total_ip": round(total_relief_ip, 1),
        "fatigue_score": round(fatigue_score, 1),
        "relievers_used": games_analyzed,
        "high_leverage_ip": round(high_leverage_ip, 1),
        "back_to_back": False,
        "status": status,
    }

def calculate_recent_trends(recent_games: list, team_id: int) -> Dict:
    """Calculate recent offensive and pitching trends from last N games."""
    if not recent_games:
        return {"games_analyzed": 0, "runs_per_game": 0, "hits_per_game": 0,
                "era": 0, "win_pct": 0, "last_3_runs": 0, "last_3_era": 0,
                "trend": "unknown", "last_3_record": "0-0"}
    
    total_runs = 0
    total_hits = 0
    total_earned_runs_against = 0
    total_innings = 0
    wins = 0
    losses = 0
    last_3_runs = 0
    last_3_era_runs = 0
    last_3_wins = 0
    last_3_losses = 0
    
    for i, game in enumerate(recent_games):
        try:
            stats = extract_team_stats_from_game(game, team_id)
            runs = stats.get("runs", 0)
            hits = stats.get("hits", 0)
            era_runs = stats.get("earned_runs_against", 0)
            innings = stats.get("innings_pitched", 9)
            
            total_runs += runs
            total_hits += hits
            total_earned_runs_against += era_runs
            total_innings += innings
            
            if i < 3:
                last_3_runs += runs
                last_3_era_runs += era_runs
            
            # Win/loss from linescore
            if runs > era_runs:
                wins += 1
                if i < 3:
                    last_3_wins += 1
            elif runs < era_runs:
                losses += 1
                if i < 3:
                    last_3_losses += 1
        except Exception:
            continue
    
    games_analyzed = len(recent_games)
    runs_per_game = total_runs / games_analyzed if games_analyzed > 0 else 0
    hits_per_game = total_hits / games_analyzed if games_analyzed > 0 else 0
    era = (total_earned_runs_against / total_innings * 9) if total_innings > 0 else 0
    win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.5
    last_3_rpg = last_3_runs / 3 if games_analyzed >= 3 else last_3_runs / max(1, games_analyzed)
    last_3_era = (last_3_era_runs / (3 * 9) * 9) if games_analyzed >= 3 else (last_3_era_runs / max(1, total_innings) * 9)
    last_3_record = f"{last_3_wins}-{last_3_losses}"
    
    # Trend determination
    if runs_per_game >= 5.5 and era <= 3.5:
        trend = "hot"
    elif runs_per_game >= 4.5 and era <= 4.0:
        trend = "warm"
    elif runs_per_game >= 3.8 and era <= 4.5:
        trend = "neutral"
    elif runs_per_game >= 3.0:
        trend = "cold"
    else:
        trend = "ice_cold"
    
    return {
        "games_analyzed": games_analyzed,
        "runs_per_game": round(runs_per_game, 2),
        "hits_per_game": round(hits_per_game, 2),
        "era": round(era, 2),
        "win_pct": round(win_pct, 3),
        "last_3_runs": round(last_3_rpg, 2),
        "last_3_era": round(last_3_era, 2),
        "last_3_record": last_3_record,
        "trend": trend,
    }

def analyze_bvp(bvp_data: list, pitcher_id: int = None) -> Dict:
    """Analyze batter vs pitcher matchups."""
    if not bvp_data:
        return {"total_pa": 0, "avg": 0, "obp": 0, "slg": 0, "ops": 0,
                "strikeouts": 0, "walks": 0, "home_runs": 0, "edge": "no_data"}
    
    total_pa = 0
    total_hits = 0
    total_bb = 0
    total_so = 0
    total_hr = 0
    total_bases = 0
    
    for matchup in bvp_data:
        data = matchup.get("data", {})
        try:
            stats = data.get("people", [{}])[0].get("stats", {})
            hitting = stats.get("group", [{}])[0].get("stats", {})
            pa = hitting.get("atBats", 0) + hitting.get("baseOnBalls", 0) + hitting.get("hitByPitch", 0)
            hits = hitting.get("hits", 0)
            bb = hitting.get("baseOnBalls", 0)
            so = hitting.get("strikeOuts", 0)
            hr = hitting.get("homeRuns", 0)
            tb = hitting.get("totalBases", 0)
            total_pa += pa
            total_hits += hits
            total_bb += bb
            total_so += so
            total_hr += hr
            total_bases += tb
        except Exception:
            continue
    
    if total_pa == 0:
        return {"total_pa": 0, "avg": 0, "obp": 0, "slg": 0, "ops": 0,
                "strikeouts": 0, "walks": 0, "home_runs": 0, "edge": "no_data"}
    
    avg = total_hits / total_pa
    obp = (total_hits + total_bb) / total_pa
    slg = total_bases / total_pa
    ops = obp + slg
    
    if total_pa < 10:
        edge = "low_sample"
    elif ops < 0.500:
        edge = "dominates"
    elif ops < 0.650:
        edge = "advantage"
    elif ops < 0.800:
        edge = "neutral"
    elif ops < 1.000:
        edge = "struggles"
    else:
        edge = "dominated"
    
    return {
        "total_pa": total_pa, "avg": round(avg, 3), "obp": round(obp, 3),
        "slg": round(slg, 3), "ops": round(ops, 3),
        "strikeouts": total_so, "walks": total_bb, "home_runs": total_hr,
        "edge": edge,
    }

def calculate_game_score(team_offense, team_pitching, bullpen_fatigue,
                         recent_trends, bvp_analysis, weather,
                         park_factor, umpire_tendency) -> Dict:
    """Calculate composite game score combining all factors."""
    ops = team_offense.get("ops", 0.720)
    runs_per_game = team_offense.get("runs_per_game", 4.5)
    
    # Offense score (0-100)
    offense_score = min(100, max(0,
        ((ops - 0.600) / 0.200) * 80 + (runs_per_game / 7.0) * 20
    ))
    
    # Pitching vulnerability (0-100, higher = more vulnerable)
    era = team_pitching.get("era", 4.00)
    whip = team_pitching.get("whip", 1.30)
    pitching_vulnerability = min(100, max(0,
        ((era - 3.00) / 3.00) * 70 + ((whip - 1.00) / 0.50) * 30
    ))
    
    # Bullpen fatigue (0-100)
    bullpen_score = bullpen_fatigue.get("fatigue_score", 0)
    
    # Recent trends (0-100)
    trend_scores = {"hot": 90, "warm": 70, "neutral": 50, "cold": 30,
                    "ice_cold": 10, "unknown": 50}
    trend_score = trend_scores.get(recent_trends.get("trend", "neutral"), 50)
    
    # BvP edge (0-100)
    edge_scores = {"dominates": 90, "advantage": 70, "neutral": 50,
                   "struggles": 30, "dominated": 10, "low_sample": 50,
                   "no_data": 50, "unknown": 50}
    bvp_score = edge_scores.get(bvp_analysis.get("edge", "neutral"), 50)
    
    # Weather impact (-10 to +10)
    weather_impact = 0
    if weather:
        temp = weather.get("temperature_f", 72)
        wind = weather.get("wind_speed_mph", 5)
        wind_dir = weather.get("wind_impact", "neutral")
        if temp > 85:
            weather_impact += 5
        elif temp > 80:
            weather_impact += 3
        elif temp < 55:
            weather_impact -= 3
        elif temp < 50:
            weather_impact -= 5
        if wind_dir == "blowing_out":
            weather_impact += wind / 3
        elif wind_dir == "blowing_in":
            weather_impact -= wind / 3
        weather_impact = max(-10, min(10, weather_impact))
    
    # Park factor impact (-10 to +10)
    park_impact = (park_factor - 1.00) * 100
    
    # Umpire impact (-5 to +5)
    umpire_impact = 0
    if umpire_tendency == "tight":
        umpire_impact = -3
    elif umpire_tendency == "loose":
        umpire_impact = 3
    
    # Composite weighted score
    weights = {
        "offense": 0.25, "pitching": 0.25, "bullpen": 0.15,
        "trends": 0.15, "bvp": 0.10, "weather": 0.05,
        "park": 0.03, "umpire": 0.02,
    }
    
    total_score = (
        offense_score * weights["offense"] +
        pitching_vulnerability * weights["pitching"] +
        bullpen_score * weights["bullpen"] +
        trend_score * weights["trends"] +
        bvp_score * weights["bvp"] +
        (weather_impact + 10) / 20 * 100 * weights["weather"] +
        (park_impact + 10) / 20 * 100 * weights["park"] +
        (umpire_impact + 5) / 10 * 100 * weights["umpire"]
    )
    total_score = max(0, min(100, total_score))
    
    # Recommendation
    if total_score >= 75:
        recommendation = "🔥 FIRE — Strong edge"
    elif total_score >= 60:
        recommendation = "🟢 LEAN — Moderate edge"
    elif total_score >= 45:
        recommendation = "⚪ NEUTRAL — No clear edge"
    elif total_score >= 30:
        recommendation = "🔴 AVOID — Negative edge"
    else:
        recommendation = "🧊 ICE — Strong negative edge"
    
    return {
        "offense_score": round(offense_score, 1),
        "pitching_vulnerability": round(pitching_vulnerability, 1),
        "bullpen_fatigue_score": round(bullpen_score, 1),
        "recent_trend_score": round(trend_score, 1),
        "bvp_edge_score": round(bvp_score, 1),
        "weather_impact": round(weather_impact, 1),
        "park_factor_impact": round(park_impact, 1),
        "umpire_impact": round(umpire_impact, 1),
        "total_score": round(total_score, 1),
        "recommendation": recommendation,
    }
