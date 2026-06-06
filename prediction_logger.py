"""
MLB Edge v2.1 — Pitcher Analytics Module
Fetches and analyzes probable starters for moneyline + hitter prop decisions.
"""
import requests
import time
from typing import Dict, Optional, List
from config import MLB_API, REQUEST_TIMEOUT, API_DELAY

class PitcherAnalyzer:
    """Analyze probable starting pitchers for matchup edges."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MLBEdge/2.1"})
        self._last_call = 0
        self.pitcher_cache = {}
        self.batter_cache = {}
    
    def _wait(self):
        elapsed = time.time() - self._last_call
        if elapsed < API_DELAY:
            time.sleep(API_DELAY - elapsed)
        self._last_call = time.time()
    
    def get_pitcher_stats(self, pitcher_id: int, season: str = "2026") -> Optional[Dict]:
        """Get 2026 season stats for a specific pitcher."""
        if pitcher_id in self.pitcher_cache:
            return self.pitcher_cache[pitcher_id]
        
        self._wait()
        try:
            r = requests.get(
                f"{MLB_API}/people/{pitcher_id}",
                params={"season": season, "hydrate": "stats(group=[pitching],type=[season])"},
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
            people = data.get("people", [])
            if not people:
                return None
            
            p = people[0]
            stats_list = p.get("stats", [])
            if not stats_list:
                return None
            
            stat_data = stats_list[0]
            splits = stat_data.get("splits", [])
            if not splits:
                return None
            
            st = splits[0].get("stat", {})
            
            # Helper to safely convert to float
            def sf(val, default=0.0):
                try:
                    return float(val) if val else default
                except (ValueError, TypeError):
                    return default
            
            result = {
                "id": pitcher_id,
                "name": p.get("fullName", "Unknown"),
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
                "ground_outs": st.get("groundOuts", 0),
                "air_outs": st.get("airOuts", 0),
                "go_ao_ratio": sf(st.get("groundOutsToAirouts")),
                "obp_against": sf(st.get("obp")),
                "slg_against": sf(st.get("slg")),
            }
            
            self.pitcher_cache[pitcher_id] = result
            return result
            
        except Exception as e:
            print(f"  Pitcher stats error (ID: {pitcher_id}): {e}")
            return None
    
    def get_batter_stats(self, batter_id: int, season: str = "2026") -> Optional[Dict]:
        """Get 2026 season stats for a specific batter."""
        if batter_id in self.batter_cache:
            return self.batter_cache[batter_id]
            
        self._wait()
        try:
            r = requests.get(
                f"{MLB_API}/people/{batter_id}",
                params={"season": season, "hydrate": "stats(group=[hitting],type=[season])"},
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
            people = data.get("people", [])
            if not people:
                return None
            
            p = people[0]
            stats_list = p.get("stats", [])
            if not stats_list:
                return None
            
            stat_data = stats_list[0]
            splits = stat_data.get("splits", [])
            if not splits:
                return None
            
            st = splits[0].get("stat", {})
            
            def sf(val, default=0.0):
                try:
                    return float(val) if val else default
                except (ValueError, TypeError):
                    return default
            
            result = {
                "id": batter_id,
                "name": p.get("fullName", "Unknown"),
                "avg": sf(st.get("avg")),
                "obp": sf(st.get("obp")),
                "slg": sf(st.get("slg")),
                "ops": sf(st.get("ops")),
                "home_runs": st.get("homeRuns", 0),
                "rbi": st.get("rbi", 0),
                "runs": st.get("runs", 0),
                "hits": st.get("hits", 0),
                "strikeouts": st.get("strikeOuts", 0),
                "walks": st.get("baseOnBalls", 0),
                "stolen_bases": st.get("stolenBases", 0),
                "doubles": st.get("doubles", 0),
                "triples": st.get("triples", 0),
                "games": st.get("gamesPlayed", 0),
                "at_bats": st.get("atBats", 0),
            }
            
            self.batter_cache[batter_id] = result
            return result
            
        except Exception as e:
            print(f"  Batter stats error (ID: {batter_id}): {e}")
            return None
    
    def calculate_pitcher_quality(self, stats: Dict) -> float:
        """
        Calculate pitcher quality score (0-100, higher = better pitcher).
        Combines ERA, WHIP, K/9, and opponent OPS.
        """
        if not stats:
            return 50.0
        
        era = stats.get("era", 4.00)
        whip = stats.get("whip", 1.30)
        k9 = stats.get("k9", 8.0)
        ops_against = stats.get("ops_against", 0.750)
        
        # ERA component (lower is better, 2.50=100, 6.00=0)
        era_score = max(0, min(100, (6.00 - era) / 3.50 * 100))
        
        # WHIP component (lower is better, 0.90=100, 1.50=0)
        whip_score = max(0, min(100, (1.50 - whip) / 0.60 * 100))
        
        # K/9 component (higher is better, 5=0, 12=100)
        k9_score = max(0, min(100, (k9 - 5.0) / 7.0 * 100))
        
        # OPS against component (lower is better, 0.600=100, 0.900=0)
        ops_score = max(0, min(100, (0.900 - ops_against) / 0.300 * 100))
        
        # Weighted average
        quality = (era_score * 0.35 + whip_score * 0.25 + k9_score * 0.20 + ops_score * 0.20)
        
        return round(quality, 1)
    
    def get_pitcher_edge(self, away_pitcher: Dict, home_pitcher: Dict) -> Dict:
        """
        Compare two starting pitchers.
        Returns edge analysis for moneyline and hitter props.
        """
        away_quality = self.calculate_pitcher_quality(away_pitcher) if away_pitcher else 50
        home_quality = self.calculate_pitcher_quality(home_pitcher) if home_pitcher else 50
        
        quality_diff = home_quality - away_quality
        
        # Determine pitcher advantage
        if abs(quality_diff) < 5:
            advantage = "even"
            adv_text = "Pitching matchup is even"
        elif quality_diff > 0:
            advantage = "home"
            adv_text = f"Home pitcher edge (+{quality_diff:.1f})"
        else:
            advantage = "away"
            adv_text = f"Away pitcher edge (+{abs(quality_diff):.1f})"
        
        # Hitter prop implications
        hitter_props = {
            "home_batters_favorable": home_pitcher.get("era", 4.00) > 4.50 if home_pitcher else False,
            "away_batters_favorable": away_pitcher.get("era", 4.00) > 4.50 if away_pitcher else False,
            "high_k_pitcher_home": home_pitcher.get("k9", 0) > 9.0 if home_pitcher else False,
            "high_k_pitcher_away": away_pitcher.get("k9", 0) > 9.0 if away_pitcher else False,
            "hr_allowed_home": home_pitcher.get("hr9", 0) > 1.2 if home_pitcher else False,
            "hr_allowed_away": away_pitcher.get("hr9", 0) > 1.2 if away_pitcher else False,
        }
        
        return {
            "away_pitcher_quality": away_quality,
            "home_pitcher_quality": home_quality,
            "quality_diff": round(quality_diff, 1),
            "advantage": advantage,
            "adv_text": adv_text,
            "hitter_props": hitter_props,
        }
    
    def get_batter_vs_pitcher(self, batter_id: int, pitcher_id: int) -> Optional[Dict]:
        """
        Get career BvP stats between a batter and pitcher.
        Uses MLB API hydrate endpoint.
        """
        self._wait()
        try:
            r = requests.get(
                f"{MLB_API}/people/{batter_id}",
                params={
                    "season": "2026",
                    "hydrate": f"stats(group=[hitting],type=[opponent],opponent={pitcher_id})"
                },
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
            
            people = data.get("people", [])
            if not people:
                return None
            
            stats_list = people[0].get("stats", [])
            if not stats_list:
                return None
            
            # Find opponent stats
            for stat_group in stats_list:
                if stat_group.get("group", {}).get("displayName") == "hitting":
                    if stat_group.get("type", {}).get("displayName") == "opponent":
                        splits = stat_group.get("splits", [])
                        if splits:
                            st = splits[0].get("stat", {})
                            return {
                                "at_bats": st.get("atBats", 0),
                                "hits": st.get("hits", 0),
                                "home_runs": st.get("homeRuns", 0),
                                "avg": st.get("avg", ".000"),
                                "obp": st.get("obp", ".000"),
                                "slg": st.get("slg", ".000"),
                                "strikeouts": st.get("strikeOuts", 0),
                                "walks": st.get("baseOnBalls", 0),
                            }
            
            return None
            
        except Exception as e:
            print(f"  BvP error (batter: {batter_id}, pitcher: {pitcher_id}): {e}")
            return None
