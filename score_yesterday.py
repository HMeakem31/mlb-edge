"""
MLB Edge v2.1 — Complete Pipeline
F5 Analysis + Convergence Score + Platoon + Home/Road + Streaks
Optimized for weak systems — minimal API calls, smart caching.
"""
import sys
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    TEAM_IDS, TEAM_NAMES, STADIUM_COORDS, PARK_FACTORS,
    RECENT_GAMES, PARALLEL_WORKERS,
    OUTPUT_DIR, DATA_DIR, CACHE_DIR, API_DELAY, MLB_API, REQUEST_TIMEOUT
)
from cache import clear_expired_cache, get_cache_stats
from fetcher import Fetcher
from weather_fetcher import WeatherFetcher
from lines_fetcher import LinesFetcher
from umpire_fetcher import UmpireFetcher
from pitcher_analytics import PitcherAnalyzer
from splits_analytics import SplitsAnalyzer
from splits_streaks import parse_streak, calculate_home_road_edge, format_splits_summary
from f5_analytics import estimate_f5_metrics, calculate_f5_edge, generate_f5_recommendations
from convergence import calculate_convergence_score
from edge_calculator import (
    calculate_ev, calculate_grade, kelly_sizing, calculate_nrfi,
    calculate_fip, calculate_totals_edge, build_sgp_suggestions, generate_narrative
)
from prediction_logger import log_predictions, get_accuracy_dict
from injury_fetcher import fetch_injuries, cross_reference_probables
from matchup_engine import build_matchup_extras, format_extras_for_report
from situational_engine import (
    calculate_travel_fatigue, calculate_timezone_shift, check_triple_stack,
    check_fade_public, classify_game_script, early_pull_scenario,
    build_regression_radar, find_market_divergences, calculate_rest_and_schedule
)
from advanced_analytics import (
    calculate_bullpen_fatigue, calculate_recent_trends, calculate_game_score
)
from reporter import generate_report, save_report
import requests

# User bankroll for Kelly sizing (set in config or here)
USER_BANKROLL = 1000.0

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def get_standings() -> dict:
    """Fetch 2026 standings with ALL split data."""
    all_teams = {}
    for league_id in [103, 104]:
        try:
            r = requests.get(
                f'{MLB_API}/standings?season=2026&leagueId={league_id}',
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
            for rec in data.get('records', []):
                for tr in rec.get('teamRecords', []):
                    tid = tr.get('team', {}).get('id')
                    lr = tr.get('leagueRecord', {})
                    streak = tr.get('streak', {})
                    split_records = {}
                    for sr in tr.get('records', {}).get('splitRecords', []):
                        stype = sr.get('type', '')
                        split_records[stype] = {
                            'wins': sr.get('wins', 0),
                            'losses': sr.get('losses', 0),
                            'pct': sr.get('pct', '.000'),
                        }
                    all_teams[tid] = {
                        'name': tr.get('team', {}).get('name', ''),
                        'wins': lr.get('wins', 0),
                        'losses': lr.get('losses', 0),
                        'pct': lr.get('pct', '.000'),
                        'runs_scored': tr.get('runsScored', 0),
                        'runs_allowed': tr.get('runsAllowed', 0),
                        'games_played': tr.get('gamesPlayed', 0),
                        'streak_code': streak.get('streakCode', 'N/A'),
                        'streak_type': streak.get('streakType', ''),
                        'streak_num': streak.get('streakNumber', 0),
                        'splits': split_records,
                    }
        except Exception as e:
            print(f"  Error fetching league {league_id}: {e}")
    return all_teams

def get_schedule_with_pitchers(date: str) -> list:
    """Get today's schedule with probable pitchers."""
    try:
        r = requests.get(
            f'{MLB_API}/schedule?sportId=1&date={date}&hydrate=probablePitcher,team,venue',
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
        games = []
        for d in data.get('dates', []):
            for g in d.get('games', []):
                away = g.get('teams', {}).get('away', {})
                home = g.get('teams', {}).get('home', {})
                away_p = away.get('probablePitcher', {})
                home_p = home.get('probablePitcher', {})
                games.append({
                    'game_pk': g.get('gamePk'),
                    'away_id': away.get('team', {}).get('id'),
                    'home_id': home.get('team', {}).get('id'),
                    'away_name': away.get('team', {}).get('name', 'Away'),
                    'home_name': home.get('team', {}).get('name', 'Home'),
                    'venue': g.get('venue', {}).get('name', 'Unknown'),
                    'game_time': g.get('gameDate', 'TBD'),
                    'away_pitcher_id': away_p.get('id'),
                    'away_pitcher_name': away_p.get('fullName', 'TBD'),
                    'home_pitcher_id': home_p.get('id'),
                    'home_pitcher_name': home_p.get('fullName', 'TBD'),
                })
        return games
    except Exception as e:
        print(f"  Schedule error: {e}")
        return []

def team_offense_from_standings(team_data: dict) -> dict:
    gp = max(1, team_data.get('games_played', 50))
    rs = team_data.get('runs_scored', 0)
    rpg = rs / gp
    ops_estimate = 0.600 + (rpg - 3.5) * 0.12
    ops_estimate = max(0.550, min(0.800, ops_estimate))
    return {'ops': round(ops_estimate, 3), 'runs_per_game': round(rpg, 2), 'total_runs': rs}

def team_pitching_from_standings(team_data: dict) -> dict:
    gp = max(1, team_data.get('games_played', 50))
    ra = team_data.get('runs_allowed', 0)
    ra_per_game = ra / gp
    era_estimate = ra_per_game * 0.92
    whip_estimate = 0.90 + (era_estimate / 10)
    whip_estimate = max(1.00, min(1.60, whip_estimate))
    return {'era': round(era_estimate, 2), 'whip': round(whip_estimate, 2),
            'runs_allowed_per_game': round(ra_per_game, 2), 'total_runs_allowed': ra}

def generate_hitter_prop_recommendations(game_data: dict) -> list:
    """Generate hitter prop recommendations based on pitcher matchups."""
    recs = []
    away_pitcher = game_data.get('away_pitcher_stats')
    home_pitcher = game_data.get('home_pitcher_stats')
    platoon = game_data.get('platoon_analysis', {})
    
    if away_pitcher:
        era = away_pitcher.get('era', 4.00)
        hr9 = away_pitcher.get('hr9', 1.0)
        k9 = away_pitcher.get('k9', 8.0)
        team = game_data.get('home_team_name', 'Home')
        pitcher_name = game_data.get('away_pitcher_name', 'TBD')
        
        if era > 4.50:
            recs.append({'type': 'hitter_prop', 'side': 'home', 'team': team,
                        'recommendation': f"{team} hitters vs {pitcher_name} (ERA: {era})",
                        'confidence': 'high' if era > 5.0 else 'medium',
                        'reason': 'Pitcher has high ERA'})
        if hr9 > 1.2:
            recs.append({'type': 'hr_prop', 'side': 'home', 'team': team,
                        'recommendation': f"HR props vs {pitcher_name} (HR/9: {hr9})",
                        'confidence': 'medium', 'reason': 'High HR rate'})
        if k9 > 9.0:
            recs.append({'type': 'strikeout_prop', 'side': 'home', 'team': team,
                        'recommendation': f"Strikeout props vs {pitcher_name} (K/9: {k9})",
                        'confidence': 'high', 'reason': 'Elite K rate'})
    
    if home_pitcher:
        era = home_pitcher.get('era', 4.00)
        hr9 = home_pitcher.get('hr9', 1.0)
        k9 = home_pitcher.get('k9', 8.0)
        team = game_data.get('away_team_name', 'Away')
        pitcher_name = game_data.get('home_pitcher_name', 'TBD')
        
        if era > 4.50:
            recs.append({'type': 'hitter_prop', 'side': 'away', 'team': team,
                        'recommendation': f"{team} hitters vs {pitcher_name} (ERA: {era})",
                        'confidence': 'high' if era > 5.0 else 'medium',
                        'reason': 'Pitcher has high ERA'})
        if hr9 > 1.2:
            recs.append({'type': 'hr_prop', 'side': 'away', 'team': team,
                        'recommendation': f"HR props vs {pitcher_name} (HR/9: {hr9})",
                        'confidence': 'medium', 'reason': 'High HR rate'})
        if k9 > 9.0:
            recs.append({'type': 'strikeout_prop', 'side': 'away', 'team': team,
                        'recommendation': f"Strikeout props vs {pitcher_name} (K/9: {k9})",
                        'confidence': 'high', 'reason': 'Elite K rate'})
    
    # Platoon props
    if platoon:
        away_platoon = platoon.get('away_team', {}).get('platoon_edge', 50)
        home_platoon = platoon.get('home_team', {}).get('platoon_edge', 50)
        if away_platoon > 60:
            recs.append({'type': 'platoon_edge', 'side': 'away',
                        'recommendation': f"Away batters have platoon advantage ({away_platoon:.0f})",
                        'confidence': 'high' if away_platoon > 65 else 'medium',
                        'reason': 'Lineup vs pitcher handedness mismatch'})
        if home_platoon > 60:
            recs.append({'type': 'platoon_edge', 'side': 'home',
                        'recommendation': f"Home batters have platoon advantage ({home_platoon:.0f})",
                        'confidence': 'high' if home_platoon > 65 else 'medium',
                        'reason': 'Lineup vs pitcher handedness mismatch'})
    
    return recs

def main():
    start_time = time.time()
    print_header("⚾ MLB Edge v2.4 — F5 + Convergence + Prediction Logger")
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"📅 Date: {today} | Workers: {PARALLEL_WORKERS} | Statcast: Savant CSV")

    fetcher = Fetcher()
    weather_fetcher = WeatherFetcher()
    lines_fetcher = LinesFetcher()
    umpire_fetcher = UmpireFetcher()
    pitchers = PitcherAnalyzer()
    splits = SplitsAnalyzer()

    # Step 1: Schedule
    print(f"\n[1/9] Schedule + pitchers...")
    games = get_schedule_with_pitchers(today)
    if not games:
        print("⚠️ No games today."); return
    print(f"  ✅ {len(games)} games")

    # Step 2: Standings
    print(f"\n[2/9] Standings + splits...")
    standings = get_standings()
    print(f"  ✅ {len(standings)} teams")

    # Step 3: Lineups + Team Stats (batch)
    print(f"\n[3/9] Lineups + team stats...")
    all_ids = list(set([g["away_id"] for g in games] + [g["home_id"] for g in games]))
    lineup_data = {tid: splits.analyze_lineup_handedness(tid) for tid in all_ids}
    offense_data = {tid: splits.get_team_offensive_profile(tid) for tid in all_ids}
    # Batch team hitting+fielding (1 call/team instead of 3)
    from batch_fetcher import fetch_all_team_stats, fetch_weather_parallel, fetch_pitcher_full
    from player_profiles import (
        get_sprint_speed_db, get_pitch_arsenal_db, build_batter_card,
        build_pitcher_card, format_batter_card_html, format_pitcher_card_html,
        batter_vs_style
    )
    team_stats_db = fetch_all_team_stats(all_ids)
    print(f"  ✅ {len(lineup_data)} lineups, {len(team_stats_db)} team stats")

    # Step 4: Weather (parallel)
    print(f"\n[4/9] Weather (parallel)...")
    home_ids = list(set([g["home_id"] for g in games]))
    weather_data = fetch_weather_parallel(weather_fetcher, home_ids)
    print(f"  ✅ {len(weather_data)} stadiums")

    # Step 5: Umpires
    print(f"\n[5/9] Umpires...")
    umpire_list = umpire_fetcher.get_umpire_assignments()
    print(f"  ✅ {len(umpire_list)} assignments")

    # Step 6: Vegas lines (ESPN — free, no key)
    print(f"\n[6/9] Lines (ESPN)...")
    vegas_lines = lines_fetcher.get_mlb_lines()
    if vegas_lines:
        print(f"  ✅ {len(vegas_lines)} games")
    else:
        print("  ⏭️ No lines available")

    # Step 6b: Injuries / IL (1 API call)
    print(f"\n[6b/9] Injury/IL check...")
    injuries = fetch_injuries()
    injury_flags = cross_reference_probables(games, injuries)
    print(f"  ✅ {len(injuries)} injuries on file, {sum(1 for f in injury_flags.values() if f['on_il'] or f['is_questionable'])} SP flags")

    # Step 7: Statcast (Baseball Savant CSV — free, no key)
    print(f"\n[7/9] Statcast (Savant)...")
    from statcast_fetcher import get_pitcher_expected, get_batter_expected, get_pitcher_xera, get_pitcher_statcast
    from prop_engine import build_game_props
    pitcher_expected_db = get_pitcher_expected()
    batter_expected_db = get_batter_expected()
    # v2.4: sprint speed + pitch arsenals + pitcher statcast (2 new Savant calls)
    sprint_db = get_sprint_speed_db()
    arsenal_db = get_pitch_arsenal_db()
    pitcher_statcast_db = get_pitcher_statcast()
    # Step 8: Analyze games
    print(f"\n[8/9] Analyzing with F5 + Convergence + Props...")
    analyzed_games = []
    all_prop_recs = []
    convergence_summary = []

    for i, game in enumerate(games):
        away_id = game["away_id"]
        home_id = game["home_id"]
        away_std = standings.get(away_id, {})
        home_std = standings.get(home_id, {})
        away_splits = away_std.get('splits', {})
        home_splits = home_std.get('splits', {})

        # Recent games + trends
        away_recent = fetcher.get_team_recent_games(away_id, RECENT_GAMES)
        home_recent = fetcher.get_team_recent_games(home_id, RECENT_GAMES)
        away_trends = calculate_recent_trends(away_recent, away_id)
        home_trends = calculate_recent_trends(home_recent, home_id)
        away_bullpen = calculate_bullpen_fatigue(away_recent, away_id)
        home_bullpen = calculate_bullpen_fatigue(home_recent, home_id)

        # Pitchers (combined stats + RISP in 1 call each)
        away_p_full = fetch_pitcher_full(game.get('away_pitcher_id'))
        home_p_full = fetch_pitcher_full(game.get('home_pitcher_id'))
        away_p_stats = away_p_full  # compatible dict shape
        home_p_stats = home_p_full
        away_p_hand = away_p_full.get('pitch_hand', 'Unknown') if away_p_full else 'Unknown'
        home_p_hand = home_p_full.get('pitch_hand', 'Unknown') if home_p_full else 'Unknown'
        pitcher_edge = pitchers.get_pitcher_edge(away_p_stats, home_p_stats)

        # F5
        away_f5 = estimate_f5_metrics(away_p_stats) if away_p_stats else None
        home_f5 = estimate_f5_metrics(home_p_stats) if home_p_stats else None
        f5_edge = calculate_f5_edge(away_f5, home_f5)

        # Platoon
        matchup = splits.get_matchup_analysis(away_id, home_id, away_p_hand, home_p_hand)
        away_platoon = matchup['away_team']['platoon_edge']
        home_platoon = matchup['home_team']['platoon_edge']
        platoon_diff = matchup['platoon_differential']

        # Home/Road
        home_road = calculate_home_road_edge(home_std, away_std)

        # Streaks
        away_streak = parse_streak(away_std.get('streak_code', 'N/A'))
        home_streak = parse_streak(home_std.get('streak_code', 'N/A'))

        # Offense/Pitching
        away_off = team_offense_from_standings(away_std)
        home_off = team_offense_from_standings(home_std)
        away_pitch = team_pitching_from_standings(away_std)
        home_pitch = team_pitching_from_standings(home_std)

        # Weather
        home_weather = weather_data.get(home_id, {})
        home_pf = PARK_FACTORS.get(home_id, 1.00)
        umpire = umpire_fetcher.get_umpire_for_game(game["home_name"], game["away_name"], umpire_list)
        ump_tendency = umpire.get("tendency", "neutral") if umpire else "neutral"

        # Game scores
        away_score = calculate_game_score(away_off, home_pitch, home_bullpen, away_trends,
                                          {"total_pa":0,"avg":0,"ops":0,"edge":"no_data"},
                                          home_weather, home_pf, ump_tendency)
        home_score = calculate_game_score(home_off, away_pitch, away_bullpen, home_trends,
                                          {"total_pa":0,"avg":0,"ops":0,"edge":"no_data"},
                                          home_weather, home_pf, ump_tendency)

        # CONVERGENCE SCORE
        convergence = calculate_convergence_score(
            home_score=home_score['total_score'],
            away_score=away_score['total_score'],
            platoon_edge={'home_platoon': home_platoon, 'away_platoon': away_platoon,
                         'home_streak': home_streak, 'away_streak': away_streak},
            home_road_edge=home_road,
            f5_edge=f5_edge,
            bullpen={'home_fatigue': home_bullpen.get('fatigue_score', 0),
                    'away_fatigue': away_bullpen.get('fatigue_score', 0)},
            weather={'impact': home_weather.get('wind_impact', 'neutral')},
            park_factor=home_pf
        )
        convergence_summary.append(convergence)

        # Hitter props
        game_data = {
            'away_pitcher_stats': away_p_stats, 'home_pitcher_stats': home_p_stats,
            'away_pitcher_name': game.get('away_pitcher_name', 'TBD'),
            'home_pitcher_name': game.get('home_pitcher_name', 'TBD'),
            'away_team_name': game['away_name'], 'home_team_name': game['home_name'],
            'platoon_analysis': matchup,
        }
        prop_recs = generate_hitter_prop_recommendations(game_data)
        f5_recs = generate_f5_recommendations(f5_edge, {'away_team_name': game['away_name'], 'home_team_name': game['home_name']})
        all_prop_recs.extend(prop_recs + f5_recs)

        # Vegas line + raw odds extraction
        game_line = lines_fetcher.get_game_line(game["home_name"], game["away_name"], vegas_lines)
        line_str = lines_fetcher.format_line(game_line) if game_line else "No line"
        home_odds, away_odds = None, None
        if game_line and game_line.get("moneyline"):
            ml = game_line["moneyline"]
            home_odds = ml.get(game["home_name"])
            away_odds = ml.get(game["away_name"])

        # PHASE 1: EV + Grade + Kelly + NRFI (zero extra API calls)
        ev_data = calculate_ev(convergence, home_odds, away_odds, game["home_name"], game["away_name"])
        grade = calculate_grade(convergence, ev_data)
        kelly = kelly_sizing(ev_data, USER_BANKROLL)
        nrfi = calculate_nrfi(away_p_stats, home_p_stats, away_trends, home_trends, home_pf)

        # PHASE 2A: FIP/xERA + Totals + SGP + Props + Narrative
        away_fip = calculate_fip(away_p_stats)
        home_fip = calculate_fip(home_p_stats)
        # Upgrade FIP with Statcast xERA if available
        away_xera = get_pitcher_xera(game.get("away_pitcher_id"), pitcher_expected_db)
        home_xera = get_pitcher_xera(game.get("home_pitcher_id"), pitcher_expected_db)
        if away_xera:
            away_fip = {**away_fip, **away_xera} if away_fip else away_xera
        if home_xera:
            home_fip = {**home_fip, **home_xera} if home_fip else home_xera
        book_total = 0
        if game_line and game_line.get("totals"):
            book_total = game_line["totals"].get("line", 0) or 0
        ump_stats = umpire if umpire else {}
        totals_edge = calculate_totals_edge(
            f5_edge, home_pf, home_weather,
            home_bullpen, away_bullpen, book_total, ump_stats
        )

        # ADVANCED MATCHUP: RISP (from batch pitcher), defense, SB, shadows
        # Use pre-fetched team stats (zero new calls) + batch pitcher RISP
        from matchup_engine import calculate_shadow_impact, format_extras_for_report as _fmt_extras
        away_ts = team_stats_db.get(away_id, {})
        home_ts = team_stats_db.get(home_id, {})
        shadow = calculate_shadow_impact(home_id, game.get("game_time", ""))
        sb_edge = "even"
        if away_ts.get("aggressive") and home_ts.get("cs_pct", 0) < 0.22:
            sb_edge = "away"
        elif home_ts.get("aggressive") and away_ts.get("cs_pct", 0) < 0.22:
            sb_edge = "home"
        matchup_extras = {
            "away_pitcher_risp": away_p_full.get("risp_splits") if away_p_full else None,
            "home_pitcher_risp": home_p_full.get("risp_splits") if home_p_full else None,
            "away_baserunning": away_ts, "home_baserunning": home_ts,
            "away_fielding": away_ts, "home_fielding": home_ts,
            "shadow": shadow,
            "sb_matchup": {"sb_edge": sb_edge,
                           "away_sb_threat": away_ts.get("sb_threat", "low"),
                           "home_sb_threat": home_ts.get("sb_threat", "low")},
        }

        # SITUATIONAL ENGINE (zero API calls — pure math on existing data)
        away_recent = fetcher.get_team_recent_games(away_id, 7)
        home_recent_7 = fetcher.get_team_recent_games(home_id, 7)
        away_travel = calculate_travel_fatigue(away_id, away_recent, False, game["away_name"])
        home_travel = calculate_travel_fatigue(home_id, home_recent_7, True, game["home_name"])
        away_rest = calculate_rest_and_schedule(away_id, away_recent, False, game["away_name"])
        home_rest = calculate_rest_and_schedule(home_id, home_recent_7, True, game["home_name"])
        away_tz = calculate_timezone_shift(away_id, away_recent, game["away_name"], home_id)
        home_tz = calculate_timezone_shift(home_id, home_recent_7, game["home_name"], home_id)
        triple_stack = check_triple_stack(home_weather, ump_stats, home_pf)
        fade_public = check_fade_public(
            home_id, away_id, home_odds, away_odds,
            convergence.get("favored_side", "none"), game.get("game_time", "")
        )
        game_script = classify_game_script(
            pitcher_edge.get("away_pitcher_quality", 50),
            pitcher_edge.get("home_pitcher_quality", 50),
            away_score.get("offense_score", 50),
            home_score.get("offense_score", 50),
            away_bullpen.get("fatigue_score", 0),
            home_bullpen.get("fatigue_score", 0),
        )
        pull_scenario = early_pull_scenario(
            f5_edge.get("f5_total_estimate", 4.5), home_pf,
            home_bullpen.get("fatigue_score", 0),
            away_bullpen.get("fatigue_score", 0),
        )

        # Build game record
        analyzed_games.append({
            "game_pk": game["game_pk"],
            "away_team": {
                "name": game["away_name"], "id": away_id,
                "record": f"{away_std.get('wins',0)}-{away_std.get('losses',0)}",
                "streak": away_std.get('streak_code', 'N/A'),
                "road_record": f"{away_splits.get('away',{}).get('wins',0)}-{away_splits.get('away',{}).get('losses',0)}",
                "road_pct": away_splits.get('away',{}).get('pct','.000'),
                "l10": f"{away_splits.get('lastTen',{}).get('wins',0)}-{away_splits.get('lastTen',{}).get('losses',0)}",
                "rpg": away_off['runs_per_game'],
                "rapg": away_pitch['runs_allowed_per_game'],
                "pitcher": game.get('away_pitcher_name', 'TBD'),
                "pitcher_hand": away_p_hand,
                "pitcher_quality": pitcher_edge.get("away_pitcher_quality", 50),
                "pitcher_era": away_p_stats.get('era', 'N/A') if away_p_stats else 'N/A',
                "pitcher_k9": away_p_stats.get('k9', 'N/A') if away_p_stats else 'N/A',
                "lineup_lefty_pct": lineup_data[away_id]["lefty_pct"],
                "lineup_righty_pct": lineup_data[away_id]["righty_pct"],
                "platoon_edge": away_platoon,
                "f5_era": away_f5.get('f5_era', 'N/A') if away_f5 else 'N/A',
                "f5_quality": away_f5.get('f5_quality', 'N/A') if away_f5 else 'N/A',
            },
            "home_team": {
                "name": game["home_name"], "id": home_id,
                "record": f"{home_std.get('wins',0)}-{home_std.get('losses',0)}",
                "streak": home_std.get('streak_code', 'N/A'),
                "home_record": f"{home_splits.get('home',{}).get('wins',0)}-{home_splits.get('home',{}).get('losses',0)}",
                "home_pct": home_splits.get('home',{}).get('pct','.000'),
                "l10": f"{home_splits.get('lastTen',{}).get('wins',0)}-{home_splits.get('lastTen',{}).get('losses',0)}",
                "rpg": home_off['runs_per_game'],
                "rapg": home_pitch['runs_allowed_per_game'],
                "pitcher": game.get('home_pitcher_name', 'TBD'),
                "pitcher_hand": home_p_hand,
                "pitcher_quality": pitcher_edge.get("home_pitcher_quality", 50),
                "pitcher_era": home_p_stats.get('era', 'N/A') if home_p_stats else 'N/A',
                "pitcher_k9": home_p_stats.get('k9', 'N/A') if home_p_stats else 'N/A',
                "lineup_lefty_pct": lineup_data[home_id]["lefty_pct"],
                "lineup_righty_pct": lineup_data[home_id]["righty_pct"],
                "platoon_edge": home_platoon,
                "f5_era": home_f5.get('f5_era', 'N/A') if home_f5 else 'N/A',
                "f5_quality": home_f5.get('f5_quality', 'N/A') if home_f5 else 'N/A',
            },
            "context": {
                "game_time": game["game_time"], "venue": game["venue"],
                "weather": {
                    "summary": weather_fetcher.format_summary(home_weather) if home_weather else "N/A",
                    "run_adj": home_weather.get("weather_run_adj", 0) if home_weather else 0,
                    "wind_impact": home_weather.get("wind_impact", "neutral") if home_weather else "neutral",
                    "out_component": home_weather.get("out_component", 0) if home_weather else 0,
                    "carry_ft": home_weather.get("carry_adjustment_ft", 0) if home_weather else 0,
                    "pressure": home_weather.get("surface_pressure_hpa", 0) if home_weather else 0,
                    "is_dome": home_weather.get("is_dome", False) if home_weather else False,
                },
                "umpire": {
                    "summary": umpire_fetcher.format_umpire_line(umpire.get("umpire", "TBD")) if umpire else "TBD",
                    "name": umpire.get("umpire", "TBD") if umpire else "TBD",
                    "run_impact": ump_stats.get("run_impact", 0),
                    "over_pct": ump_stats.get("over_pct", 0.50),
                    "k_per_game": ump_stats.get("k_per_game", 16),
                    "tendency": ump_stats.get("tendency", "neutral"),
                    "in_database": ump_stats.get("in_database", False),
                },
                "park_factor": home_pf,
                "splits_summary": format_splits_summary(home_std, away_std),
            },
            "pitcher_edge": {
                "advantage": pitcher_edge.get("advantage", "even"),
                "adv_text": pitcher_edge.get("adv_text", "No data"),
                "quality_diff": pitcher_edge.get("quality_diff", 0),
            },
            "f5_edge": f5_edge,
            "convergence": convergence,
            "ev_data": ev_data,
            "grade": grade,
            "kelly": kelly,
            "nrfi": nrfi,
            "away_fip": away_fip,
            "home_fip": home_fip,
            "totals_edge": totals_edge,
            "situational": {
                "away_travel": away_travel,
                "home_travel": home_travel,
                "away_timezone": away_tz,
                "home_timezone": home_tz,
                "triple_stack": triple_stack,
                "fade_public": fade_public,
                "game_script": game_script,
                "pull_scenario": pull_scenario,
                "away_rest": away_rest,
                "home_rest": home_rest,
            },
            "matchup_extras": matchup_extras,
            "extras_display": format_extras_for_report(matchup_extras, game["away_name"], game["home_name"]),
            "platoon_differential": platoon_diff,
            "lines": {
                "moneyline": line_str.split(" | ")[0] if " | " in line_str else line_str,
                "total": line_str.split(" | ")[1] if len(line_str.split(" | ")) > 1 else "N/A",
                "spread": game_line.get("spread") if game_line else None,
                "moneyline_open": game_line.get("moneyline_open") if game_line else None,
                "moneyline_raw": game_line.get("moneyline") if game_line else None,
                "totals_raw": game_line.get("totals") if game_line else None,
            },
            "injury_flags": {
                "away": injury_flags.get(game.get("away_pitcher_id"), {}),
                "home": injury_flags.get(game.get("home_pitcher_id"), {}),
            },
            "analysis": {
                "away_analysis": {
                    "offense_score": away_score["offense_score"],
                    "pitching_vulnerability": away_score["pitching_vulnerability"],
                    "bullpen_fatigue": away_bullpen.get("fatigue_score", 0),
                    "trend": away_trends.get("trend", "neutral"),
                    "platoon_edge": away_platoon,
                    "f5_era": away_f5.get('f5_era', 'N/A') if away_f5 else 'N/A',
                    "f5_quality": away_f5.get('f5_quality', 'N/A') if away_f5 else 'N/A',
                    "total_score": away_score["total_score"],
                },
                "home_analysis": {
                    "offense_score": home_score["offense_score"],
                    "pitching_vulnerability": home_score["pitching_vulnerability"],
                    "bullpen_fatigue": home_bullpen.get("fatigue_score", 0),
                    "trend": home_trends.get("trend", "neutral"),
                    "platoon_edge": home_platoon,
                    "f5_era": home_f5.get('f5_era', 'N/A') if home_f5 else 'N/A',
                    "f5_quality": home_f5.get('f5_quality', 'N/A') if home_f5 else 'N/A',
                    "total_score": home_score["total_score"],
                },
                "recommendation": convergence['recommendation'],
            },
        })
        
        # Props (K props + hit props — uses batch K rates, zero new calls)
        from prop_engine import calculate_k_prop
        from hitter_profile import build_hitter_props
        away_k_rate = team_stats_db.get(away_id, {}).get("k_rate", 0.235)
        home_k_rate = team_stats_db.get(home_id, {}).get("k_rate", 0.235)
        game_props = {
            "k_props": {
                "home_pitcher": calculate_k_prop(home_p_stats, away_k_rate, game.get("home_pitcher_name", "")),
                "away_pitcher": calculate_k_prop(away_p_stats, home_k_rate, game.get("away_pitcher_name", "")),
            },
            "hit_props": {
                "home_hitters": build_hitter_props(home_id, game["home_name"],
                    away_p_stats, away_p_hand, batter_expected_db, home_recent_7),
                "away_hitters": build_hitter_props(away_id, game["away_name"],
                    home_p_stats, home_p_hand, batter_expected_db, away_recent),
            },
        }
        # v2.4: Pitcher style + batter vs style profiles
        away_pitcher_card = build_pitcher_card(game.get("away_pitcher_id"), away_p_stats, arsenal_db, pitcher_statcast_db)
        home_pitcher_card = build_pitcher_card(game.get("home_pitcher_id"), home_p_stats, arsenal_db, pitcher_statcast_db)
        game_props["pitcher_cards"] = {
            "away": away_pitcher_card,
            "home": home_pitcher_card,
        }
        # Batter vs pitcher style for hit props (enrich each hitter)
        away_style = away_pitcher_card.get("style", {}).get("style", "unknown")
        home_style = home_pitcher_card.get("style", {}).get("style", "unknown")
        for h in game_props["hit_props"]["home_hitters"]:
            if h.get("season_avg") and h.get("season_ops"):
                pid = h.get("player_id")
                sav = batter_expected_db.get(pid, {})
                bs_matchup = batter_vs_style(
                    {"ab": 100, "hits": int(float(str(h.get("season_avg","0")).replace(".","")) or 0) * 100,
                     "so": int(float(h.get("season_hr",0))*4)},
                    sav, away_style
                )
                h["style_matchup"] = bs_matchup
        for h in game_props["hit_props"]["away_hitters"]:
            if h.get("season_avg") and h.get("season_ops"):
                pid = h.get("player_id")
                sav = batter_expected_db.get(pid, {})
                bs_matchup = batter_vs_style(
                    {"ab": 100, "hits": int(float(str(h.get("season_avg","0")).replace(".","")) or 0) * 100,
                     "so": int(float(h.get("season_hr",0))*4)},
                    sav, home_style
                )
                h["style_matchup"] = bs_matchup
        cur_game = analyzed_games[-1]
        cur_game["props"] = game_props
        cur_game["player_profiles"] = {
            "sprint_db": sprint_db,  # passed through for reporter
            "arsenal_db": arsenal_db,
        }

        # SGP + Narrative (needs the full game record)
        cur_game = analyzed_games[-1]
        sgp = build_sgp_suggestions(convergence, f5_edge, nrfi, totals_edge, grade,
                                    game["away_name"], game["home_name"])
        narrative = generate_narrative(cur_game, game["away_name"], game["home_name"])
        cur_game["sgp"] = sgp
        cur_game["narrative"] = narrative

        # Print game summary
        ev_str = f"EV: {'+' if ev_data['best_ev']>0 else ''}{ev_data['best_ev']:.1f}%" if ev_data['has_line'] else "EV: N/A"
        def _fmt_pitcher(fip_data, label):
            if not fip_data: return f"{label} N/A"
            val = fip_data.get('xera') or fip_data.get('fip') or fip_data.get('era', 0)
            lbl = "xERA" if fip_data.get('xera') else "FIP"
            flag = f" {fip_data['flag']}" if fip_data.get('flag') else ""
            return f"{lbl} {val:.2f}{flag}"
        afip = _fmt_pitcher(away_fip, "Away")
        hfip = _fmt_pitcher(home_fip, "Home")
        tot_str = f"Total: {totals_edge['recommendation']} (Model {totals_edge['model_total']} vs Book {totals_edge['book_total']})" if totals_edge.get('book_total') else ""
        print(f"  [{grade['grade']:2s}] {game['away_name']} @ {game['home_name']}")
        print(f"    SP: {game.get('away_pitcher_name','TBD')} ({afip}) vs {game.get('home_pitcher_name','TBD')} ({hfip})")
        print(f"    {convergence['recommendation']} | {ev_str} | Kelly: ${kelly['suggested_bet']:.0f} | NRFI: {nrfi['recommendation']}")
        if tot_str:
            print(f"    {tot_str}")
        if sgp:
            print(f"    SGP: {' + '.join(sgp[0]['legs'])} ({sgp[0]['correlation']})")
        print()

    # Step 8b: Log predictions (before report, after analysis complete)
    print(f"\n[8b/9] Logging predictions...")
    log_predictions(analyzed_games, today)

    # Step 9: Report
    print(f"\n[9/9] Generating report...")
    # Build league-wide situational data
    regression_radar = build_regression_radar(pitcher_expected_db, batter_expected_db)
    market_divs = find_market_divergences(analyzed_games)
    report_extras = {
        "regression_radar": regression_radar,
        "market_divergences": market_divs,
    }
    accuracy = get_accuracy_dict()
    html = generate_report(analyzed_games, report_extras, accuracy)
    filepath = save_report(html)
    
    elapsed = time.time() - start_time
    api_stats = fetcher.stats()
    print(f"\n{'='*60}")
    print(f"📊 RUN COMPLETE in {elapsed:.1f}s | API calls: {api_stats['api_calls']} | Cache: {api_stats['cache_hits']} hits")
    print(f"Report: {filepath}")
    
    if all_prop_recs:
        print(f"\n🎯 {len(all_prop_recs)} PROP RECOMMENDATIONS:")
        for rec in sorted(all_prop_recs, key=lambda x: {'high':3,'medium':2,'low':1}.get(x.get('confidence','low'),0), reverse=True):
            print(f"  [{rec['confidence'].upper():5s}] {rec['recommendation']}")
    
    print(f"\n🎯 CONVERGENCE + EDGE SUMMARY:")
    for i, conv in enumerate(convergence_summary):
        g = analyzed_games[i]
        gr = g.get('grade', {})
        ev = g.get('ev_data', {})
        nf = g.get('nrfi', {})
        kel = g.get('kelly', {})
        ev_str = f"EV: {'+' if ev.get('best_ev',0)>0 else ''}{ev.get('best_ev',0):.1f}%" if ev.get('has_line') else "EV: N/A"
        print(f"  [{gr.get('grade','?'):2s}] {g['away_team']['name']} @ {g['home_team']['name']}: {conv['recommendation']}")
        print(f"       {ev_str} | Kelly: ${kel.get('suggested_bet',0):.0f} | NRFI: {nf.get('recommendation','?')} ({nf.get('nrfi_score',0):.0f})")

if __name__ == "__main__":
    main()
