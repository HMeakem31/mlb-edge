"""
MLB Edge v2.4 — Convergence Score Engine
Combines ALL 7 signals. Quality-blended scoring prevents inflation from weak signals.
"""
from typing import Dict

def calculate_convergence_score(
    home_score: float, away_score: float,
    platoon_edge: dict, home_road_edge: dict,
    f5_edge: dict, bullpen: dict,
    weather: dict, park_factor: float
) -> dict:
    signals = []

    # 1. Base Model
    model_diff = home_score - away_score
    s = {'name': 'Base Model', 'weight': 0.25}
    if abs(model_diff) > 3:
        s.update({'direction': 'home' if model_diff > 0 else 'away',
                  'strength': min(100, abs(model_diff) * 2)})
    else:
        s.update({'direction': 'home' if model_diff > 0 else 'away',
                  'strength': max(10, abs(model_diff) * 2), 'note': 'Close matchup'})
    signals.append(s)

    # 2. Platoon
    pd = platoon_edge.get('home_platoon', 50) - platoon_edge.get('away_platoon', 50)
    s = {'name': 'Platoon', 'weight': 0.15}
    if abs(pd) > 5:
        s.update({'direction': 'home' if pd > 0 else 'away', 'strength': min(100, abs(pd) * 2)})
    else:
        s.update({'direction': 'home' if pd >= 0 else 'away', 'strength': max(10, abs(pd) * 2), 'note': 'Even platoon'})
    signals.append(s)

    # 3. Home/Road
    hr = home_road_edge.get('edge_score', 50)
    s = {'name': 'Home/Road', 'weight': 0.15}
    if abs(hr - 50) > 3:
        s.update({'direction': 'home' if hr > 50 else 'away', 'strength': min(100, abs(hr - 50) * 2)})
    else:
        s.update({'direction': 'home' if hr >= 50 else 'away', 'strength': max(10, abs(hr - 50) * 2), 'note': 'Neutral split'})
    signals.append(s)

    # 4. F5 Pitcher
    adv = f5_edge.get('advantage', 'even')
    fc = f5_edge.get('confidence', 'low')
    s = {'name': 'F5 Pitcher', 'weight': 0.20}
    sm = {'high': 85, 'medium': 65, 'low': 45}
    if adv not in ('even', 'unknown'):
        s.update({'direction': adv, 'strength': sm.get(fc, 50)})
    else:
        s.update({'direction': 'home', 'strength': 10, 'note': 'Even matchup'})
    signals.append(s)

    # 5. Streaks
    hs = (platoon_edge.get('home_streak', {}) or {}).get('score', 50)
    aws = (platoon_edge.get('away_streak', {}) or {}).get('score', 50)
    sd = hs - aws
    s = {'name': 'Streaks', 'weight': 0.10}
    if abs(sd) > 5:
        s.update({'direction': 'home' if sd > 0 else 'away', 'strength': min(100, abs(sd) * 1.5)})
    else:
        s.update({'direction': 'home' if sd >= 0 else 'away', 'strength': max(10, abs(sd) * 1.5), 'note': 'Similar momentum'})
    signals.append(s)

    # 6. Bullpen
    hb = bullpen.get('home_fatigue', 0)
    ab = bullpen.get('away_fatigue', 0)
    bd = ab - hb
    s = {'name': 'Bullpen', 'weight': 0.10}
    if abs(bd) > 5:
        s.update({'direction': 'home' if bd > 0 else 'away', 'strength': min(100, abs(bd) * 1.5)})
    else:
        s.update({'direction': 'home' if bd >= 0 else 'away', 'strength': max(10, abs(bd) * 1.5), 'note': 'Pens similar'})
    signals.append(s)

    # 7. Weather
    im = weather.get('impact', 'neutral')
    imap = {'blowing_out': 5, 'light_out': 3, 'blowing_in': -3, 'light_in': -2,
            'light_breeze': 1, 'crosswind': 0, 'neutral': 0}
    wv = imap.get(im, 0) if isinstance(im, str) else 0
    s = {'name': 'Weather', 'weight': 0.05}
    if abs(wv) > 1:
        s.update({'direction': 'home' if wv > 0 else 'away', 'strength': min(100, abs(wv) * 15)})
    else:
        s.update({'direction': 'home', 'strength': 10, 'note': 'Neutral'})
    signals.append(s)

    # ── Weighted convergence ──
    home_sigs = [s for s in signals if s['direction'] == 'home']
    away_sigs = [s for s in signals if s['direction'] == 'away']
    hw = sum(s['weight'] * s['strength'] / 100 for s in home_sigs)
    aw = sum(s['weight'] * s['strength'] / 100 for s in away_sigs)
    tw = hw + aw
    raw = (hw / tw * 100) if tw > 0 else 50

    # ── Quality factor (0-1): how many signals are actually strong? ──
    strong_n = sum(1 for s in signals if s['strength'] > 40)
    moderate_n = sum(1 for s in signals if 25 < s['strength'] <= 40)
    equiv = strong_n + moderate_n * 0.5
    quality = min(1.0, equiv / 5.0)

    # Blend: pull toward 50 when signal quality is low
    score = 50 + (raw - 50) * quality

    # ── Agreement across ALL signals ──
    agreeing = max(len(home_sigs), len(away_sigs))
    total = len(signals)
    ag_pct = agreeing / total

    # ── Confidence ──
    if ag_pct >= 0.75 and quality >= 0.8:
        confidence = 'strong'
    elif ag_pct >= 0.65 and quality >= 0.5:
        confidence = 'high'
    elif ag_pct >= 0.55 and quality >= 0.3:
        confidence = 'medium'
    else:
        confidence = 'low'

    favored = 'home' if hw > aw else ('away' if aw > hw else 'even')
    emoji_map = {'strong': '🔥', 'high': '🟢', 'medium': '🟡', 'low': '⚪'}
    emoji = emoji_map.get(confidence, '⚪')

    # ── Recommendation text ──
    nh = len(home_sigs)
    na = len(away_sigs)
    sn = int(round(equiv))
    if confidence in ('strong', 'high'):
        rec = f'{emoji} STRONG {favored.title()} ({nh}h/{na}a, {ag_pct:.0%} agree, Q={quality:.1f})'
    elif confidence == 'medium':
        rec = f'{emoji} LEAN {favored.title()} ({nh}h/{na}a, {ag_pct:.0%} agree, Q={quality:.1f})'
    else:
        rec = f'{emoji} PASS ({nh}h/{na}a agree, Q={quality:.1f} — weak signals)'

    return {
        'score': round(score, 1),
        'signal_count': total,
        'strong_signals': sn,
        'agreeing_signals': agreeing,
        'quality_factor': round(quality, 2),
        'agreement_pct': round(ag_pct * 100, 0),
        'confidence': confidence,
        'recommendation': rec,
        'favored_side': favored,
        'breakdown': signals,
        'home_weight': round(hw, 3),
        'away_weight': round(aw, 3),
    }
