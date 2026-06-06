"""
MLB Edge v2.4 — Injury / IL Fetcher
Single API call to statsapi.mlb.com/api/v1/injuries?sportId=1
Cross-references probable pitchers with IL list and first-start-back flags.
"""
import requests
from typing import Dict, List, Optional
from config import MLB_API, REQUEST_TIMEOUT


def fetch_injuries() -> List[Dict]:
    """Fetch all current injuries for MLB (sportId=1). One call."""
    try:
        r = requests.get(
            f"{MLB_API}/injuries?sportId=1",
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        injuries = []
        for entry in data.get("injuries", []):
            player = entry.get("player", {})
            team = entry.get("team", {})
            injuries.append({
                "player_id": player.get("id"),
                "player_name": player.get("fullName", ""),
                "team_id": team.get("id"),
                "team_name": team.get("name", ""),
                "status": entry.get("status", {}).get("description", "Unknown"),
                "status_code": entry.get("status", {}).get("code", ""),
                "injury_type": entry.get("injuryType", "Unknown"),
                "description": entry.get("note", ""),
                "from_date": entry.get("fromDate", ""),
                " DL_or_IL": entry.get("status", {}).get("code", "") in ("D10", "D15", "D60", "D7"),
            })
        return injuries
    except Exception as e:
        print(f"  ⚠️ Injury fetch error: {e}")
        return []


def check_pitcher_injury_flags(
    pitcher_id: Optional[int],
    pitcher_name: str,
    injuries: List[Dict],
) -> Dict:
    """
    Check if a pitcher is currently on IL, or recently returned.
    Returns dict with flags for report integration.
    """
    flags = {
        "on_il": False,
        "il_desc": "",
        "first_start_back": False,
        "first_start_note": "",
        "is_questionable": False,
        "questionable_note": "",
    }
    if not pitcher_id or not injuries:
        return flags

    # Look for exact player match
    for inj in injuries:
        if inj.get("player_id") == pitcher_id:
            status = inj.get("status", "")
            code = inj.get("status_code", "")
            desc = inj.get("description", "")
            # Active IL codes
            if code in ("D10", "D15", "D60", "D7", "IL"):
                flags["on_il"] = True
                flags["il_desc"] = f"{status}: {desc}"
            elif code in ("D", "DTD") or "day-to-day" in status.lower():
                flags["is_questionable"] = True
                flags["questionable_note"] = f"{status}: {desc}"
            break

    # Heuristic: if pitcher is NOT on IL but has very few 2026 IP/GS, flag first-start-back
    # This is a weak signal; we leave it to the caller to check stats.
    return flags


def cross_reference_probables(
    games: List[Dict],
    injuries: List[Dict],
) -> Dict[int, Dict]:
    """
    Cross-reference all probable pitchers in today's games with injury list.
    Returns dict: {pitcher_id: flags_dict}
    """
    results = {}
    for g in games:
        for side in ("away", "home"):
            pid = g.get(f"{side}_pitcher_id")
            pname = g.get(f"{side}_pitcher_name", "TBD")
            if pid:
                results[pid] = check_pitcher_injury_flags(pid, pname, injuries)
    return results
