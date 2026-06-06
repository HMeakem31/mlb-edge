"""
MLB Edge v2.2 — Edge Calculator
EV, grades, Kelly, NRFI, FIP, totals, SGP, narrative — ZERO API calls.
"""
from typing import Dict, Optional, List

# ─── EV CALCULATION ──────────────────────────────────────────────
def american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability (0-1)."""
    if odds is None:
        return 0.5
    if odds > 0:
        return 100.0 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal odds."""
    if odds is None:
        return 2.0
    if odds > 0:
        return (odds / 100) + 1
    else:
        return (100 / abs(odds)) + 1

def devig_moneyline(home_odds: int, away_odds: int) -> tuple:
    """Remove vig to get true implied probabilities."""
    home_imp = american_to_implied(home_odds)
    away_imp = american_to_implied(away_odds)
    total = home_imp + away_imp  # > 1.0 due to vig
    if total == 0:
        return 0.5, 0.5
    return home_imp / total, away_imp / total

def calculate_ev(
    convergence: dict, home_odds: int, away_odds: int,
    home_name: str, away_name: str
) -> dict:
    """
    Calculate expected value by comparing model probability vs book implied.
    Uses convergence score to derive model win probability.
    """
    if home_odds is None or away_odds is None:
        return {
            "has_line": False, "home_ev": 0, "away_ev": 0,
            "home_edge": 0, "away_edge": 0,
            "best_side": "none", "best_ev": 0, "best_edge": 0,
            "home_model_prob": 50, "away_model_prob": 50,
            "home_book_prob": 50, "away_book_prob": 50,
        }

    # Devig the book line
    home_book, away_book = devig_moneyline(home_odds, away_odds)

    # Model probability from convergence
    conv_score = convergence.get("score", 50)
    quality = convergence.get("quality_factor", 0.3)
    confidence = convergence.get("confidence", "low")
    favored = convergence.get("favored_side", "none")

    # Model weight: capped by signal QUALITY and CONFIDENCE, not just signal count
    # Low quality / low confidence = lean heavily on market (book odds)
    # High quality / high confidence = trust our model more
    confidence_weights = {
        'strong': 0.65,
        'high': 0.50,
        'medium': 0.35,
        'low': 0.15,
    }
    model_weight = confidence_weights.get(confidence, 0.15)
    # Further scale by quality factor
    model_weight = min(0.65, model_weight * quality)

    home_model = (conv_score / 100) * model_weight + home_book * (1 - model_weight)
    away_model = 1 - home_model

    # Edge = model prob - book prob
    home_edge = (home_model - home_book) * 100
    away_edge = (away_model - away_book) * 100

    # EV per $100 bet
    home_decimal = american_to_decimal(home_odds)
    away_decimal = american_to_decimal(away_odds)
    home_ev = (home_model * (home_decimal - 1) - (1 - home_model)) * 100
    away_ev = (away_model * (away_decimal - 1) - (1 - away_model)) * 100

    # Best side
    if home_ev > away_ev and home_ev > 0:
        best_side = "home"
        best_ev = home_ev
        best_edge = home_edge
    elif away_ev > home_ev and away_ev > 0:
        best_side = "away"
        best_ev = away_ev
        best_edge = away_edge
    else:
        best_side = "pass"
        best_ev = max(home_ev, away_ev)
        best_edge = 0

    return {
        "has_line": True,
        "home_ev": round(home_ev, 2),
        "away_ev": round(away_ev, 2),
        "home_edge": round(home_edge, 1),
        "away_edge": round(away_edge, 1),
        "best_side": best_side,
        "best_ev": round(best_ev, 2),
        "best_edge": round(max(home_edge, away_edge) if best_side != "pass" else 0, 1),
        "home_model_prob": round(home_model * 100, 1),
        "away_model_prob": round(away_model * 100, 1),
        "home_book_prob": round(home_book * 100, 1),
        "away_book_prob": round(away_book * 100, 1),
        "home_odds": home_odds,
        "away_odds": away_odds,
    }


# ─── LETTER GRADES ──────────────────────────────────────────────
def calculate_grade(convergence: dict, ev_data: dict) -> dict:
    """
    Map convergence + EV into a letter grade (A+ to D).
    Monster.bet uses A+ to C. We use A+ to D with PASS.
    """
    confidence = convergence.get("confidence", "low")
    agreement = convergence.get("agreement_pct", 0)
    signals = convergence.get("signal_count", 0)
    best_ev = ev_data.get("best_ev", 0) if ev_data.get("has_line") else 0
    best_edge = ev_data.get("best_edge", 0)

    # Score components
    # Confidence: strong=40, high=30, medium=20, low=5
    conf_pts = {"strong": 40, "high": 30, "medium": 20, "low": 5}.get(confidence, 5)

    # Agreement: 0-100 scaled to 0-25
    agree_pts = min(25, agreement / 4)

    # Signal count: more signals = more reliable, max 15
    sig_pts = min(15, signals * 2.5)

    # EV: positive EV = good, max 20
    ev_pts = min(20, max(0, best_ev * 2)) if best_ev > 0 else 0

    total = conf_pts + agree_pts + sig_pts + ev_pts  # max ~100

    # Calibrated thresholds v2.4 (tightened: A+ raised 85→88, A 72→75, B+ 58→61, B 44→47, C+ 32→35, C 20→23)
    if total >= 88:
        grade, grade_text = "A+", "Elite"
    elif total >= 75:
        grade, grade_text = "A", "Strong"
    elif total >= 61:
        grade, grade_text = "B+", "Good"
    elif total >= 47:
        grade, grade_text = "B", "Decent"
    elif total >= 35:
        grade, grade_text = "C+", "Marginal"
    elif total >= 23:
        grade, grade_text = "C", "Weak"
    else:
        grade, grade_text = "D", "Pass"

    return {
        "grade": grade,
        "grade_text": grade_text,
        "grade_score": round(total, 1),
        "components": {
            "confidence": round(conf_pts, 1),
            "agreement": round(agree_pts, 1),
            "signals": round(sig_pts, 1),
            "ev": round(ev_pts, 1),
        }
    }


# ─── KELLY CRITERION ────────────────────────────────────────────
def kelly_sizing(ev_data: dict, bankroll: float = 1000.0) -> dict:
    """
    Calculate bet size using fractional Kelly criterion.
    Uses quarter-Kelly for conservative sizing.
    """
    if not ev_data.get("has_line") or ev_data.get("best_side") == "pass":
        return {"kelly_pct": 0, "quarter_kelly": 0, "suggested_bet": 0,
                "bankroll": bankroll, "side": "pass"}

    side = ev_data["best_side"]
    if side == "home":
        prob = ev_data["home_model_prob"] / 100
        odds = ev_data["home_odds"]
    else:
        prob = ev_data["away_model_prob"] / 100
        odds = ev_data["away_odds"]

    decimal = american_to_decimal(odds)
    b = decimal - 1  # net odds (profit per $1)
    q = 1 - prob

    if b <= 0:
        return {"kelly_pct": 0, "quarter_kelly": 0, "suggested_bet": 0,
                "bankroll": bankroll, "side": side}

    # Kelly: f* = (bp - q) / b
    kelly = (b * prob - q) / b
    kelly = max(0, kelly)  # never negative

    # Quarter-Kelly (conservative)
    qk = kelly / 4
    suggested = round(bankroll * qk, 2)

    # Cap at 5% of bankroll no matter what
    suggested = min(suggested, bankroll * 0.05)

    return {
        "kelly_pct": round(kelly * 100, 2),
        "quarter_kelly": round(qk * 100, 2),
        "suggested_bet": round(suggested, 2),
        "bankroll": bankroll,
        "side": side,
    }


# ─── NRFI SCORE ─────────────────────────────────────────────────
def calculate_nrfi(
    away_pitcher: dict, home_pitcher: dict,
    away_trends: dict, home_trends: dict,
    park_factor: float
) -> dict:
    """
    Calculate No Run First Inning probability.
    Uses pitcher WHIP, K/9, and team scoring trends.
    Zero extra API calls — pure math on existing data.
    """
    # Pitcher 1st-inning proxy: lower WHIP + higher K/9 = harder to score
    def pitcher_nrfi_score(stats):
        if not stats:
            return 50.0  # neutral
        era = float(stats.get("era", 4.00) or 4.00)
        whip = float(stats.get("whip", 1.30) or 1.30)
        k9 = float(stats.get("k9", 8.0) or 8.0)
        bb9 = float(stats.get("bb9", 3.0) or 3.0)

        # WHIP component (lower = better for NRFI)
        whip_score = max(0, min(100, (1.60 - whip) / 0.80 * 100))
        # K/9 component (higher = better for NRFI)
        k9_score = max(0, min(100, (k9 - 4.0) / 8.0 * 100))
        # BB/9 component (lower = better — walks lead to runs)
        bb9_score = max(0, min(100, (5.0 - bb9) / 4.0 * 100))
        # ERA component
        era_score = max(0, min(100, (6.00 - era) / 4.00 * 100))

        return era_score * 0.30 + whip_score * 0.30 + k9_score * 0.25 + bb9_score * 0.15

    away_p_score = pitcher_nrfi_score(away_pitcher)
    home_p_score = pitcher_nrfi_score(home_pitcher)

    # Team offensive tendencies (higher RPG = worse for NRFI)
    away_rpg = away_trends.get("runs_per_game", 4.5)
    home_rpg = home_trends.get("runs_per_game", 4.5)

    # Teams that score a lot are more likely to score in 1st inning
    # Scale: 3.0 RPG = +15 NRFI bonus, 6.0 RPG = -15 NRFI penalty
    away_off_adj = max(-15, min(15, (4.5 - away_rpg) * 5))
    home_off_adj = max(-15, min(15, (4.5 - home_rpg) * 5))

    # Park factor adjustment (higher PF = worse for NRFI)
    park_adj = max(-10, min(10, (1.0 - park_factor) * 50))

    # Combined NRFI score (0-100, higher = more likely NRFI)
    # Away pitcher keeps home team scoreless + home pitcher keeps away team scoreless
    raw_score = (
        (away_p_score + home_off_adj) * 0.45 +  # away SP vs home lineup
        (home_p_score + away_off_adj) * 0.45 +  # home SP vs away lineup
        (50 + park_adj) * 0.10                    # park
    )
    nrfi_score = max(0, min(100, raw_score))

    # Recommendation
    if nrfi_score >= 72:
        rec = "NRFI"
        confidence = "high"
    elif nrfi_score >= 60:
        rec = "NRFI"
        confidence = "medium"
    elif nrfi_score <= 30:
        rec = "YRFI"
        confidence = "high"
    elif nrfi_score <= 42:
        rec = "YRFI"
        confidence = "medium"
    else:
        rec = "SKIP"
        confidence = "low"

    return {
        "nrfi_score": round(nrfi_score, 1),
        "away_pitcher_score": round(away_p_score, 1),
        "home_pitcher_score": round(home_p_score, 1),
        "recommendation": rec,
        "confidence": confidence,
        "park_adjustment": round(park_adj, 1),
    }


# ─── FIP REGRESSION FLAGS ───────────────────────────────────────
_FIP_CONSTANT = 3.15  # league-average constant, ~3.10-3.20 historically

def calculate_fip(pitcher_stats: dict) -> Optional[dict]:
    """
    Calculate FIP from per-9 rates + IP we already have.
    FIP = ((13*HR + 3*BB - 2*K) / IP) + constant
    Derived from HR/9, BB/9, K/9 — zero extra data needed.
    """
    if not pitcher_stats:
        return None
    era = float(pitcher_stats.get("era", 0) or 0)
    hr9 = float(pitcher_stats.get("hr9", 1.0) or 1.0)
    bb9 = float(pitcher_stats.get("bb9", 3.0) or 3.0)
    k9 = float(pitcher_stats.get("k9", 8.0) or 8.0)
    ip = float(pitcher_stats.get("innings_pitched", 0) or 0)
    if ip < 5:
        return None
    # Derive raw counts from per-9 rates
    hr = hr9 * ip / 9
    bb = bb9 * ip / 9
    k = k9 * ip / 9
    fip = ((13 * hr + 3 * bb - 2 * k) / ip) + _FIP_CONSTANT
    fip = max(1.50, min(8.00, fip))
    gap = era - fip  # positive = ERA higher than FIP (unlucky), negative = lucky
    # Flag
    if gap < -0.50:
        flag = "⚠️ LUCKY"
        flag_detail = f"ERA {era:.2f} is {abs(gap):.2f} below FIP — regression risk UP"
    elif gap > 0.50:
        flag = "🍀 UNLUCKY"
        flag_detail = f"ERA {era:.2f} is {gap:.2f} above FIP — regression risk DOWN"
    else:
        flag = ""
        flag_detail = "ERA and FIP aligned — no regression signal"
    return {
        "fip": round(fip, 2),
        "era": round(era, 2),
        "era_fip_gap": round(gap, 2),
        "flag": flag,
        "flag_detail": flag_detail,
    }


# ─── TOTALS EDGE ────────────────────────────────────────────────
def calculate_totals_edge(
    f5_edge: dict, park_factor: float, weather: dict,
    home_bullpen: dict, away_bullpen: dict,
    book_total: float, umpire: dict = None
) -> dict:
    """
    Full-game total estimate from F5 + bullpen + park + weather + umpire.
    Compare to book total for over/under edge.
    """
    f5_total = f5_edge.get("f5_total_estimate", 4.5) if f5_edge else 4.5
    # F5 is ~48% of scoring (calibrated from backtest: was 54%, undershot by 1.5R)
    full_raw = f5_total / 0.48 + 0.5
    # Bullpen fatigue adjustment: tired bullpens = more runs
    home_bull = home_bullpen.get("fatigue_score", 0) if home_bullpen else 0
    away_bull = away_bullpen.get("fatigue_score", 0) if away_bullpen else 0
    bull_adj = (home_bull + away_bull) / 200  # 0-1 scale, avg fatigue
    full_raw += bull_adj * 1.0  # max +1 run from exhausted bullpens
    # Park factor
    full_raw *= park_factor
    # Weather: use physics-based run adjustment if available
    weather_adj = 0
    if weather and isinstance(weather, dict):
        weather_adj = weather.get("weather_run_adj", 0)
        if weather_adj == 0:
            # fallback for old-format weather
            impact = weather.get("wind_impact", "neutral")
            w_map = {"blowing_out": 0.5, "light_out": 0.2, "crosswind": 0,
                     "neutral": 0, "light_in": -0.2, "blowing_in": -0.4}
            weather_adj = w_map.get(impact, 0)
    full_raw += weather_adj
    # Umpire run impact
    ump_adj = 0
    if umpire and isinstance(umpire, dict):
        ump_adj = umpire.get("run_impact", 0)
    full_raw += ump_adj * 0.5  # dampen — umpire effect is real but noisy
    model_total = max(4.0, min(14.0, round(full_raw, 1)))
    # Edge vs book
    if book_total and book_total > 0:
        diff = model_total - book_total
        if diff > 0.7:
            rec = "OVER"
            conf = "high" if diff > 1.2 else "medium"
        elif diff < -0.7:
            rec = "UNDER"
            conf = "high" if diff < -1.2 else "medium"
        else:
            rec = "NO EDGE"
            conf = "low"
    else:
        diff = 0
        rec = "N/A"
        conf = "low"
    return {
        "model_total": model_total,
        "book_total": book_total or 0,
        "diff": round(diff, 1),
        "recommendation": rec,
        "confidence": conf,
    }


# ─── SGP CORRELATION SUGGESTIONS ────────────────────────────────
def build_sgp_suggestions(
    convergence: dict, f5_edge: dict, nrfi: dict,
    totals_edge: dict, grade: dict,
    away_name: str, home_name: str
) -> List[dict]:
    """Build correlated same-game parlay suggestions from existing signals."""
    sgps = []
    if grade.get("grade", "D") in ("D", "C"):
        return sgps  # not enough conviction
    favored = convergence.get("favored_side", "none")
    if favored == "none":
        return sgps
    fav_name = home_name if favored == "home" else away_name
    conf = convergence.get("confidence", "low")
    # Strong side + totals + NRFI correlation
    nrfi_rec = nrfi.get("recommendation", "SKIP")
    totals_rec = totals_edge.get("recommendation", "N/A")
    f5_adv = f5_edge.get("advantage", "even") if f5_edge else "even"
    # SGP 1: ML + Totals (if aligned)
    if totals_rec in ("OVER", "UNDER") and conf in ("strong", "high"):
        sgps.append({
            "legs": [f"{fav_name} ML", f"Total {totals_rec} {totals_edge.get('book_total', '?')}"],
            "correlation": "positive" if (favored != "even") else "neutral",
            "note": f"Strong side ({fav_name}) + totals lean {totals_rec}",
            "confidence": conf,
        })
    # SGP 2: ML + NRFI (dominant pitching correlation)
    if nrfi_rec == "NRFI" and f5_adv == favored and conf in ("strong", "high", "medium"):
        sgps.append({
            "legs": [f"{fav_name} ML", "NRFI"],
            "correlation": "positive",
            "note": f"Favored side's pitcher dominates early + NRFI",
            "confidence": "medium" if conf == "medium" else "high",
        })
    # SGP 3: F5 ML + NRFI (strong pitcher game)
    if nrfi_rec == "NRFI" and totals_rec == "UNDER":
        sgps.append({
            "legs": [f"{fav_name} F5 ML", "NRFI", f"Under {totals_edge.get('book_total', '?')}"],
            "correlation": "strong",
            "note": "Pitcher duel — all legs benefit from low scoring",
            "confidence": "high" if nrfi.get("confidence") == "high" else "medium",
        })
    # SGP 4: YRFI + Over (if offense-heavy game)
    if nrfi_rec == "YRFI" and totals_rec == "OVER":
        sgps.append({
            "legs": ["YRFI", f"Over {totals_edge.get('book_total', '?')}"],
            "correlation": "strong",
            "note": "High-scoring game expected from first pitch",
            "confidence": "high" if nrfi.get("confidence") == "high" else "medium",
        })
    return sgps[:3]  # cap at 3


# ─── AUTO-NARRATIVE ─────────────────────────────────────────────
def generate_narrative(
    game: dict, away_name: str, home_name: str
) -> str:
    """
    Generate a 2-4 sentence human-readable explanation of the pick.
    No AI, no LLM — pure template logic from existing data.
    """
    convergence = game.get("convergence", {})
    grade = game.get("grade", {})
    ev_data = game.get("ev_data", {})
    f5_edge = game.get("f5_edge", {})
    nrfi = game.get("nrfi", {})
    kelly = game.get("kelly", {})
    away_fip = game.get("away_fip", {})
    home_fip = game.get("home_fip", {})
    totals = game.get("totals_edge", {})
    away = game.get("away_team", {})
    home = game.get("home_team", {})
    analysis = game.get("analysis", {})

    g = grade.get("grade", "D")
    favored = convergence.get("favored_side", "none")
    fav_name = home_name if favored == "home" else (away_name if favored == "away" else "Neither side")
    signals = convergence.get("signal_count", 0)
    agreeing = convergence.get("agreeing_signals", 0)
    conf = convergence.get("confidence", "low")

    parts = []

    # Sentence 1: Core pick
    if g in ("A+", "A"):
        parts.append(f"{g} STRONG {fav_name}.")
    elif g in ("B+", "B"):
        parts.append(f"{g} LEAN {fav_name}.")
    else:
        parts.append(f"{g} — low conviction, consider passing.")

    # Sentence 2: Why — pitching matchup + F5
    if f5_edge and f5_edge.get("advantage") != "even":
        f5_side = home_name if f5_edge["advantage"] == "home" else away_name
        away_era = f5_edge.get("away_f5_era", "?")
        home_era = f5_edge.get("home_f5_era", "?")
        qual_diff = abs(f5_edge.get("f5_quality_diff", 0))
        parts.append(f"F5 pitching edge to {f5_side} (ERA {away_era} vs {home_era}, {qual_diff:.0f}-pt quality gap).")

    # Sentence 2b: xERA/FIP regression flag if present
    for side_name, fip_data in [(away_name, away_fip), (home_name, home_fip)]:
        if fip_data and fip_data.get("flag"):
            detail = fip_data.get("detail", fip_data.get("flag_detail", ""))
            parts.append(f"{side_name} SP: {fip_data['flag']} — {detail}.")
            break  # only mention the most impactful one

    # Sentence 3: Convergence + EV
    if ev_data.get("has_line") and ev_data.get("best_ev", 0) > 0:
        parts.append(f"{agreeing}/{signals} signals converge ({conf}). +{ev_data['best_ev']:.1f}% EV on {fav_name}.")
    elif signals > 0:
        parts.append(f"{agreeing}/{signals} signals converge ({conf}).")

    # Sentence 4: Action items (Kelly + NRFI + totals + props)
    actions = []
    if kelly.get("suggested_bet", 0) > 0:
        actions.append(f"Kelly: ${kelly['suggested_bet']:.0f}")
    if nrfi.get("recommendation") != "SKIP":
        actions.append(f"{nrfi['recommendation']} ({nrfi.get('confidence', '?')})")
    if totals.get("recommendation") not in ("NO EDGE", "N/A", None):
        actions.append(f"Total {totals['recommendation']} {totals.get('book_total', '?')}")

    # K props
    props = game.get("props", {})
    kp = props.get("k_props", {})
    for kd in [kp.get("home_pitcher"), kp.get("away_pitcher")]:
        if kd and kd.get("confidence") in ("high", "medium") and kd.get("recommendation") != "NO EDGE":
            actions.append(f"{kd['pitcher'][:10]} {kd['recommendation']} {kd['likely_line']:.0f}K")
            break

    # Hot hitters
    hp = props.get("hit_props", {})
    for hitters in [hp.get("home_hitters", []), hp.get("away_hitters", [])]:
        if hitters and hitters[0].get("confidence") == "high":
            h = hitters[0]
            actions.append(f"{h['name'].split(',')[0] if ',' in h['name'] else h['name'].split()[-1]} hits OVER")
            break

    if actions:
        parts.append(" | ".join(actions) + ".")

    return " ".join(parts)
