"""
MLB Edge v2.1 — First 5 Innings (F5) Analysis
Derives F5 metrics from existing pitcher stats. Zero extra API calls.
"""
from typing import Dict, Optional

def estimate_f5_metrics(pitcher_stats: Dict) -> Optional[Dict]:
    """
    Estimate F5 performance from season stats.
    Uses: ERA, WHIP, K/9, HR/9, innings per start proxy.
    """
    if not pitcher_stats:
        return None
    
    era = float(pitcher_stats.get("era", 4.00) or 4.00)
    whip = float(pitcher_stats.get("whip", 1.30) or 1.30)
    k9 = float(pitcher_stats.get("k9", 8.0) or 8.0)
    hr9 = float(pitcher_stats.get("hr9", 1.0) or 1.0)
    gs = pitcher_stats.get("games_started", 0)
    ip = float(pitcher_stats.get("innings_pitched", 0) or 0)
    
    if ip == 0:  # Allow relievers with 0 GS (spot starts)
        return None
    
    ip_per_start = ip / max(1, gs)
    
    # F5 adjustment: F5 ERA typically lower than full-game ERA
    # Pitchers who go deeper tend to have less fatigue impact
    fatigue_factor = max(0, min(0.5, (ip_per_start - 5.0) * 0.1))
    f5_era = max(2.00, era - fatigue_factor)
    f5_whip = max(0.80, whip - fatigue_factor * 0.1)
    f5_k9 = k9 + fatigue_factor * 0.5
    f5_hr9 = hr9 * (1 - fatigue_factor * 0.05)
    
    # F5 quality score (0-100)
    era_score = max(0, min(100, (6.00 - f5_era) / 4.00 * 100))
    whip_score = max(0, min(100, (1.50 - f5_whip) / 0.70 * 100))
    k9_score = max(0, min(100, (f5_k9 - 5.0) / 7.0 * 100))
    hr9_score = max(0, min(100, (2.0 - f5_hr9) / 1.5 * 100))
    
    f5_quality = (era_score * 0.40 + whip_score * 0.25 + k9_score * 0.20 + hr9_score * 0.15)
    
    return {
        "f5_era": round(f5_era, 2),
        "f5_whip": round(f5_whip, 2),
        "f5_k9": round(f5_k9, 2),
        "f5_hr9": round(f5_hr9, 2),
        "ip_per_start": round(ip_per_start, 2),
        "f5_quality": round(f5_quality, 1),
        "go_deep_score": round(min(100, ip_per_start / 7.0 * 100), 1),
    }

def calculate_f5_edge(away_f5: Dict, home_f5: Dict) -> Dict:
    """
    Calculate F5 advantage between two starting pitchers.
    Lower ERA = better, Higher quality = better.
    """
    if not away_f5 or not home_f5:
        return {
            "away_f5_era": None, "home_f5_era": None,
            "f5_era_diff": 0, "f5_quality_diff": 0,
            "advantage": "unknown", "confidence": "low",
            "f5_total_estimate": 4.5,
        }
    
    away_era = away_f5.get("f5_era", 4.00)
    home_era = home_f5.get("f5_era", 4.00)
    era_diff = home_era - away_era  # negative = home pitcher better
    
    away_quality = away_f5.get("f5_quality", 50)
    home_quality = home_f5.get("f5_quality", 50)
    quality_diff = home_quality - away_quality  # positive = home pitcher better
    
    # Determine advantage (calibrated: was too loose, tightened thresholds)
    if abs(era_diff) < 0.75 and abs(quality_diff) < 15:
        advantage = "even"
        confidence = "low"
    elif era_diff < -0.40 or quality_diff > 15:
        advantage = "home"
        confidence = "high" if (era_diff < -1.00 or quality_diff > 25) else "medium"
    else:
        advantage = "away"
        confidence = "high" if (era_diff > 1.00 or quality_diff < -25) else "medium"
    
    # F5 total estimate
    avg_f5_era = (away_era + home_era) / 2
    avg_f5_quality = (away_quality + home_quality) / 2
    f5_total = 4.2 + (avg_f5_era - 4.00) * 0.5 + (50 - avg_f5_quality) / 100 * 0.5
    f5_total = max(2.5, min(6.5, f5_total))
    
    return {
        "away_f5_era": round(away_era, 2),
        "home_f5_era": round(home_era, 2),
        "f5_era_diff": round(era_diff, 2),
        "away_f5_quality": round(away_quality, 1),
        "home_f5_quality": round(home_quality, 1),
        "f5_quality_diff": round(quality_diff, 1),
        "advantage": advantage,
        "confidence": confidence,
        "f5_total_estimate": round(f5_total, 1),
        "away_go_deep": away_f5.get("go_deep_score", 0),
        "home_go_deep": home_f5.get("go_deep_score", 0),
    }

def generate_f5_recommendations(f5_edge: Dict, game_context: Dict) -> list:
    """Generate F5 betting recommendations."""
    recommendations = []
    advantage = f5_edge.get("advantage", "unknown")
    confidence = f5_edge.get("confidence", "low")
    era_diff = f5_edge.get("f5_era_diff", 0)
    quality_diff = f5_edge.get("f5_quality_diff", 0)
    
    if advantage == "unknown":
        return recommendations
    
    # F5 moneyline
    if abs(era_diff) > 0.75 or abs(quality_diff) > 15:
        side = advantage
        team_name = game_context.get(f"{side}_team_name", side.title())
        f5_era = f5_edge.get(f"{side}_f5_era", 0)
        f5_quality = f5_edge.get(f"{side}_f5_quality", 0)
        recommendations.append({
            "type": "f5_moneyline",
            "side": side,
            "recommendation": f"F5: {team_name} ML (SP F5 ERA: {f5_era}, Quality: {f5_quality:.0f})",
            "confidence": confidence,
            "reason": f"F5 ERA advantage ({abs(era_diff):.2f}) and quality edge ({abs(quality_diff):.0f})",
        })
    
    # F5 totals
    f5_total = f5_edge.get("f5_total_estimate")
    if f5_total:
        if f5_total < 3.5:
            recommendations.append({
                "type": "f5_under",
                "recommendation": f"F5 Under {f5_total + 0.5:.1f} (est: {f5_total})",
                "confidence": "high" if f5_total < 3.0 else "medium",
                "reason": "Both starters project well in F5",
            })
        elif f5_total > 5.0:
            recommendations.append({
                "type": "f5_over",
                "recommendation": f"F5 Over {f5_total - 0.5:.1f} (est: {f5_total})",
                "confidence": "high" if f5_total > 5.5 else "medium",
                "reason": "Both starters project poorly in F5",
            })
    
    return recommendations
