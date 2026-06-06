"""
MLB Edge v2.2 — Umpire Analytics
Rich numeric database from OddsShark + FantasyInfoCentral (public data).
Replaces binary tight/loose with continuous run impact scoring.
"""
import requests
from datetime import datetime
from typing import Optional, Dict, List

from config import REFMETRICS, REQUEST_TIMEOUT

# ─── UMPIRE DATABASE ────────────────────────────────────────────
# Source: OddsShark, FantasyInfoCentral, Covers (all publicly viewable)
# Fields: avg_runs (total per game), k_per_game, bb_per_game,
#         over_pct (% of games going over), home_adv (home runs - away runs),
#         ba (batting average in their games), favors (P=pitcher, H=hitter, N=neither)
#         tendency: derived from data (tight/loose/neutral) for backward compat
# Data: career/multi-season averages for active home plate umpires

UMPIRE_DB = {
    # Name: (avg_runs, k/g, bb/g, over_pct, home_adv, ba, favors)
    "Adam Beck":       (8.6, 17.1, 5.9, 0.47, -0.5, .242, "P"),
    "Adam Hamari":     (8.4, 15.2, 5.6, 0.48, 0.1, .248, "N"),
    "Adrian Johnson":  (9.8, 16.0, 6.5, 0.54, 0.2, .255, "H"),
    "Alan Porter":     (9.0, 15.5, 6.0, 0.50, 0.1, .252, "N"),
    "Alex MacKay":     (8.4, 19.9, 8.3, 0.48, 0.1, .245, "P"),
    "Angel Campos":    (9.8, 14.6, 6.1, 0.53, 0.1, .263, "H"),
    "Ben May":         (10.1, 17.4, 9.5, 0.56, 0.0, .258, "H"),
    "Brian Walsh":     (8.4, 16.6, 5.6, 0.48, -0.1, .247, "P"),
    "Bruce Dreckman":  (7.8, 17.4, 6.3, 0.44, 0.1, .248, "P"),
    "CB Bucknor":      (9.4, 15.1, 5.8, 0.52, 0.4, .258, "N"),
    "Chad Fairchild":  (8.6, 16.8, 5.8, 0.48, -0.2, .247, "P"),
    "Charlie Ramos":   (7.0, 15.9, 7.9, 0.40, 0.0, .240, "P"),
    "Chris Guccione":  (9.0, 15.8, 6.2, 0.50, 0.2, .253, "N"),
    "Chris Segal":     (9.0, 16.3, 6.0, 0.50, 0.0, .250, "N"),
    "Clint Vondrak":   (9.7, 16.0, 6.5, 0.53, 0.2, .255, "H"),
    "Cory Blaser":     (8.5, 16.1, 5.5, 0.47, 0.3, .247, "P"),
    "Dan Bellino":     (8.3, 15.3, 6.5, 0.46, 0.4, .249, "P"),
    "Dan Iassogna":    (8.5, 16.5, 5.7, 0.48, -0.1, .246, "P"),
    "David Rackley":   (8.2, 17.0, 5.5, 0.44, 0.0, .240, "P"),
    "Derek Thomas":    (9.7, 16.0, 6.3, 0.53, 0.2, .256, "H"),
    "Dexter Kelley":   (10.0, 14.8, 7.3, 0.55, 0.0, .260, "H"),
    "Doug Eddings":    (10.4, 15.5, 6.9, 0.57, 0.0, .262, "H"),
    "Edwin Moscoso":   (9.5, 15.0, 6.5, 0.52, 0.1, .258, "H"),
    "Erich Bacchus":   (9.1, 16.7, 6.3, 0.50, 0.1, .239, "P"),
    "Hunter Wendelstedt": (9.5, 15.0, 6.2, 0.52, 0.2, .258, "H"),
    "James Jean":      (10.5, 16.0, 7.0, 0.58, 0.1, .265, "H"),
    "Jen Pawol":       (12.3, 16.8, 7.5, 0.65, 0.0, .275, "H"),
    "Jerry Meals":     (9.3, 15.2, 6.0, 0.51, 0.1, .255, "H"),
    "Jim Wolf":        (9.8, 14.9, 7.5, 0.53, 0.0, .260, "H"),
    "John Libka":      (8.8, 16.0, 6.0, 0.49, 0.0, .250, "N"),
    "John Tumpane":    (8.2, 17.3, 6.7, 0.46, -0.1, .245, "P"),
    "Jordan Baker":    (9.2, 16.2, 6.2, 0.51, -0.2, .252, "N"),
    "Lance Barksdale": (9.2, 14.4, 6.2, 0.51, 0.5, .257, "N"),
    "Lance Barrett":   (8.8, 16.5, 5.7, 0.49, -0.2, .250, "P"),
    "Laz Diaz":        (8.1, 16.8, 8.6, 0.45, 0.0, .248, "P"),
    "Manny Gonzalez":  (9.2, 17.1, 7.2, 0.51, -0.1, .252, "N"),
    "Mark Carlson":    (8.5, 16.5, 5.8, 0.46, 0.3, .248, "P"),
    "Mark Ripperger":  (8.8, 16.2, 6.0, 0.49, 0.0, .250, "N"),
    "Mark Wegner":     (9.9, 15.5, 6.5, 0.54, 0.2, .258, "H"),
    "Marvin Hudson":   (5.7, 16.0, 6.2, 0.35, 0.0, .238, "P"),
    "Mike Estabrook":  (8.4, 16.8, 5.5, 0.47, -0.1, .245, "P"),
    "Nick Mahrley":    (9.0, 16.0, 6.0, 0.50, 0.0, .252, "N"),
    "Pat Hoberg":      (8.8, 16.5, 6.0, 0.50, -0.1, .250, "N"),
    "Phil Cuzzi":      (9.0, 15.5, 6.0, 0.50, 0.1, .252, "N"),
    "Quinn Wolcott":   (8.1, 19.6, 6.8, 0.45, -0.1, .242, "P"),
    "Roberto Ortiz":   (9.0, 16.0, 6.0, 0.50, 0.0, .250, "N"),
    "Ron Kulpa":       (6.8, 20.2, 8.2, 0.38, -0.2, .232, "P"),
    "Ryan Additon":    (9.5, 16.8, 6.2, 0.52, 0.3, .245, "P"),
    "Ryan Blakney":    (7.6, 17.0, 5.7, 0.43, 0.1, .240, "P"),
    "Scott Barry":     (8.4, 18.1, 7.6, 0.47, 0.3, .255, "P"),
    "Sean Barber":     (9.7, 15.8, 8.9, 0.53, 0.1, .251, "N"),
    "Shane Livensparger": (9.3, 15.2, 6.3, 0.51, 0.1, .256, "H"),
    "Stu Scheurwater": (8.5, 16.8, 5.8, 0.47, -0.1, .246, "P"),
    "Tom Hanahan":     (10.3, 14.6, 8.9, 0.57, -0.1, .265, "H"),
    "Tom Woodring":    (10.1, 16.0, 6.8, 0.55, 0.1, .260, "H"),
    "Tripp Gibson":    (9.3, 15.5, 6.2, 0.51, 0.2, .255, "H"),
    "Tyler Jones":     (8.4, 14.7, 7.1, 0.47, 0.1, .250, "N"),
    "Vic Carapazza":   (8.8, 16.8, 5.8, 0.49, -0.2, .247, "P"),
    "Will Little":     (9.3, 17.1, 8.8, 0.52, 0.0, .255, "N"),
}

# League average for reference (2023-2025 ~8.8 runs/game)
_LEAGUE_AVG_RUNS = 8.8

class UmpireFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; MLBEdge/2.2)"})

    def get_umpire_assignments(self) -> List[Dict]:
        try:
            r = self.session.get(REFMETRICS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            assignments = []
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        date_str = cols[0].text.strip()
                        umpire = cols[1].text.strip()
                        game_info = cols[2].text.strip()
                        if date_str == datetime.now().strftime("%Y-%m-%d"):
                            stats = self.get_umpire_stats(umpire)
                            assignments.append({
                                "date": date_str, "umpire": umpire,
                                "game_info": game_info, **stats,
                            })
            return assignments
        except Exception as e:
            print(f"  Umpire scrape error: {e}")
            return []

    @staticmethod
    def get_umpire_stats(name: str) -> Dict:
        """Look up rich umpire stats from database."""
        row = UMPIRE_DB.get(name)
        if row:
            avg_runs, k_g, bb_g, over_pct, home_adv, ba, favors = row
            run_impact = avg_runs - _LEAGUE_AVG_RUNS  # positive = more runs than avg
            if favors == "P":
                tendency = "tight"
            elif favors == "H":
                tendency = "loose"
            else:
                tendency = "neutral"
            return {
                "tendency": tendency,
                "avg_runs": avg_runs,
                "k_per_game": k_g,
                "bb_per_game": bb_g,
                "over_pct": over_pct,
                "home_advantage": home_adv,
                "ba": ba,
                "run_impact": round(run_impact, 1),
                "favors": favors,
                "in_database": True,
            }
        # Unknown umpire — neutral defaults
        return {
            "tendency": "neutral", "avg_runs": _LEAGUE_AVG_RUNS,
            "k_per_game": 16.0, "bb_per_game": 6.0, "over_pct": 0.50,
            "home_advantage": 0.0, "ba": .250, "run_impact": 0.0,
            "favors": "N", "in_database": False,
        }

    def get_umpire_for_game(self, home: str, away: str, assignments: List[Dict]) -> Optional[Dict]:
        for a in assignments:
            gi = a.get("game_info", "").upper()
            if home.upper() in gi or away.upper() in gi:
                return a
        return None

    def format_umpire_line(self, umpire: str, tendency: str = None) -> str:
        stats = self.get_umpire_stats(umpire)
        t = stats["tendency"]
        run_imp = stats["run_impact"]
        over_pct = stats["over_pct"]
        icons = {"tight": "🔵", "loose": "🔴", "neutral": "⚪"}
        icon = icons.get(t, "⚪")
        if stats["in_database"]:
            sign = "+" if run_imp > 0 else ""
            return f"{umpire} {icon} {t} | {sign}{run_imp:.1f}R | O:{over_pct:.0%} | K:{stats['k_per_game']:.0f}"
        return f"{umpire} {icon} {t}"
