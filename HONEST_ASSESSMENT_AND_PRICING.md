"""
MLB Edge v2.3 — Core Data Fetcher
MLB Stats API calls with caching and rate limiting.
"""
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

from config import (MLB_API, MLB_SCHEDULE, API_DELAY, REQUEST_TIMEOUT,
                    MAX_RETRIES, RETRY_DELAY, RECENT_GAMES, CACHE_DIR)

CACHE_TTL = {
    "recent_schedule": 3 * 3600,
    "recent_games": 3 * 3600,
    "team_stats": 6 * 3600,
}


class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MLBEdge/2.3"})
        self._last_call = 0
        self.call_count = 0
        self.cache_hits = 0

    def _wait(self):
        elapsed = time.time() - self._last_call
        if elapsed < API_DELAY:
            time.sleep(API_DELAY - elapsed)
        self._last_call = time.time()

    def _get(self, url: str, params: dict = None) -> Optional[dict]:
        for attempt in range(MAX_RETRIES):
            try:
                self._wait()
                self.call_count += 1
                r = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
        return None

    def _cache_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return CACHE_DIR / f"{safe}.json"

    def _get_cached(self, key: str) -> Optional[Any]:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            age = time.time() - path.stat().st_mtime
            prefix = key.split("_")[0]
            ttl = CACHE_TTL.get(prefix, 3 * 3600)
            # Match longer prefixes
            for k, v in CACHE_TTL.items():
                if key.startswith(k):
                    ttl = v
                    break
            if age > ttl:
                return None
            with open(path, 'r') as f:
                data = json.load(f)
            self.cache_hits += 1
            return data.get("content")
        except Exception:
            return None

    def _set_cache(self, key: str, content: Any):
        try:
            with open(self._cache_path(key), 'w') as f:
                json.dump({"content": content, "timestamp": time.time()}, f)
        except Exception:
            pass

    def get_recent_schedule(self, days_back: int = 7) -> dict:
        """Get schedules for last N days. Cached per day."""
        all_games = {}
        for i in range(1, days_back + 1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            ck = f"recent_schedule_{date}"
            cached = self._get_cached(ck)
            if cached:
                all_games[date] = cached
                continue
            data = self._get(MLB_SCHEDULE, {"date": date, "sportId": "1", "hydrate": "linescore"})
            if data and "dates" in data:
                games = [g for d in data["dates"] for g in d.get("games", [])]
                all_games[date] = games
                self._set_cache(ck, games)
        return all_games

    def get_team_recent_games(self, team_id: int, num: int = None, days_back: int = 7) -> list:
        """Get last N completed games for a team."""
        if num is None:
            num = RECENT_GAMES
        ck = f"recent_games_{team_id}_{num}"
        cached = self._get_cached(ck)
        if cached:
            return cached
        all_games = self.get_recent_schedule(days_back)
        team_games = []
        for date, games in all_games.items():
            for g in games:
                away_id = g.get("teams", {}).get("away", {}).get("team", {}).get("id")
                home_id = g.get("teams", {}).get("home", {}).get("team", {}).get("id")
                status = g.get("status", {}).get("detailedState", "")
                if (away_id == team_id or home_id == team_id) and "Final" in status:
                    team_games.append(g)
        team_games.sort(key=lambda x: x.get("gameDate", ""), reverse=True)
        recent = team_games[:num]
        self._set_cache(ck, recent)
        return recent

    def stats(self) -> dict:
        total = max(1, self.call_count)
        return {
            "api_calls": self.call_count,
            "cache_hits": self.cache_hits,
            "hit_rate": f"{self.cache_hits / total * 100:.1f}%",
        }
