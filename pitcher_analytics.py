"""
MLB Edge v2.3 — Lines Fetcher
ESPN Scoreboard API — free, no key, no signup, no credit card.
Returns DraftKings lines: moneyline, run line, totals, with opening lines.
"""
import requests
from typing import Optional, Dict, List
from config import REQUEST_TIMEOUT

ESPN_MLB = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

class LinesFetcher:
    def __init__(self, api_key: str = None):
        # api_key kept for backward compat but ignored — ESPN needs none
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MLBEdge/2.3"})

    def get_mlb_lines(self) -> List[Dict]:
        """Fetch all MLB lines from ESPN scoreboard — zero signup required."""
        try:
            r = self.session.get(ESPN_MLB, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            games = []
            for event in data.get("events", []):
                comp = event.get("competitions", [{}])[0]
                teams = comp.get("competitors", [])
                odds_list = comp.get("odds", [])
                if not teams or len(teams) < 2:
                    continue
                home = [t for t in teams if t.get("homeAway") == "home"]
                away = [t for t in teams if t.get("homeAway") == "away"]
                if not home or not away:
                    continue
                home = home[0]
                away = away[0]
                home_name = home.get("team", {}).get("displayName", "")
                away_name = away.get("team", {}).get("displayName", "")
                status = comp.get("status", {}).get("type", {}).get("name", "")

                result = {
                    "home_team": home_name,
                    "away_team": away_name,
                    "status": status,
                    "moneyline": None,
                    "totals": None,
                    "spread": None,
                    "moneyline_open": None,
                }
                if odds_list:
                    o = odds_list[0]
                    result.update(self._parse_odds(o, home_name, away_name))
                games.append(result)
            return games
        except Exception as e:
            print(f"  ⚠️ ESPN lines error: {e}")
            return []

    @staticmethod
    def _parse_odds(o: dict, home_name: str, away_name: str) -> dict:
        """Parse ESPN odds object into our standard format."""
        result = {}
        # Moneyline
        ml = o.get("moneyline", {})
        home_ml_str = ml.get("home", {}).get("close", {}).get("odds")
        away_ml_str = ml.get("away", {}).get("close", {}).get("odds")
        home_ml_open = ml.get("home", {}).get("open", {}).get("odds")
        away_ml_open = ml.get("away", {}).get("open", {}).get("odds")

        def to_int(s):
            if s is None:
                return None
            try:
                return int(str(s).replace("+", ""))
            except (ValueError, TypeError):
                return None

        hml = to_int(home_ml_str)
        aml = to_int(away_ml_str)
        if hml is not None and aml is not None:
            result["moneyline"] = {home_name: hml, away_name: aml}
        hmlo = to_int(home_ml_open)
        amlo = to_int(away_ml_open)
        if hmlo is not None and amlo is not None:
            result["moneyline_open"] = {home_name: hmlo, away_name: amlo}

        # Totals (O/U)
        total = o.get("total", {})
        ou_line = o.get("overUnder")
        over_odds = to_int(total.get("over", {}).get("close", {}).get("odds"))
        under_odds = to_int(total.get("under", {}).get("close", {}).get("odds"))
        over_open = to_int(total.get("over", {}).get("open", {}).get("odds"))
        ou_line_open_str = total.get("over", {}).get("open", {}).get("line", "")
        ou_line_open = None
        if ou_line_open_str:
            try:
                ou_line_open = float(str(ou_line_open_str).replace("o", "").replace("u", ""))
            except (ValueError, TypeError):
                pass
        if ou_line:
            result["totals"] = {
                "line": float(ou_line),
                "over_price": over_odds,
                "under_price": under_odds,
                "open_line": ou_line_open,
            }

        # Run line (spread)
        ps = o.get("pointSpread", {})
        home_rl = ps.get("home", {}).get("close", {})
        away_rl = ps.get("away", {}).get("close", {})
        home_rl_open = ps.get("home", {}).get("open", {})
        if home_rl.get("line"):
            try:
                result["spread"] = {
                    "home_line": float(home_rl["line"]),
                    "home_price": to_int(home_rl.get("odds")),
                    "away_line": float(away_rl.get("line", 0)),
                    "away_price": to_int(away_rl.get("odds")),
                    "open_home_line": float(home_rl_open.get("line", 0)) if home_rl_open.get("line") else None,
                }
            except (ValueError, TypeError):
                pass

        return result

    def get_game_line(self, home: str, away: str, games: list) -> Optional[Dict]:
        """Match a game by team names (fuzzy)."""
        h, a = home.upper(), away.upper()
        for g in games:
            gh = g.get("home_team", "").upper()
            ga = g.get("away_team", "").upper()
            # Check if team name is contained in either direction
            if (h in gh or gh in h) and (a in ga or ga in a):
                return g
            if (h in ga or ga in h) and (a in gh or gh in a):
                return g
        return None

    def format_line(self, game: Dict) -> str:
        """Format line for display."""
        if not game:
            return "No line available"
        parts = []
        ml = game.get("moneyline")
        if ml:
            items = list(ml.items())
            if len(items) == 2:
                n1, o1 = items[0]
                n2, o2 = items[1]
                s1 = f"+{o1}" if o1 > 0 else str(o1)
                s2 = f"+{o2}" if o2 > 0 else str(o2)
                # Abbreviate team names
                a1 = n1.split()[-1][:3].upper() if " " in n1 else n1[:3].upper()
                a2 = n2.split()[-1][:3].upper() if " " in n2 else n2[:3].upper()
                parts.append(f"ML: {a1} {s1} / {a2} {s2}")
        totals = game.get("totals")
        if totals and totals.get("line"):
            parts.append(f"O/U: {totals['line']}")
        return " | ".join(parts) if parts else "No line available"
