"""
MLB Edge v2.3 — Situational Engine
Travel fatigue, fade the public, game script, triple-stack, timezone,
regression radar, market divergence, early-pull scenario. ZERO API calls.
"""
import math
from typing import Dict, List, Optional
from config import STADIUM_COORDS

# ─── 1. TRAVEL FATIGUE ──────────────────────────────────────────
def calculate_travel_fatigue(team_id: int, recent_games: list, is_home: bool,
                             team_name: str = "") -> Dict:
    """
    Calculate travel fatigue from recent game venues.
    Uses stadium coordinates to compute travel distance.
    Shows which cities the team visited and when.
    ZERO API calls — uses already-fetched recent games.
    """
    if not recent_games or len(recent_games) < 2:
        return {"fatigue_level": "unknown", "miles_traveled": 0, "games_in_7": 0,
                "detail": "", "run_adj": 0, "team": team_name, "travel_log": ""}

    # Extract venue sequence from recent games with dates
    venues = []
    venue_log = []
    for g in recent_games[:7]:  # last 7 games
        home_id = g.get("teams", {}).get("home", {}).get("team", {}).get("id")
        home_name = g.get("teams", {}).get("home", {}).get("team", {}).get("name", "?")
        game_date = g.get("officialDate", "?")
        if home_id:
            venues.append(home_id)
            venue_log.append(f"{game_date[-5:]}: {'HOME' if home_id == team_id else home_name[:12]}")

    # Calculate total miles traveled
    total_miles = 0
    for i in range(len(venues) - 1):
        c1 = STADIUM_COORDS.get(venues[i])
        c2 = STADIUM_COORDS.get(venues[i + 1])
        if c1 and c2:
            total_miles += _haversine(c1[0], c1[1], c2[0], c2[1])

    games_in_7 = len(recent_games)
    cities = len(set(venues))

    # Fatigue scoring
    score = 0
    detail_parts = []

    if total_miles > 3000:
        score += 3
        detail_parts.append(f"{total_miles:.0f}mi traveled")
    elif total_miles > 1500:
        score += 2
        detail_parts.append(f"{total_miles:.0f}mi")
    elif total_miles > 500:
        score += 1

    if cities >= 4:
        score += 2
        detail_parts.append(f"{cities} cities")
    elif cities >= 3:
        score += 1
        detail_parts.append(f"{cities} cities")

    if games_in_7 >= 7:
        score += 1
        detail_parts.append("no off day")

    # Home team gets rest bonus
    if is_home:
        score = max(0, score - 1)

    if score >= 4:
        level = "exhausted"
        run_adj = -0.3  # team underperforms
    elif score >= 3:
        level = "tired"
        run_adj = -0.2
    elif score >= 2:
        level = "moderate"
        run_adj = -0.1
    else:
        level = "fresh"
        run_adj = 0

    travel_log = " → ".join(venue_log[:5]) if venue_log else ""

    return {
        "fatigue_level": level,
        "miles_traveled": round(total_miles),
        "games_in_7": games_in_7,
        "cities_visited": cities,
        "score": score,
        "detail": ", ".join(detail_parts) if detail_parts else "Normal schedule",
        "run_adj": run_adj,
        "team": team_name,
        "travel_log": travel_log,
    }


def _haversine(lat1, lon1, lat2, lon2):
    """Distance between two points in miles."""
    R = 3959  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ─── 2. TIMEZONE / JET LAG ──────────────────────────────────────
# Approximate timezone offset by longitude (MLB stadiums are all US)
def calculate_timezone_shift(team_id: int, recent_games: list,
                             team_name: str = "", home_id: int = None) -> Dict:
    """Detect cross-country travel for jet lag impact. Shows which team is affected."""
    if not recent_games:
        return {"shift_hours": 0, "alert": "", "run_adj": 0, "team": team_name}

    # Where did they play last?
    last_venue = recent_games[0].get("teams", {}).get("home", {}).get("team", {}).get("id")
    last_venue_name = recent_games[0].get("teams", {}).get("home", {}).get("team", {}).get("name", "?")
    if not last_venue:
        return {"shift_hours": 0, "alert": "", "run_adj": 0, "team": team_name}

    today_venue = home_id or team_id
    prev_coords = STADIUM_COORDS.get(last_venue)
    curr_coords = STADIUM_COORDS.get(today_venue)
    if not prev_coords or not curr_coords:
        return {"shift_hours": 0, "alert": "", "run_adj": 0, "team": team_name}

    prev_tz = round(prev_coords[1] / 15)
    curr_tz = round(curr_coords[1] / 15)
    shift = abs(prev_tz - curr_tz)
    direction = "East→West" if curr_coords[1] < prev_coords[1] else "West→East"

    if shift >= 3:
        return {"shift_hours": shift, "team": team_name,
                "alert": f"⚠️ {team_name}: {shift}hr timezone shift ({direction}) from {last_venue_name[:15]} — jet lag risk",
                "run_adj": -0.15}
    elif shift >= 2:
        return {"shift_hours": shift, "team": team_name,
                "alert": f"🔄 {team_name}: {shift}hr timezone change ({direction})",
                "run_adj": -0.08}
    return {"shift_hours": shift, "alert": "", "run_adj": 0, "team": team_name}


# ─── 3. TRIPLE STACK ALERT ──────────────────────────────────────
def check_triple_stack(weather: dict, umpire: dict, park_factor: float) -> Optional[Dict]:
    """
    Detect when park + weather + umpire ALL point the same direction.
    These are the highest-conviction totals plays.
    """
    signals_over = 0
    signals_under = 0
    reasons_over = []
    reasons_under = []

    # Weather
    w_adj = weather.get("weather_run_adj", 0) if weather else 0
    if w_adj > 0.3:
        signals_over += 1
        reasons_over.append(f"Weather +{w_adj:.1f}R")
    elif w_adj < -0.3:
        signals_under += 1
        reasons_under.append(f"Weather {w_adj:.1f}R")

    # Umpire
    u_imp = umpire.get("run_impact", 0) if umpire else 0
    if u_imp > 0.5:
        signals_over += 1
        reasons_over.append(f"Ump +{u_imp:.1f}R")
    elif u_imp < -0.5:
        signals_under += 1
        reasons_under.append(f"Ump {u_imp:.1f}R")

    # Park
    if park_factor >= 1.05:
        signals_over += 1
        reasons_over.append(f"Park {park_factor:.2f}")
    elif park_factor <= 0.96:
        signals_under += 1
        reasons_under.append(f"Park {park_factor:.2f}")

    if signals_over >= 3:
        return {"direction": "OVER", "strength": "triple_stack",
                "reasons": reasons_over, "emoji": "🔺🔺🔺",
                "detail": "Park + Weather + Ump ALL favor scoring"}
    if signals_under >= 3:
        return {"direction": "UNDER", "strength": "triple_stack",
                "reasons": reasons_under, "emoji": "🔻🔻🔻",
                "detail": "Park + Weather + Ump ALL suppress scoring"}
    if signals_over >= 2:
        return {"direction": "OVER", "strength": "double_stack",
                "reasons": reasons_over, "emoji": "🔺🔺",
                "detail": "2 of 3 environmental factors favor scoring"}
    if signals_under >= 2:
        return {"direction": "UNDER", "strength": "double_stack",
                "reasons": reasons_under, "emoji": "🔻🔻",
                "detail": "2 of 3 environmental factors suppress scoring"}
    return None


# ─── 4. FADE THE PUBLIC ─────────────────────────────────────────
# Big-market teams the public loves to bet
_PUBLIC_DARLINGS = {119, 147, 111, 112, 144, 117, 143}  # LAD, NYY, BOS, CHC, ATL, HOU, PHI

def check_fade_public(home_id: int, away_id: int, home_odds: int,
                      away_odds: int, model_favored: str, game_time: str = "") -> Optional[Dict]:
    """
    Heuristic: detect when public money is likely inflating one side.
    Big-name team + home favorite + primetime = public side.
    When our model disagrees → fade signal.
    """
    if not home_odds or not away_odds:
        return None

    # Who is the book favorite?
    book_fav = "home" if home_odds < away_odds else "away"
    fav_id = home_id if book_fav == "home" else away_id
    dog_id = away_id if book_fav == "home" else home_id

    # Is the favorite a public darling?
    is_public_fav = fav_id in _PUBLIC_DARLINGS

    # Is it a heavy favorite?
    fav_odds = min(home_odds, away_odds)
    is_heavy = fav_odds <= -160

    # Primetime detection (7pm+ ET games, weekend games)
    is_prime = False
    if game_time:
        try:
            t = game_time.upper()
            if any(x in t for x in ["7:", "8:", "9:", "10:"]) and "PM" in t:
                is_prime = True
        except Exception:
            pass

    # Public score (higher = more likely public is on favorite)
    pub_score = 0
    if is_public_fav:
        pub_score += 2
    if is_heavy:
        pub_score += 1
    if is_prime:
        pub_score += 1
    if book_fav == "home":
        pub_score += 1  # public loves home favorites

    # Does our model disagree?
    if model_favored == book_fav or model_favored in ("none", "even"):
        return None  # model agrees with book — no fade

    if pub_score >= 3:
        dog_side = "away" if book_fav == "home" else "home"
        return {
            "side": dog_side,
            "pub_score": pub_score,
            "reasons": [
                "Public darling" if is_public_fav else "",
                "Heavy favorite" if is_heavy else "",
                "Primetime" if is_prime else "",
                "Home favorite" if book_fav == "home" else "",
            ],
            "detail": f"🔄 FADE: Public on {book_fav} favorite — model sees value on {dog_side}",
        }
    return None


# ─── 5. GAME SCRIPT CLASSIFICATION ──────────────────────────────
def classify_game_script(away_pitcher_quality: float, home_pitcher_quality: float,
                         away_offense: float, home_offense: float,
                         away_bullpen_fatigue: float, home_bullpen_fatigue: float) -> Dict:
    """
    Predict game script: Pitcher Duel, Slugfest, or Blowout.
    Changes which bet types make sense.
    """
    # Pitcher quality avg (0-100)
    avg_pitch = (away_pitcher_quality + home_pitcher_quality) / 2
    # Offense avg
    avg_off = (away_offense + home_offense) / 2
    # Bullpen fatigue avg
    avg_bull = (away_bullpen_fatigue + home_bullpen_fatigue) / 2
    # Quality gap
    quality_gap = abs(away_pitcher_quality - home_pitcher_quality)

    if avg_pitch >= 65 and avg_off <= 55 and avg_bull <= 35:
        script = "pitcher_duel"
        emoji = "🧊"
        detail = "Two strong arms, limited offense — low scoring expected"
        bet_advice = "F5 Under · NRFI · Pitcher K props"
    elif avg_off >= 60 and (avg_pitch <= 50 or avg_bull >= 45):
        script = "slugfest"
        emoji = "🔥"
        detail = "Offense-heavy, vulnerable pitching or tired pens"
        bet_advice = "Full-game Over · YRFI · Hitter props"
    elif quality_gap >= 25:
        script = "blowout"
        emoji = "💨"
        detail = "Significant mismatch — one side heavily favored"
        bet_advice = "Run line · F5 ML · Team total"
    else:
        script = "competitive"
        emoji = "⚖️"
        detail = "Evenly matched — standard game expected"
        bet_advice = "Moneyline · Standard totals"

    return {
        "script": script,
        "emoji": emoji,
        "detail": detail,
        "bet_advice": bet_advice,
        "avg_pitcher_quality": round(avg_pitch),
        "avg_offense": round(avg_off),
        "quality_gap": round(quality_gap),
    }


# ─── 6. REGRESSION RADAR ────────────────────────────────────────
def build_regression_radar(pitcher_expected: dict, batter_expected: dict) -> Dict:
    """
    Find players with biggest actual vs expected stat gaps.
    These are prime regression candidates for props.
    """
    # Pitchers: biggest ERA - xERA gap (positive = lucky, negative = unlucky)
    lucky_pitchers = []
    unlucky_pitchers = []
    for pid, data in pitcher_expected.items():
        if data.get("pa", 0) < 100:
            continue  # skip small samples
        gap = data.get("era_xera_gap", 0)
        if gap > 0.60:
            lucky_pitchers.append({"name": data["name"], "era": data["era"],
                                   "xera": data["xera"], "gap": gap})
        elif gap < -0.60:
            unlucky_pitchers.append({"name": data["name"], "era": data["era"],
                                     "xera": data["xera"], "gap": gap})

    lucky_pitchers.sort(key=lambda x: x["gap"], reverse=True)
    unlucky_pitchers.sort(key=lambda x: x["gap"])

    # Batters: biggest wOBA - xwOBA gap
    lucky_batters = []
    unlucky_batters = []
    for pid, data in batter_expected.items():
        if data.get("pa", 0) < 100:
            continue  # skip small samples
        gap = data.get("luck_gap", 0)
        if gap > 0.030:
            lucky_batters.append({"name": data["name"], "woba": data["woba"],
                                  "xwoba": data["xwoba"], "gap": gap})
        elif gap < -0.030:
            unlucky_batters.append({"name": data["name"], "woba": data["woba"],
                                    "xwoba": data["xwoba"], "gap": gap})

    lucky_batters.sort(key=lambda x: x["gap"], reverse=True)
    unlucky_batters.sort(key=lambda x: x["gap"])

    return {
        "lucky_pitchers": lucky_pitchers[:5],   # fade these — ERA will rise
        "unlucky_pitchers": unlucky_pitchers[:5],  # back these — ERA will drop
        "lucky_batters": lucky_batters[:5],     # fade — hitting above true talent
        "unlucky_batters": unlucky_batters[:5],  # back — due for improvement
    }


# ─── 7. MARKET DIVERGENCE ───────────────────────────────────────
def find_market_divergences(games: list) -> List[Dict]:
    """
    Find games where model probability diverges most from book implied.
    These are where the most value lives.
    """
    divs = []
    for g in games:
        ev = g.get("ev_data", {})
        if not ev.get("has_line"):
            continue
        edge = max(abs(ev.get("home_edge", 0)), abs(ev.get("away_edge", 0)))
        if edge > 2.0:
            best = ev.get("best_side", "pass")
            name = g.get("home_team", {}).get("name", "?") if best == "home" else g.get("away_team", {}).get("name", "?")
            divs.append({
                "matchup": f'{g.get("away_team",{}).get("name","?")} @ {g.get("home_team",{}).get("name","?")}',
                "side": name,
                "edge": round(edge, 1),
                "ev": ev.get("best_ev", 0),
                "model_prob": ev.get(f"{best}_model_prob", 50),
                "book_prob": ev.get(f"{best}_book_prob", 50),
                "grade": g.get("grade", {}).get("grade", "?"),
            })
    divs.sort(key=lambda x: x["edge"], reverse=True)
    return divs[:5]


# ─── 8. EARLY PULL SCENARIO ─────────────────────────────────────
def early_pull_scenario(f5_total: float, park_factor: float,
                        home_bull_fatigue: float, away_bull_fatigue: float) -> Dict:
    """
    What happens to the total if the starter is pulled after 4 IP vs 6 IP?
    Helps bettors think about live betting thresholds.
    """
    # Full-game with starter going 6 IP (normal)
    normal = f5_total / 0.48 + 0.5  # calibrated formula
    normal *= park_factor

    # Early pull (4 IP): more bullpen exposure
    bull_factor = 1.0 + (home_bull_fatigue + away_bull_fatigue) / 200
    early_pull = (f5_total * 0.8) / 0.40 + 0.5  # F5 reduced, worse divisor
    early_pull *= park_factor * bull_factor

    return {
        "normal_total": round(normal, 1),
        "early_pull_total": round(early_pull, 1),
        "swing": round(early_pull - normal, 1),
        "detail": f"6+ IP: {normal:.1f} | Pulled 4 IP: {early_pull:.1f} (+{early_pull - normal:.1f}R)"
    }


# ─── 9. REST DAYS + GAMES PLAYED TRACKER ─────────────────────────
def calculate_rest_and_schedule(team_id: int, recent_games: list,
                                is_home: bool, team_name: str = "") -> Dict:
    """
    Calculate rest days, games in last 15 days, last travel date.
    Uses already-fetched recent games. ZERO API calls.
    """
    from datetime import datetime, timedelta
    
    if not recent_games:
        return {
            "days_since_last_game": None,
            "had_game_yesterday": False,
            "games_last_15_days": 0,
            "last_travel_date": None,
            "rest_status": "unknown",
            "detail": "",
        }
    
    today = datetime.now()
    
    # Find last game date
    last_game_date_str = None
    for g in recent_games:
        d = g.get("officialDate", "") or g.get("gameDate", "")[:10]
        if d:
            last_game_date_str = d
            break
    
    days_since = None
    had_game_yesterday = False
    if last_game_date_str:
        try:
            last_game_dt = datetime.strptime(last_game_date_str, "%Y-%m-%d")
            days_since = (today - last_game_dt).days
            had_game_yesterday = (days_since == 1)
        except Exception:
            pass
    
    # Count games in last 15 days
    cutoff = today - timedelta(days=15)
    games_15 = 0
    for g in recent_games:
        d = g.get("officialDate", "") or g.get("gameDate", "")[:10]
        if d:
            try:
                gd = datetime.strptime(d, "%Y-%m-%d")
                if gd >= cutoff:
                    games_15 += 1
            except Exception:
                continue
    
    # Last travel date: find when team last changed cities
    last_travel_date = None
    venues_seen = []
    for g in recent_games[:10]:
        d = g.get("officialDate", "") or g.get("gameDate", "")[:10]
        home_id = g.get("teams", {}).get("home", {}).get("team", {}).get("id")
        if home_id is not None and home_id != team_id:
            # Away game — traveled to this city
            if home_id not in venues_seen:
                last_travel_date = d
                break
            venues_seen.append(home_id)
        elif home_id == team_id and venues_seen:
            # Was on road, now home — traveled to home
            last_travel_date = d
            break
    
    # Rest status
    if days_since is not None and days_since >= 2:
        rest_status = "rested"
        detail = f"{days_since} days rest — fresh"
    elif days_since == 1:
        rest_status = "normal"
        detail = "Played yesterday — standard rest"
    elif days_since == 0:
        rest_status = "no_rest"
        detail = "Played today (doubleheader?) — no rest"
    else:
        rest_status = "unknown"
        detail = ""
    
    return {
        "days_since_last_game": days_since,
        "had_game_yesterday": had_game_yesterday,
        "games_last_15_days": games_15,
        "last_travel_date": last_travel_date,
        "rest_status": rest_status,
        "detail": detail,
    }
