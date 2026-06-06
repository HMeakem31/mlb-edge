"""
MLB Edge v2.3 — Statcast Fetcher
Baseball Savant CSV leaderboards — free, no key, no signup.
One HTTP call each for pitchers + batters, cached 12 hours.
"""
import csv
import io
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional
from config import CACHE_DIR

_SAVANT_EXPECTED = "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
_SAVANT_STATCAST = "https://baseballsavant.mlb.com/leaderboard/statcast"
_CACHE_TTL = 12 * 3600  # 12 hours
_session = requests.Session()
_session.headers.update({"User-Agent": "MLBEdge/2.3"})


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"savant_{key}.json"


def _load_cache(key: str) -> Optional[dict]:
    p = _cache_path(key)
    if not p.exists():
        return None
    try:
        if time.time() - p.stat().st_mtime > _CACHE_TTL:
            return None
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(key: str, data: dict):
    try:
        with open(_cache_path(key), 'w') as f:
            json.dump(data, f)
    except Exception:
        pass


def _fetch_csv(url: str, params: dict) -> list:
    """Fetch a Baseball Savant CSV and parse with stdlib csv — no pandas."""
    try:
        r = _session.get(url, params=params, timeout=30)
        if r.status_code != 200 or len(r.content) < 100:
            return []
        text = r.text.replace('\ufeff', '')
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        print(f"  Savant CSV error: {e}")
        return []


def get_pitcher_expected(year: int = 2026, min_pa: int = 50) -> Dict[int, dict]:
    """
    Get xERA, xBA, xSLG, xwOBA for all qualified pitchers.
    Returns {player_id: {name, xera, era, xba, ba, xwoba, woba, era_xera_gap}}.
    One HTTP call, cached 12 hours.
    """
    cached = _load_cache(f"pitcher_expected_{year}")
    if cached:
        return {int(k): v for k, v in cached.items()}

    rows = _fetch_csv(_SAVANT_EXPECTED, {
        "type": "pitcher", "year": year, "position": "",
        "team": "", "min": min_pa, "csv": "true"
    })
    result = {}
    for row in rows:
        try:
            pid = int(row.get("player_id", 0))
            if not pid:
                continue
            name = row.get("last_name, first_name", "?")
            era = _f(row.get("era"))
            xera = _f(row.get("xera"))
            ba = _f(row.get("ba"))
            xba = _f(row.get("est_ba"))
            woba = _f(row.get("woba"))
            xwoba = _f(row.get("est_woba"))
            slg = _f(row.get("slg"))
            xslg = _f(row.get("est_slg"))
            result[pid] = {
                "name": name, "era": era, "xera": xera,
                "ba": ba, "xba": xba, "woba": woba, "xwoba": xwoba,
                "slg": slg, "xslg": xslg,
                "era_xera_gap": round(era - xera, 3) if era and xera else 0,
                "pa": int(row.get("pa", 0) or 0),
            }
        except (ValueError, TypeError):
            continue

    if result:
        _save_cache(f"pitcher_expected_{year}", {str(k): v for k, v in result.items()})
        print(f"  ✅ Savant: {len(result)} pitchers (xERA, xwOBA)")
    return result


def get_batter_expected(year: int = 2026, min_pa: int = 50) -> Dict[int, dict]:
    """
    Get xBA, xSLG, xwOBA for all qualified batters.
    Returns {player_id: {name, ba, xba, slg, xslg, woba, xwoba, luck_gap}}.
    One HTTP call, cached 12 hours.
    """
    cached = _load_cache(f"batter_expected_{year}")
    if cached:
        return {int(k): v for k, v in cached.items()}

    rows = _fetch_csv(_SAVANT_EXPECTED, {
        "type": "batter", "year": year, "position": "",
        "team": "", "min": min_pa, "csv": "true"
    })
    result = {}
    for row in rows:
        try:
            pid = int(row.get("player_id", 0))
            if not pid:
                continue
            name = row.get("last_name, first_name", "?")
            ba = _f(row.get("ba"))
            xba = _f(row.get("est_ba"))
            slg = _f(row.get("slg"))
            xslg = _f(row.get("est_slg"))
            woba = _f(row.get("woba"))
            xwoba = _f(row.get("est_woba"))
            result[pid] = {
                "name": name, "ba": ba, "xba": xba,
                "slg": slg, "xslg": xslg, "woba": woba, "xwoba": xwoba,
                "luck_gap": round((woba or 0) - (xwoba or 0), 3) if woba and xwoba else 0,
                "pa": int(row.get("pa", 0) or 0),
            }
        except (ValueError, TypeError):
            continue

    if result:
        _save_cache(f"batter_expected_{year}", {str(k): v for k, v in result.items()})
        print(f"  ✅ Savant: {len(result)} batters (xBA, xwOBA)")
    return result


def get_pitcher_statcast(year: int = 2026, min_bbe: int = 50) -> Dict[int, dict]:
    """
    Get exit velocity, barrel%, hard hit% for pitchers.
    One HTTP call, cached 12 hours.
    """
    cached = _load_cache(f"pitcher_statcast_{year}")
    if cached:
        return {int(k): v for k, v in cached.items()}

    rows = _fetch_csv(_SAVANT_STATCAST, {
        "type": "pitcher", "year": year, "position": "",
        "team": "", "min": min_bbe, "csv": "true"
    })
    result = {}
    for row in rows:
        try:
            pid = int(row.get("player_id", 0))
            if not pid:
                continue
            result[pid] = {
                "name": row.get("last_name, first_name", "?"),
                "avg_ev": _f(row.get("avg_hit_speed")),
                "max_ev": _f(row.get("max_hit_speed")),
                "barrel_pct": _f(row.get("brl_percent")),
                "barrels": int(row.get("barrels", 0) or 0),
                "ev95_pct": _f(row.get("ev95percent")),
                "avg_distance": _f(row.get("avg_distance")),
                "gb_pct": _f(row.get("gb")),
            }
        except (ValueError, TypeError):
            continue

    if result:
        _save_cache(f"pitcher_statcast_{year}", {str(k): v for k, v in result.items()})
        print(f"  ✅ Savant: {len(result)} pitcher Statcast (EV, barrel%)")
    return result


def _f(val) -> Optional[float]:
    """Safe float conversion."""
    if val is None or val == '' or val == 'None' or val == 'null':
        return None
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return None


def get_pitcher_xera(pitcher_id: int, expected_db: dict) -> Optional[dict]:
    """Look up a specific pitcher's expected stats from the pre-loaded DB."""
    data = expected_db.get(pitcher_id)
    if not data:
        return None
    gap = data.get("era_xera_gap", 0)
    # gap = ERA - xERA
    # Positive gap = ERA higher than xERA = UNLUCKY (ERA should drop)
    # Negative gap = ERA lower than xERA = LUCKY (ERA will regress up)
    if gap > 0.50:
        flag = "🍀 UNLUCKY"
        detail = f'ERA {data["era"]:.2f} is {gap:.2f} ABOVE xERA {data["xera"]:.2f} — ERA should improve (drop)'
    elif gap < -0.50:
        flag = "⚠️ LUCKY"
        detail = f'ERA {data["era"]:.2f} is {abs(gap):.2f} BELOW xERA {data["xera"]:.2f} — regression risk UP'
    else:
        flag = ""
        detail = "ERA and xERA aligned"
    return {
        "era": data["era"],
        "xera": data["xera"],
        "gap": gap,
        "xwoba": data.get("xwoba"),
        "woba": data.get("woba"),
        "xba": data.get("xba"),
        "flag": flag,
        "detail": detail,
        "pa": data.get("pa", 0),
    }
