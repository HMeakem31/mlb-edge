"""
MLB Edge v2.1 — Splits Analytics Module
Calculates platoon edges from lineup composition vs pitcher handedness.
Uses league-average splits weighted by actual roster data.
"""
import requests
import time
from typing import Dict, Optional, List
from config import MLB_API, REQUEST_TIMEOUT, API_DELAY, TEAM_IDS, TEAM_NAMES

# League-average platoon splits (2024-2026 MLB averages)
LEAGUE_PLATOON_SPLITS = {
    "vs_same_handedness": {
        "avg_diff": -0.015,    # -15 points vs same-handed pitcher
        "ops_diff": -0.040,    # -40 points OPS
        "woba_diff": -0.018,
    },
    "vs_opposite_handedness": {
        "avg_diff": +0.015,    # +15 points vs opposite-handed pitcher
        "ops_diff": +0.040,    # +40 points OPS
        "woba_diff": +0.018,
    }
}

class SplitsAnalyzer:
    """Analyze platoon splits and batter/pitcher matchups."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MLBEdge/2.1"})
        self._last_call = 0
        self._player_cache = {}
        self._roster_cache = {}
        self._team_stats_cache = {}
    
    def _wait(self):
        elapsed = time.time() - self._last_call
        if elapsed < API_DELAY:
            time.sleep(API_DELAY - elapsed)
        self._last_call = time.time()
    
    def get_team_roster(self, team_id: int) -> List[Dict]:
        """Get team roster with player IDs and positions."""
        if team_id in self._roster_cache:
            return self._roster_cache[team_id]
        
        self._wait()
        try:
            r = requests.get(
                f"{MLB_API}/teams/{team_id}/roster",
                params={"season": "2026", "hydrate": "person"},
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
            roster = []
            for player in data.get("roster", []):
                person = player.get("person", {})
                roster.append({
                    "id": person.get("id"),
                    "name": person.get("fullName", ""),
                    "jersey": player.get("jerseyNumber", ""),
                    "position": player.get("position", {}).get("abbreviation", ""),
                    "bat_side": person.get("batSide", {}).get("code", "Unknown"),
                    "pitch_hand": person.get("pitchHand", {}).get("code", "Unknown"),
                })
            self._roster_cache[team_id] = roster
            return roster
        except Exception as e:
            print(f"  Roster error for team {team_id}: {e}")
            return []
    
    def get_player_handedness(self, player_id: int) -> Dict:
        """Get bat side and pitch hand for a player."""
        if player_id in self._player_cache:
            return self._player_cache[player_id]
        
        self._wait()
        try:
            r = requests.get(
                f"{MLB_API}/people/{player_id}",
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
            people = data.get("people", [])
            if people:
                p = people[0]
                result = {
                    "bat_side": p.get("batSide", {}).get("code", "Unknown"),
                    "pitch_hand": p.get("pitchHand", {}).get("code", "Unknown"),
                    "name": p.get("fullName", ""),
                    "primary_position": p.get("primaryPosition", {}).get("abbreviation", ""),
                }
                self._player_cache[player_id] = result
                return result
        except Exception as e:
            print(f"  Handedness error for player {player_id}: {e}")
        
        return {"bat_side": "Unknown", "pitch_hand": "Unknown", 
                "name": "", "primary_position": ""}
    
    def get_team_stats(self, team_id: int, group: str = "hitting") -> Optional[Dict]:
        """Get team season stats (hitting or pitching)."""
        cache_key = f"{team_id}_{group}"
        if cache_key in self._team_stats_cache:
            return self._team_stats_cache[cache_key]
        
        self._wait()
        try:
            r = requests.get(
                f"{MLB_API}/teams/{team_id}/stats",
                params={
                    "season": "2026",
                    "stats": "season",
                    "group": group,
                    "sportId": "1"
                },
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
            stats_list = data.get("stats", [])
            if stats_list:
                splits = stats_list[0].get("splits", [])
                if splits:
                    result = splits[0].get("stat", {})
                    self._team_stats_cache[cache_key] = result
                    return result
        except Exception as e:
            print(f"  Team stats error for {team_id}: {e}")
        
        return None
    
    def analyze_lineup_handedness(self, team_id: int) -> Dict:
        """
        Analyze team's lineup handedness composition.
        Returns percentage of lefty/righty/switch hitters among position players.
        """
        roster = self.get_team_roster(team_id)
        
        # Filter to position players (not pitchers)
        position_players = [
            p for p in roster 
            if p.get("position") not in ("P", "SP", "RP", "LR")
            and p.get("position") in ("C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "OF", "IF", "UTIL")
        ]
        
        lefty_count = 0
        righty_count = 0
        switch_count = 0
        unknown_count = 0
        
        for player in position_players:
            bat_side = player.get("bat_side", "Unknown")
            
            if bat_side == "L":
                lefty_count += 1
            elif bat_side == "R":
                righty_count += 1
            elif bat_side == "S":
                switch_count += 1
            else:
                unknown_count += 1
        
        total = max(1, lefty_count + righty_count + switch_count)
        
        return {
            "lefty_pct": round(lefty_count / total * 100, 1),
            "righty_pct": round(righty_count / total * 100, 1),
            "switch_pct": round(switch_count / total * 100, 1),
            "lefty_count": lefty_count,
            "righty_count": righty_count,
            "switch_count": switch_count,
            "total_position_players": total,
            "team_id": team_id,
            "team_name": TEAM_NAMES.get(team_id, "Unknown"),
        }
    
    def calculate_platoon_edge(self, lineup_analysis: Dict, opposing_pitcher_hand: str) -> float:
        """
        Calculate platoon advantage score (0-100).
        Higher score = lineup has advantage vs opposing pitcher.
        
        Logic:
        - Lefty batters struggle vs LHP (platoon disadvantage)
        - Righty batters struggle vs RHP (platoon disadvantage)
        - Switch hitters have slight advantage (can choose favorable side)
        - League average platoon split: ~15 points batting average
        """
        if opposing_pitcher_hand == "L":
            # Lefty pitcher: lefty batters disadvantaged, righty batters advantaged
            disadvantaged_pct = lineup_analysis["lefty_pct"]
            advantaged_pct = lineup_analysis["righty_pct"]
            switch_pct = lineup_analysis["switch_pct"]
        elif opposing_pitcher_hand == "R":
            # Righty pitcher: righty batters disadvantaged, lefty batters advantaged
            disadvantaged_pct = lineup_analysis["righty_pct"]
            advantaged_pct = lineup_analysis["lefty_pct"]
            switch_pct = lineup_analysis["switch_pct"]
        else:
            return 50.0  # Unknown handedness
        
        # Calculate raw platoon score
        # Base 50, +/- based on lineup composition
        # League average platoon split effect: ~15 points in batting average
        # This translates to roughly 40 points of OPS
        
        # Switch hitters get neutral treatment (slight advantage)
        net_advantage = (advantaged_pct - disadvantaged_pct) / 100.0
        
        # Scale to 0-100: 50 is neutral, +/- 30 is max effect
        platoon_score = 50 + (net_advantage * 30)
        
        return max(0, min(100, round(platoon_score, 1)))
    
    def get_team_offensive_profile(self, team_id: int) -> Dict:
        """
        Get team's offensive profile from season stats.
        Returns OPS, runs per game, strikeouts, walks, etc.
        """
        stats = self.get_team_stats(team_id, "hitting")
        if not stats:
            return {}
        
        def sf(val, default=0.0):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default
        
        gp = sf(stats.get("gamesPlayed"), 60)
        rpg = sf(stats.get("runs"), 0) / max(1, gp)
        
        return {
            "team_id": team_id,
            "team_name": TEAM_NAMES.get(team_id, "Unknown"),
            "games": int(sf(stats.get("gamesPlayed"), 0)),
            "runs_per_game": round(rpg, 2),
            "avg": sf(stats.get("avg"), 0),
            "obp": sf(stats.get("obp"), 0),
            "slg": sf(stats.get("slg"), 0),
            "ops": sf(stats.get("ops"), 0),
            "home_runs": int(sf(stats.get("homeRuns"), 0)),
            "strikeouts": int(sf(stats.get("strikeOuts"), 0)),
            "walks": int(sf(stats.get("baseOnBalls"), 0)),
            "stolen_bases": int(sf(stats.get("stolenBases"), 0)),
            "babip": sf(stats.get("babip"), 0),
            "iso": round(sf(stats.get("slg"), 0) - sf(stats.get("avg"), 0), 3),
        }
    
    def get_pitcher_performance_profile(self, pitcher_id: int) -> Dict:
        """
        Get pitcher's 2026 season performance profile.
        Returns ERA, WHIP, K/9, HR/9, opponent stats.
        """
        # This is handled by pitcher_analytics.PitcherAnalyzer
        # We'll use it there instead to avoid duplication
        return {}
    
    def get_matchup_analysis(self, away_team_id: int, home_team_id: int,
                            away_pitcher_hand: str, home_pitcher_hand: str) -> Dict:
        """
        Full matchup analysis for a game.
        Returns platoon edges for both teams.
        """
        # Get lineup compositions
        away_lineup = self.analyze_lineup_handedness(away_team_id)
        home_lineup = self.analyze_lineup_handedness(home_team_id)
        
        # Get offensive profiles
        away_offense = self.get_team_offensive_profile(away_team_id)
        home_offense = self.get_team_offensive_profile(home_team_id)
        
        # Calculate platoon edges
        # Away batters face home pitcher
        away_platoon_edge = self.calculate_platoon_edge(away_lineup, home_pitcher_hand)
        # Home batters face away pitcher
        home_platoon_edge = self.calculate_platoon_edge(home_lineup, away_pitcher_hand)
        
        return {
            "away_team": {
                "id": away_team_id,
                "name": TEAM_NAMES.get(away_team_id, "Unknown"),
                "lineup": away_lineup,
                "offense": away_offense,
                "platoon_edge": away_platoon_edge,
                "facing_pitcher_hand": home_pitcher_hand,
            },
            "home_team": {
                "id": home_team_id,
                "name": TEAM_NAMES.get(home_team_id, "Unknown"),
                "lineup": home_lineup,
                "offense": home_offense,
                "platoon_edge": home_platoon_edge,
                "facing_pitcher_hand": away_pitcher_hand,
            },
            "pitcher_handedness": {
                "away": away_pitcher_hand,
                "home": home_pitcher_hand,
            },
            "platoon_differential": round(home_platoon_edge - away_platoon_edge, 1),
        }
