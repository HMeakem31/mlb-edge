"""
MLB Edge v2.1 — Home/Road Splits + Streak Integration
Uses already-fetched standings data. Zero extra API calls.
"""

def parse_streak(streak_code: str) -> dict:
    """Parse streak code like 'W3', 'L2', 'N/A' into usable data."""
    if not streak_code or streak_code == 'N/A':
        return {'type': 'none', 'count': 0, 'score': 50.0}
    
    if streak_code.startswith('W'):
        count = int(streak_code[1:])
        return {
            'type': 'win',
            'count': count,
            'score': min(100, 50 + count * 10),
        }
    elif streak_code.startswith('L'):
        count = int(streak_code[1:])
        return {
            'type': 'loss',
            'count': count,
            'score': max(0, 50 - count * 10),
        }
    
    return {'type': 'none', 'count': 0, 'score': 50.0}

def calculate_home_road_edge(home_team_data: dict, away_team_data: dict) -> dict:
    """
    Calculate home/road performance edge.
    Returns edge score 0-100 (higher = home team advantage).
    """
    # Extract split records
    home_splits = home_team_data.get('splits', {})
    away_splits = away_team_data.get('splits', {})
    
    home_home = home_splits.get('home', {})
    away_away = away_splits.get('away', {})
    home_last10 = home_splits.get('lastTen', {})
    away_last10 = away_splits.get('lastTen', {})
    
    # Home team home win % vs league avg (~.500)
    home_home_pct = float(home_home.get('pct', '.500').replace('.', '')) / 1000
    home_home_games = home_home.get('wins', 0) + home_home.get('losses', 0)
    
    # Away team road win % vs league avg
    away_road_pct = float(away_away.get('pct', '.500').replace('.', '')) / 1000
    away_road_games = away_away.get('wins', 0) + away_away.get('losses', 0)
    
    # Recent form (last 10)
    home_l10_pct = float(home_last10.get('pct', '.500').replace('.', '')) / 1000
    away_l10_pct = float(away_last10.get('pct', '.500').replace('.', '')) / 1000
    
    # Calculate edge components (weighted by sample size)
    home_weight = min(1.0, home_home_games / 30)
    home_home_edge = (home_home_pct - 0.500) * 2 * home_weight
    
    away_weight = min(1.0, away_road_games / 30)
    away_road_edge = (away_road_pct - 0.500) * 2 * away_weight
    
    home_form = (home_l10_pct - 0.500) * 2
    away_form = (away_l10_pct - 0.500) * 2
    
    # Streak component
    home_streak = parse_streak(home_team_data.get('streak_code', 'N/A'))
    away_streak = parse_streak(away_team_data.get('streak_code', 'N/A'))
    home_streak_score = (home_streak['score'] - 50) / 50
    away_streak_score = (away_streak['score'] - 50) / 50
    
    # Combine into composite edge
    home_advantage = 0.54  # Base home field advantage
    
    composite = (
        (home_advantage + home_home_edge * 0.10 - away_road_edge * 0.10) * 0.40 +
        ((home_form - away_form) / 2 + 0.500) * 0.30 +
        ((home_streak_score - away_streak_score) / 2 + 0.500) * 0.30
    )
    
    edge_score = max(0, min(100, composite * 100))
    
    return {
        'home_win_pct': round(home_home_pct, 3),
        'away_win_pct': round(away_road_pct, 3),
        'home_l10_pct': round(home_l10_pct, 3),
        'away_l10_pct': round(away_l10_pct, 3),
        'home_streak': home_streak,
        'away_streak': away_streak,
        'edge_score': round(edge_score, 1),
        'edge_direction': 'home' if edge_score > 50 else 'away',
        'edge_strength': abs(edge_score - 50),
    }

def format_splits_summary(home_data: dict, away_data: dict) -> str:
    """Create human-readable home/road splits summary."""
    home_splits = home_data.get('splits', {})
    away_splits = away_data.get('splits', {})
    
    home_home = home_splits.get('home', {})
    away_away = away_splits.get('away', {})
    home_l10 = home_splits.get('lastTen', {})
    away_l10 = away_splits.get('lastTen', {})
    home_streak = home_data.get('streak_code', 'N/A')
    away_streak = away_data.get('streak_code', 'N/A')
    
    parts = []
    
    # Home team home record
    hh_w = home_home.get('wins', 0)
    hh_l = home_home.get('losses', 0)
    hh_pct = home_home.get('pct', '.000')
    parts.append(f"Home: {hh_w}-{hh_l} ({hh_pct})")
    
    # Away team road record
    aw_w = away_away.get('wins', 0)
    aw_l = away_away.get('losses', 0)
    aw_pct = away_away.get('pct', '.000')
    parts.append(f"Away: {aw_w}-{aw_l} ({aw_pct})")
    
    # Recent form
    hl10_w = home_l10.get('wins', 0)
    hl10_l = home_l10.get('losses', 0)
    al10_w = away_l10.get('wins', 0)
    al10_l = away_l10.get('losses', 0)
    parts.append(f"L10: {hl10_w}-{hl10_l} vs {al10_w}-{al10_l}")
    
    # Streaks
    parts.append(f"Streaks: {home_streak} | {away_streak}")
    
    return " | ".join(parts)
