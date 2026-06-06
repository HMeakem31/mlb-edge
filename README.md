"""
MLB Edge v2.4 — Prediction Logger + Accuracy Tracker
Logs every pick before first pitch. Scores automatically vs box scores.
Stores: data/predictions_log.json + data/accuracy.json
"""
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from config import DATA_DIR, MLB_API, REQUEST_TIMEOUT

PREDICTIONS_PATH = DATA_DIR / "predictions_log.json"
ACCURACY_PATH = DATA_DIR / "accuracy.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ─── LOGGING ────────────────────────────────────────────────────
def log_predictions(games: List[Dict], date_str: str = None):
    """
    Append predictions for every actionable market to predictions_log.json.
    Call this inside run.py after analysis is complete.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log = _load_json(PREDICTIONS_PATH)
    if date_str not in log:
        log[date_str] = []

    # Build a set of existing keys for deduplication (re-runs same day)
    existing_keys = {e.get("_key") for e in log.get(date_str, [])}

    for g in games:
        an = g.get("away_team", {}).get("name", "")
        hn = g.get("home_team", {}).get("name", "")
        grade = g.get("grade", {}).get("grade", "D")
        ev = g.get("ev_data", {})
        cv = g.get("convergence", {})
        lines = g.get("lines", {})
        nrfi = g.get("nrfi", {})
        totals = g.get("totals_edge", {})
        f5 = g.get("f5_edge", {})
        game_pk = g.get("game_pk")

        # Market 1: Moneyline (if grade B+ or better and EV positive)
        if grade in ("A+", "A", "B+") and ev.get("has_line") and ev.get("best_ev", 0) > 0:
            side = ev.get("best_side", "pass")
            if side in ("home", "away"):
                odds = ev.get("home_odds") if side == "home" else ev.get("away_odds")
                model_prob = ev.get("home_model_prob") if side == "home" else ev.get("away_model_prob")
                book_prob = ev.get("home_book_prob") if side == "home" else ev.get("away_book_prob")
                pick_name = hn if side == "home" else an
                key = f"{game_pk}_ML_{side}"
                if key not in existing_keys:
                    log[date_str].append({
                        "_key": key,
                        "game_pk": game_pk,
                        "date": date_str,
                        "away": an,
                        "home": hn,
                        "market": "moneyline",
                        "pick": pick_name,
                        "side": side,
                        "grade": grade,
                        "ev": round(ev.get("best_ev", 0), 2),
                        "odds": odds,
                        "model_prob": round(model_prob, 1),
                        "book_prob": round(book_prob, 1),
                        "kelly_suggested": g.get("kelly", {}).get("suggested_bet", 0),
                        "result": "pending",
                        "scored_at": None,
                    })

        # Market 2: NRFI/YRFI (high or medium confidence only)
        if nrfi.get("confidence") in ("high", "medium") and nrfi.get("recommendation") in ("NRFI", "YRFI"):
            key = f"{game_pk}_NRFI_{nrfi['recommendation']}"
            if key not in existing_keys:
                log[date_str].append({
                    "_key": key,
                    "game_pk": game_pk,
                    "date": date_str,
                    "away": an,
                    "home": hn,
                    "market": "nrfi",
                    "pick": nrfi["recommendation"],
                    "side": None,
                    "grade": None,
                    "ev": None,
                    "odds": None,
                    "model_prob": round(nrfi.get("nrfi_score", 50), 1),
                    "book_prob": None,
                    "kelly_suggested": None,
                    "result": "pending",
                    "scored_at": None,
                })

        # Market 3: Totals (high confidence only)
        if totals.get("confidence") == "high" and totals.get("recommendation") in ("OVER", "UNDER"):
            key = f"{game_pk}_TOTAL_{totals['recommendation']}"
            if key not in existing_keys:
                log[date_str].append({
                    "_key": key,
                    "game_pk": game_pk,
                    "date": date_str,
                    "away": an,
                    "home": hn,
                    "market": "total",
                    "pick": totals["recommendation"],
                    "side": None,
                    "grade": None,
                    "ev": round(totals.get("diff", 0), 1),
                    "odds": None,
                    "model_prob": round(totals.get("model_total", 0), 1),
                    "book_prob": round(totals.get("book_total", 0), 1),
                    "kelly_suggested": None,
                    "result": "pending",
                    "scored_at": None,
                })

        # Market 4: F5 Winner (only if high confidence and we have data)
        if f5 and f5.get("confidence") == "high" and f5.get("advantage") in ("home", "away"):
            side = f5["advantage"]
            pick_name = hn if side == "home" else an
            key = f"{game_pk}_F5_{side}"
            if key not in existing_keys:
                log[date_str].append({
                    "_key": key,
                    "game_pk": game_pk,
                    "date": date_str,
                    "away": an,
                    "home": hn,
                    "market": "f5_winner",
                    "pick": pick_name,
                    "side": side,
                    "grade": None,
                    "ev": None,
                    "odds": None,
                    "model_prob": None,
                    "book_prob": None,
                    "kelly_suggested": None,
                    "result": "pending",
                    "scored_at": None,
                })

    _save_json(PREDICTIONS_PATH, log)
    total_logged = len(log.get(date_str, []))
    print(f"  📝 Logged {total_logged} predictions for {date_str}")
    return total_logged


# ─── SCORING ────────────────────────────────────────────────────
def _fetch_boxscore(game_pk: int) -> Optional[dict]:
    """Fetch final score from MLB API."""
    try:
        r = requests.get(
            f"{MLB_API}/game/{game_pk}/boxscore",
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        info = data.get("info", [])
        # Final score is usually in info list or teams
        teams = data.get("teams", {})
        away = teams.get("away", {})
        home = teams.get("home", {})
        away_runs = away.get("teamStats", {}).get("batting", {}).get("runs", 0)
        home_runs = home.get("teamStats", {}).get("batting", {}).get("runs", 0)
        if away_runs is None or home_runs is None:
            # Fallback: try to parse from info
            for item in info:
                if item.get("label", "").lower() == "final":
                    val = item.get("value", "")
                    # e.g. "LAD 5, NYY 3"
                    parts = val.replace(",", "").split()
                    if len(parts) >= 4:
                        try:
                            away_runs = int(parts[1])
                            home_runs = int(parts[3])
                        except ValueError:
                            pass
        if away_runs is None or home_runs is None:
            return None
        return {
            "away_runs": int(away_runs),
            "home_runs": int(home_runs),
        }
    except Exception as e:
        print(f"    ⚠️ Boxscore error for {game_pk}: {e}")
        return None


def _fetch_f5_linescore(game_pk: int) -> Optional[dict]:
    """Fetch first 5 inning score from MLB linescore."""
    try:
        r = requests.get(
            f"{MLB_API}/game/{game_pk}/linescore",
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        innings = data.get("innings", [])
        away_f5 = 0
        home_f5 = 0
        for inn in innings[:5]:
            away_f5 += inn.get("away", {}).get("runs", 0) or 0
            home_f5 += inn.get("home", {}).get("runs", 0) or 0
        return {"away_runs": away_f5, "home_runs": home_f5}
    except Exception as e:
        print(f"    ⚠️ Linescore error for {game_pk}: {e}")
        return None


def _score_prediction(pred: dict, box: dict, f5_box: dict) -> str:
    """Determine win/loss/push for a single prediction."""
    market = pred.get("market")
    side = pred.get("side")
    pick = pred.get("pick")
    ar = box.get("away_runs", 0)
    hr = box.get("home_runs", 0)

    if market == "moneyline":
        if side == "home":
            return "win" if hr > ar else ("loss" if ar > hr else "push")
        elif side == "away":
            return "win" if ar > hr else ("loss" if hr > ar else "push")

    elif market == "nrfi":
        # NRFI = no runs in first inning
        # We don't have inning-by-inning from boxscore; we have f5_linescore
        if f5_box:
            f5_ar = f5_box.get("away_runs", 0)
            f5_hr = f5_box.get("home_runs", 0)
            # This is F5 total, not just 1st inning. We need a proxy.
            # Since we can't get 1st inning easily without play-by-play,
            # we use a heuristic: if f5_total == 0, definitely NRFI. If > 2, likely YRFI.
            # For strict scoring, we need 1st inning. Let's use linescore inning 1.
        # Better: fetch inning 1 specifically from play-by-play or linescore detail
        # Simplification: mark as "unscored" if we can't get inning 1
        return "pending"

    elif market == "total":
        total_runs = ar + hr
        book_total = pred.get("book_prob", 0)  # stored as book_total in odds field
        if book_total <= 0:
            return "pending"
        if pick == "OVER":
            return "win" if total_runs > book_total else ("loss" if total_runs < book_total else "push")
        elif pick == "UNDER":
            return "win" if total_runs < book_total else ("loss" if total_runs > book_total else "push")

    elif market == "f5_winner":
        if f5_box:
            f5_ar = f5_box.get("away_runs", 0)
            f5_hr = f5_box.get("home_runs", 0)
            if side == "home":
                return "win" if f5_hr > f5_ar else ("loss" if f5_ar > f5_hr else "push")
            elif side == "away":
                return "win" if f5_ar > f5_hr else ("loss" if f5_hr > f5_ar else "push")

    return "pending"


def _score_nrfi_from_linescore(game_pk: int) -> Optional[str]:
    """
    Fetch linescore and check if runs were scored in inning 1.
    Returns 'win', 'loss', or None if unavailable.
    """
    try:
        r = requests.get(
            f"{MLB_API}/game/{game_pk}/linescore",
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        innings = data.get("innings", [])
        if not innings:
            return None
        first = innings[0]
        ar = first.get("away", {}).get("runs", 0) or 0
        hr = first.get("home", {}).get("runs", 0) or 0
        if ar > 0 or hr > 0:
            return "loss"  # NRFI lost (YRFI happened)
        else:
            return "win"   # NRFI won (no runs in 1st)
    except Exception:
        return None


def score_date(date_str: str = None) -> dict:
    """
    Score all pending predictions for a given date.
    Default: yesterday. Returns summary dict.
    """
    if date_str is None:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    log = _load_json(PREDICTIONS_PATH)
    entries = log.get(date_str, [])
    if not entries:
        print(f"  ⚠️ No predictions found for {date_str}")
        return {}

    # Track which game_pks we need to fetch
    game_pks = list({e.get("game_pk") for e in entries if e.get("game_pk")})
    boxscores = {}
    f5_scores = {}
    nrfi_scores = {}

    print(f"\n[Score] Fetching {len(game_pks)} boxscores for {date_str}...")
    for pk in game_pks:
        box = _fetch_boxscore(pk)
        if box:
            boxscores[pk] = box
        f5 = _fetch_f5_linescore(pk)
        if f5:
            f5_scores[pk] = f5
        nrfi = _score_nrfi_from_linescore(pk)
        if nrfi:
            nrfi_scores[pk] = nrfi

    # Score each entry
    updated = 0
    for e in entries:
        if e.get("result") != "pending":
            continue
        pk = e.get("game_pk")
        market = e.get("market")
        if market == "nrfi" and pk in nrfi_scores:
            e["result"] = nrfi_scores[pk]
            e["scored_at"] = datetime.now().isoformat()
            updated += 1
        elif pk in boxscores:
            if market == "f5_winner" and pk in f5_scores:
                e["result"] = _score_prediction(e, boxscores[pk], f5_scores[pk])
                e["scored_at"] = datetime.now().isoformat()
                updated += 1
            elif market in ("moneyline", "total"):
                e["result"] = _score_prediction(e, boxscores[pk], f5_scores.get(pk))
                e["scored_at"] = datetime.now().isoformat()
                updated += 1

    # Save log
    _save_json(PREDICTIONS_PATH, log)

    # Build summary
    summary = _build_summary(log)
    _save_json(ACCURACY_PATH, summary)

    print(f"  ✅ Scored {updated} predictions for {date_str}")
    return summary


# ─── ACCURACY SUMMARY ───────────────────────────────────────────
def _build_summary(log: dict) -> dict:
    """Build rolling accuracy summary from full log."""
    markets = {}
    grade_stats = {}
    overall = {"wins": 0, "losses": 0, "pushes": 0, "total": 0}
    last_7 = {"wins": 0, "losses": 0, "pushes": 0, "total": 0}
    last_30 = {"wins": 0, "losses": 0, "pushes": 0, "total": 0}
    cutoff_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cutoff_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    for date_str, entries in log.items():
        for e in entries:
            res = e.get("result", "pending")
            if res == "pending":
                continue
            market = e.get("market", "unknown")
            grade = e.get("grade", "N/A")

            # Market buckets
            if market not in markets:
                markets[market] = {"wins": 0, "losses": 0, "pushes": 0, "total": 0}
            markets[market][res + "s"] += 1
            markets[market]["total"] += 1

            # Grade buckets (for moneyline)
            if grade and grade != "N/A":
                if grade not in grade_stats:
                    grade_stats[grade] = {"wins": 0, "losses": 0, "pushes": 0, "total": 0}
                grade_stats[grade][res + "s"] += 1
                grade_stats[grade]["total"] += 1

            # Overall
            overall[res + "s"] += 1
            overall["total"] += 1

            if date_str >= cutoff_7:
                last_7[res + "s"] += 1
                last_7["total"] += 1
            if date_str >= cutoff_30:
                last_30[res + "s"] += 1
                last_30["total"] += 1

    def _calc(bucket):
        t = bucket["total"]
        if t == 0:
            return {"win_pct": 0, "roi_approx": 0}
        w = bucket["wins"]
        l = bucket["losses"]
        p = bucket["pushes"]
        win_pct = w / (w + l) if (w + l) > 0 else 0
        # Approximate ROI assuming -110 juice on losses, +100 on wins (push = 0)
        roi = (w * 100 - l * 110) / ((w + l) * 100) if (w + l) > 0 else 0
        return {
            "win_pct": round(win_pct * 100, 1),
            "roi_approx": round(roi * 100, 1),
            "record": f"{w}-{l}-{p}",
            "total": t,
        }

    return {
        "last_updated": datetime.now().isoformat(),
        "overall": _calc(overall),
        "last_7_days": _calc(last_7),
        "last_30_days": _calc(last_30),
        "by_market": {k: _calc(v) for k, v in markets.items()},
        "by_grade": {k: _calc(v) for k, v in grade_stats.items()},
    }


def get_accuracy_header() -> str:
    """Return a short accuracy string for the report header."""
    acc = _load_json(ACCURACY_PATH)
    if not acc:
        return ""
    o = acc.get("overall", {})
    l7 = acc.get("last_7_days", {})
    if o.get("total", 0) == 0:
        return ""
    parts = [f"📊 All-time: {o['record']} ({o['win_pct']}% W, {o['roi_approx']}% ROI)"]
    if l7.get("total", 0) > 0:
        parts.append(f"L7D: {l7['record']} ({l7['win_pct']}%)")
    return " · ".join(parts)


def get_accuracy_dict() -> dict:
    """Return full accuracy dict for reporter integration."""
    return _load_json(ACCURACY_PATH)
