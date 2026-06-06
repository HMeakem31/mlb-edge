"""
MLB Edge v2.4 — Player Profiles Engine
Batter: OPS+ proxy, sprint speed, empty game rate
Pitcher: style classification (power/finesse), pitch mix, arsenal
All from Baseball Savant + existing data. 2 new CSV calls, cached 12hr.
"""
import csv
import io
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional, List
from config import CACHE_DIR, PARK_FACTORS

_SAVANT_SPRINT = "https://baseballsavant.mlb.com/leaderboard/sprint_speed"
_SAVANT_ARSENALS = "https://baseballsavant.mlb.com/leaderboard/pitch-arsenals"
_CACHE_TTL = 12 * 3600
_session = requests.Session()
_session.headers.update({"User-Agent": "MLBEdge/2.4"})

# League-average xwOBA estimate (2025 actual ~.310, 2026 similar)
LEAGUE_XWOBA = 0.310
LEAGUE_OPS = 0.711

# Pitch type display names
PITCH_NAMES = {
    "ff": "4-Seam Fastball", "si": "Sinker",
    "fc": "Cutter", "sl": "Slider", "ch": "Changeup",
    "cu": "Curveball", "fs": "Splitter", "kn": "Knuckleball",
    "st": "Sweeper", "sv": "Slurve",
}
# Pitch type keys in Savant CSV
PITCH_KEYS = ["ff", "si", "fc", "sl", "ch", "cu", "fs", "kn", "st", "sv"]


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
        with open(_cache_path(key), "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _fetch_csv(url: str, params: dict) -> list:
    try:
        r = _session.get(url, params=params, timeout=30)
        if r.status_code != 200 or len(r.content) < 100:
            return []
        text = r.text.replace("\ufeff", "")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        print(f"  Savant CSV error ({url}): {e}")
        return []


def _f(val):
    """Safe float conversion."""
    if val is None or val == "" or val == "None" or val == "null":
        return None
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════
# SPRINT SPEED (batter speed/athleticism metrics)
# ═══════════════════════════════════════════════════════════════

def get_sprint_speed_db(year: int = 2026) -> Dict[int, dict]:
    """Fetch sprint speed leaderboard. 1 HTTP call, cached 12hr."""
    cached = _load_cache(f"sprint_speed_{year}")
    if cached:
        print(f"  ✅ Sprint speed: {len(cached)} players (cached)")
        return {int(k): v for k, v in cached.items()}

    rows = _fetch_csv(_SAVANT_SPRINT, {
        "year": year, "position": "", "team": "", "min": "5", "csv": "true"
    })
    result = {}
    for row in rows:
        try:
            pid = int(row.get("player_id", 0))
            if not pid:
                continue
            ss = _f(row.get("sprint_speed"))
            bolts = int(row.get("bolts", 0) or 0)
            hp_to_1b = _f(row.get("hp_to_1b"))
            comp_runs = int(row.get("competitive_runs", 0) or 0)
            # Speed tier
            if ss and ss >= 30.0:
                tier = "elite"
            elif ss and ss >= 28.0:
                tier = "plus"
            elif ss and ss >= 26.5:
                tier = "average"
            elif ss:
                tier = "below"
            else:
                tier = "unknown"
            result[pid] = {
                "sprint_speed": ss,
                "bolts": bolts,
                "hp_to_1b": hp_to_1b,
                "competitive_runs": comp_runs,
                "speed_tier": tier,
                "name": row.get("last_name, first_name", "?"),
            }
        except (ValueError, TypeError):
            continue

    if result:
        _save_cache(f"sprint_speed_{year}", {str(k): v for k, v in result.items()})
        print(f"  ✅ Sprint speed: {len(result)} players")
    return result


def get_speed_profile(player_id: int, sprint_db: dict) -> Optional[dict]:
    """Get speed metrics for a specific player."""
    return sprint_db.get(player_id)


# ═══════════════════════════════════════════════════════════════
# OPS+ PROXY (park-adjusted offensive production)
# ═══════════════════════════════════════════════════════════════

def calculate_ops_plus(ops: float, team_id: int = None) -> Optional[float]:
    """
    Simplified OPS+ approximation.
    OPS+ = 100 * (OPS / lgOPS) / park_factor
    """
    if not ops or ops <= 0:
        return None
    pf = PARK_FACTORS.get(team_id, 1.00) if team_id else 1.00
    raw = (ops / LEAGUE_OPS) * 100 / pf
    return round(raw, 1)


def calculate_wrc_plus(xwoba: float, team_id: int = None) -> Optional[float]:
    """
    wRC+ proxy from xwOBA.
    wRC+ ≈ (xwOBA / lg_xwOBA) * 100 / park_factor
    """
    if not xwoba or xwoba <= 0:
        return None
    pf = PARK_FACTORS.get(team_id, 1.00) if team_id else 1.00
    raw = (xwoba / LEAGUE_XWOBA) * 100 / pf
    return round(raw, 1)


# ═══════════════════════════════════════════════════════════════
# EMPTY GAME RATE (0-hit games)
# ═══════════════════════════════════════════════════════════════

def calculate_empty_game_rate(game_log: list) -> dict:
    """
    Calculate % of games where batter went 0-for with at least 1 AB.
    From game log data (already fetched in hitter_profile).
    """
    if not game_log:
        return {"empty_rate": None, "empty_games": 0, "total_games": 0, "detail": "N/A"}

    total = 0
    empty = 0
    for g in game_log:
        ab = g.get("ab", 0) or 0
        hits = g.get("hits", 0) or 0
        if ab > 0:
            total += 1
            if hits == 0:
                empty += 1

    if total == 0:
        return {"empty_rate": None, "empty_games": 0, "total_games": 0, "detail": "N/A"}

    rate = empty / total
    if rate <= 0.10:
        tier = "rarely"
    elif rate <= 0.25:
        tier = "occasional"
    elif rate <= 0.40:
        tier = "frequent"
    else:
        tier = "very_frequent"

    return {
        "empty_rate": round(rate, 2),
        "empty_games": empty,
        "total_games": total,
        "rate_tier": tier,
        "detail": f"{empty}/{total} games ({(1-rate)*100:.0f}% hit rate)",
    }


# ═══════════════════════════════════════════════════════════════
# PITCHER STYLE CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

def get_pitch_arsenal_db(year: int = 2026, min_pa: int = 50) -> Dict[int, dict]:
    """Fetch pitcher pitch arsenals with velocity per pitch type. 1 HTTP call."""
    cached = _load_cache(f"arsenals_{year}")
    if cached:
        print(f"  ✅ Pitch arsenals: {len(cached)} pitchers (cached)")
        return {int(k): v for k, v in cached.items()}

    rows = _fetch_csv(_SAVANT_ARSENALS, {
        "year": year, "min": min_pa, "csv": "true"
    })
    result = {}
    for row in rows:
        try:
            pid = int(row.get("pitcher", 0))
            if not pid:
                continue
            pitches = {}
            for pk in PITCH_KEYS:
                velo = _f(row.get(f"{pk}_avg_speed"))
                if velo and velo > 50:  # valid velocity in mph
                    pitches[pk] = velo

            if not pitches:
                continue

            # Compute average fastball velocity (use ff or si if available)
            ff_velo = pitches.get("ff") or pitches.get("si")
            result[pid] = {
                "name": row.get("last_name, first_name", "?"),
                "pitches": pitches,
                "ff_velo": ff_velo,
                "pitch_count": len(pitches),
            }
        except (ValueError, TypeError):
            continue

    if result:
        _save_cache(f"arsenals_{year}", {str(k): v for k, v in result.items()})
        print(f"  ✅ Pitch arsenals: {len(result)} pitchers")
    return result


def classify_pitcher_style(
    pitcher_stats: dict,
    arsenal: dict = None,
    statcast: dict = None,
) -> dict:
    """
    Classify pitcher as Power / Finesse / Mixed.
    Uses: fastball velocity, K/9, BB/9, GB%, and pitch mix.
    """
    style = "unknown"
    signals_power = 0
    signals_finesse = 0
    reasons = []

    k9 = float(pitcher_stats.get("k9", 0) or 0)
    bb9 = float(pitcher_stats.get("bb9", 0) or 0)
    gb_pct = None

    # 1. Fastball velocity from pitch arsenal
    ff_velo = None
    if arsenal:
        ff_velo = arsenal.get("ff_velo")
    if ff_velo:
        if ff_velo >= 96.0:
            signals_power += 3
            reasons.append(f"Elite velo ({ff_velo:.1f}mph FB)")
        elif ff_velo >= 94.0:
            signals_power += 2
            reasons.append(f"Plus velo ({ff_velo:.1f}mph FB)")
        elif ff_velo < 91.0:
            signals_finesse += 2
            reasons.append(f"Below-avg velo ({ff_velo:.1f}mph FB)")

    # 2. Strikeout rate
    if k9 >= 10.0:
        signals_power += 2
        reasons.append(f"Elite K/9 ({k9:.1f})")
    elif k9 >= 9.0:
        signals_power += 1
    elif k9 < 7.0:
        signals_finesse += 2
        reasons.append(f"Low K/9 ({k9:.1f})")

    # 3. Walk rate (command = finesse trait)
    if bb9 and bb9 < 2.0:
        signals_finesse += 1
        reasons.append(f"Elite command (BB/9 {bb9:.1f})")
    elif bb9 and bb9 > 4.0:
        signals_power += 1  # wild power pitchers exist

    # 4. Ground ball rate from statcast
    if statcast:
        try:
            gb_pct = _f(statcast.get("gb"))
        except Exception:
            gb_pct = None
    if gb_pct and gb_pct >= 50:
        signals_finesse += 1
        reasons.append(f"GB pitcher ({gb_pct:.0f}%)")
    elif gb_pct and gb_pct < 35:
        signals_power += 1

    # 5. Pitch count in arsenal (more = craftier = finesse)
    if arsenal and arsenal.get("pitch_count", 0) >= 4:
        signals_finesse += 1
        reasons.append(f"{arsenal['pitch_count']}-pitch mix")

    # Classification
    if signals_power >= 4 and signals_power > signals_finesse + 2:
        style = "power"
    elif signals_finesse >= 4 and signals_finesse > signals_power + 2:
        style = "finesse"
    elif signals_power >= 3 and signals_finesse >= 3:
        style = "hybrid"
    elif signals_power > signals_finesse:
        style = "power-leaning"
    elif signals_finesse > signals_power:
        style = "finesse-leaning"
    else:
        style = "balanced"

    style_display = {
        "power": "🔥 Power",
        "power-leaning": "💪 Power-Leaning",
        "finesse": "🎯 Finesse",
        "finesse-leaning": "🧠 Finesse-Leaning",
        "hybrid": "⚡ Hybrid (Power + Craft)",
        "balanced": "⚖️ Balanced",
        "unknown": "❓ Unknown",
    }

    return {
        "style": style,
        "display": style_display.get(style, style),
        "ff_velo": ff_velo,
        "k9": k9,
        "bb9": bb9,
        "gb_pct": gb_pct,
        "signals_power": signals_power,
        "signals_finesse": signals_finesse,
        "reasons": reasons,
        "arsenal_detail": _format_pitch_mix(arsenal) if arsenal else "",
    }


def _format_pitch_mix(arsenal: dict) -> str:
    """Format pitch mix as human-readable string."""
    if not arsenal or not arsenal.get("pitches"):
        return ""
    pitches = arsenal["pitches"]
    parts = []
    # Sort by velocity (fastest first)
    sorted_pitches = sorted(pitches.items(), key=lambda x: x[1], reverse=True)
    for pk, velo in sorted_pitches[:5]:
        name = PITCH_NAMES.get(pk, pk.upper())
        parts.append(f"{name} {velo:.0f}mph")
    return " | ".join(parts)


# ═══════════════════════════════════════════════════════════════
# BATTER vs PITCHER STYLE MATCHUP
# ═══════════════════════════════════════════════════════════════

def batter_vs_style(
    batter_stats: dict,
    batter_savant: dict,
    pitcher_style: str,
) -> dict:
    """
    Estimate how a batter profiles against a given pitcher style.
    Uses: batter K%, ISO, contact rate, xwOBA.
    Returns a matchup note + advantage score.
    """
    if not batter_stats or pitcher_style == "unknown":
        return {"edge": "neutral", "score": 50, "note": ""}

    # Derive batter profile from stats
    ab = batter_stats.get("ab", 20) or 20
    so = batter_stats.get("so", 0) or 0
    hits = batter_stats.get("hits", 0) or 0
    k_pct = so / ab if ab > 0 else 0.22

    iso = 0.150
    if batter_savant:
        xslg = batter_savant.get("xslg", 0) or 0
        xba = batter_savant.get("xba", 0) or 0
        iso = (xslg - xba) if xslg and xba else 0.150
        if iso < 0:
            iso = 0.150

    score = 50
    notes = []

    # High-K batters vs Power pitchers → mismatch for batter
    if "power" in pitcher_style and k_pct > 0.25:
        score -= 12
        notes.append(f"High K% ({k_pct:.0%}) vs power arm — K risk elevated")

    # Low-K batters vs Power pitchers → do better
    if "power" in pitcher_style and k_pct < 0.18:
        score += 8
        notes.append(f"Good contact rate ({k_pct:.0%}) vs power — can put ball in play")

    # High-ISO batters vs Finesse → advantage (can drive mistakes)
    if "finesse" in pitcher_style and iso > 0.200:
        score += 10
        notes.append(f"Power bat (ISO .{str(iso).replace('0.','')[:3]}) vs finesse — can do damage")

    # Low-power batters vs Finesse → pitchers can challenge them
    if "finesse" in pitcher_style and iso < 0.120:
        score -= 6
        notes.append(f"Low power (ISO .{str(iso).replace('0.','')[:3]}) vs command pitcher")

    # General: same-handedness already handled by platoon, style is additive
    if score >= 58:
        edge = "advantage"
    elif score >= 53:
        edge = "slight_advantage"
    elif score <= 42:
        edge = "disadvantage"
    elif score <= 47:
        edge = "slight_disadvantage"
    else:
        edge = "neutral"

    return {
        "edge": edge,
        "score": score,
        "k_pct": round(k_pct, 3),
        "iso": round(iso, 3),
        "note": " | ".join(notes) if notes else "Neutral matchup",
    }


# ═══════════════════════════════════════════════════════════════
# COMPOSITE PLAYER CARD
# ═══════════════════════════════════════════════════════════════

def build_batter_card(
    player_id: int,
    season_stats: dict,
    game_log: list,
    savant_data: dict,
    sprint_db: dict,
    team_id: int = None,
) -> dict:
    """Build a complete batter profile card for the report."""
    # OPS+ proxy
    ops = None
    if season_stats:
        obp_s = season_stats.get("obp", ".000")
        slg_s = season_stats.get("slg", ".000")
        try:
            obp = float(obp_s) if obp_s else 0
            slg = float(slg_s) if slg_s else 0
            ops = obp + slg
        except (ValueError, TypeError):
            ops = None

    ops_plus = calculate_ops_plus(ops, team_id) if ops else None
    wrc_plus = None
    if savant_data and savant_data.get("xwoba"):
        wrc_plus = calculate_wrc_plus(savant_data["xwoba"], team_id)

    # Speed profile
    speed = get_speed_profile(player_id, sprint_db) or {}

    # Empty game rate
    empty = calculate_empty_game_rate(game_log)

    return {
        "ops_plus": ops_plus,
        "wrc_plus": wrc_plus,
        "sprint_speed": speed.get("sprint_speed"),
        "speed_tier": speed.get("speed_tier", "unknown"),
        "bolts": speed.get("bolts", 0),
        "hp_to_1b": speed.get("hp_to_1b"),
        "competitive_runs": speed.get("competitive_runs", 0),
        "empty_game_rate": empty,
    }


def build_pitcher_card(
    pitcher_id: int,
    pitcher_stats: dict,
    arsenal_db: dict,
    statcast_db: dict = None,
) -> dict:
    """Build a complete pitcher profile card for the report."""
    arsenal = arsenal_db.get(pitcher_id) if arsenal_db else None
    statcast = statcast_db.get(pitcher_id) if statcast_db else None

    style = classify_pitcher_style(pitcher_stats or {}, arsenal, statcast)

    return {
        "style": style,
        "arsenal": arsenal,
        "statcast": statcast,
    }


def format_batter_card_html(card: dict) -> str:
    """Format batter card as compact HTML for the report."""
    parts = []

    # OPS+ / wRC+
    ops_plus = card.get("ops_plus")
    wrc_plus = card.get("wrc_plus")
    if wrc_plus:
        color = "var(--green)" if wrc_plus >= 120 else ("var(--yellow)" if wrc_plus >= 100 else "var(--red)")
        parts.append(f'<span style="color:{color};font-weight:600">wRC+ {wrc_plus:.0f}</span>')
    elif ops_plus:
        color = "var(--green)" if ops_plus >= 120 else ("var(--yellow)" if ops_plus >= 100 else "var(--red)")
        parts.append(f'<span style="color:{color};font-weight:600">OPS+ {ops_plus:.0f}</span>')

    # Speed
    ss = card.get("sprint_speed")
    if ss:
        color = "var(--green)" if ss >= 29.0 else ("var(--yellow)" if ss >= 27.0 else "var(--muted)")
        parts.append(f'<span style="color:{color}">🏃 {ss:.1f} ft/s</span>')
    bolts = card.get("bolts", 0)
    if bolts > 0:
        parts.append(f'⚡ {bolts} bolts')
    comp_runs = card.get("competitive_runs", 0)
    if comp_runs > 0:
        parts.append(f'🔄 {comp_runs} runs')

    # Empty game rate
    empty = card.get("empty_game_rate", {})
    empty_detail = empty.get("detail", "")
    if empty_detail and empty_detail != "N/A":
        er = empty.get("empty_rate", 0)
        color = "var(--red)" if er and er > 0.30 else ("var(--orange)" if er and er > 0.20 else "var(--green)")
        parts.append(f'<span style="color:{color}">📭 {empty_detail}</span>')

    return " · ".join(parts) if parts else ""


def format_pitcher_card_html(card: dict) -> str:
    """Format pitcher card as compact HTML for the report."""
    style = card.get("style", {})
    parts = []

    # Style classification
    display = style.get("display", "Unknown")
    parts.append(f'<span style="font-weight:700;font-size:0.82rem">{display}</span>')

    # FF velo
    ff_velo = style.get("ff_velo")
    if ff_velo:
        color = "var(--red)" if ff_velo >= 96 else ("var(--orange)" if ff_velo >= 94 else "var(--muted)")
        parts.append(f'<span style="color:{color}">🔥 {ff_velo:.0f}mph FB</span>')

    # K/9
    k9 = style.get("k9")
    if k9:
        parts.append(f'K/9 {k9:.1f}')

    # GB%
    gb = style.get("gb_pct")
    if gb:
        parts.append(f'GB {gb:.0f}%')

    # Reason flags
    reasons = style.get("reasons", [])
    if reasons:
        parts.append(f'<span style="font-size:0.7rem;color:var(--muted)">{" · ".join(reasons[:3])}</span>')

    # Pitch mix detail
    arsenal_detail = style.get("arsenal_detail", "")
    if arsenal_detail:
        parts.append(f'<span style="font-size:0.7rem;color:var(--cyan)">🎯 {arsenal_detail}</span>')

    return " · ".join(parts) if parts else ""
