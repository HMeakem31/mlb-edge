"""
MLB Edge v2.3 — HTML Report Generator
Professional daily report: F5 + Convergence + EV + Grade + Kelly + NRFI + FIP + SGP
"""
from datetime import datetime
from typing import Dict, List
from config import OUTPUT_DIR


def generate_report(games: List[Dict], extras: Dict = None, accuracy: Dict = None) -> str:
    date_str = datetime.now().strftime('%A, %B %d, %Y')
    time_str = datetime.now().strftime('%I:%M %p')
    # Accuracy banner string
    acc_html = ""
    if accuracy:
        o = accuracy.get("overall", {})
        l7 = accuracy.get("last_7_days", {})
        if o.get("total", 0) > 0:
            acc_parts = [f"📊 All-time: {o['record']} ({o['win_pct']}% W, {o['roi_approx']}% ROI)"]
            if l7.get("total", 0) > 0:
                acc_parts.append(f"L7D: {l7['record']} ({l7['win_pct']}%)")
            acc_html = f'<div style="text-align:center;font-size:0.75rem;color:var(--muted);margin-top:0.4rem">{" · ".join(acc_parts)}</div>'
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MLB Edge — {datetime.now().strftime('%b %d, %Y')}</title>
<style>
:root{{--bg:#0b1120;--card:#141c2f;--card2:#1a2540;--border:#1e2d4a;--border2:#2a3f6a;--text:#e8ecf4;--muted:#7a8ba8;--accent:#3b9eff;--green:#34d399;--yellow:#fbbf24;--orange:#fb923c;--red:#ef4444;--purple:#a78bfa;--cyan:#22d3ee;--surface:rgba(255,255,255,0.03)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.55;min-height:100vh}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.25rem}}

/* ── HEADER ── */
.hdr{{text-align:center;padding:2rem 1rem 1.5rem;margin-bottom:1.5rem;position:relative}}
.hdr::after{{content:'';position:absolute;bottom:0;left:10%;right:10%;height:1px;background:linear-gradient(90deg,transparent,var(--accent),transparent)}}
.hdr h1{{font-size:1.6rem;font-weight:700;color:var(--text);letter-spacing:-0.5px}}
.hdr h1 span{{color:var(--accent)}}
.hdr .sub{{color:var(--muted);font-size:0.82rem;margin-top:0.3rem}}
.hdr .tags{{display:flex;gap:0.4rem;justify-content:center;flex-wrap:wrap;margin-top:0.6rem}}
.hdr .tag{{font-size:0.65rem;padding:0.15rem 0.5rem;border-radius:3px;background:rgba(59,158,255,0.08);color:var(--accent);border:1px solid rgba(59,158,255,0.15)}}

/* ── GAME CARD ── */
.gc{{background:var(--card);border:1px solid var(--border);border-radius:10px;margin-bottom:1.75rem;overflow:hidden}}
.gc-top{{display:flex;align-items:center;justify-content:space-between;padding:0.9rem 1.25rem;background:linear-gradient(135deg,#12203a 0%,#0d1525 100%);border-bottom:1px solid var(--border);flex-wrap:wrap;gap:0.5rem}}
.gc-matchup{{display:flex;align-items:center;gap:0.65rem}}
.gc-matchup h2{{font-size:1.15rem;font-weight:600;letter-spacing:-0.3px}}
.gc-meta{{color:var(--muted);font-size:0.78rem;text-align:right}}

/* Grade */
.grd{{width:38px;height:38px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;font-weight:800;flex-shrink:0}}
.grd-ap{{background:rgba(52,211,153,0.15);color:var(--green);border:2px solid var(--green)}}
.grd-a{{background:rgba(52,211,153,0.10);color:var(--green);border:2px solid rgba(52,211,153,0.6)}}
.grd-bp{{background:rgba(251,191,36,0.12);color:var(--yellow);border:2px solid rgba(251,191,36,0.5)}}
.grd-b{{background:rgba(251,191,36,0.08);color:var(--yellow);border:2px solid rgba(251,191,36,0.35)}}
.grd-cp{{background:rgba(251,146,60,0.12);color:var(--orange);border:2px solid rgba(251,146,60,0.4)}}
.grd-c{{background:rgba(251,146,60,0.08);color:var(--orange);border:2px solid rgba(251,146,60,0.3)}}
.grd-d{{background:rgba(122,139,168,0.08);color:var(--muted);border:2px solid rgba(122,139,168,0.3)}}

/* Context */
.ctx{{padding:0.5rem 1.25rem;background:rgba(59,158,255,0.02);font-size:0.75rem;color:var(--muted);display:flex;flex-wrap:wrap;gap:0.4rem 1rem;border-bottom:1px solid var(--border)}}
.ctx b{{color:var(--text);font-weight:500}}

/* Teams grid */
.tms{{display:grid;grid-template-columns:1fr 1fr;gap:0;border-bottom:1px solid var(--border)}}
.tm{{padding:1rem 1.25rem;position:relative}}
.tm:first-child{{border-right:1px solid var(--border)}}
.tm-name{{font-size:0.95rem;font-weight:600;margin-bottom:0.15rem}}
.tm-sub{{font-size:0.72rem;color:var(--muted);margin-bottom:0.5rem}}
.tm-sp{{font-size:0.75rem;color:var(--muted);margin-bottom:0.6rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border)}}
.tm-sp b{{color:var(--text);font-weight:500}}
.row{{display:flex;justify-content:space-between;align-items:center;padding:0.2rem 0;font-size:0.78rem}}
.row .l{{color:var(--muted)}}
.row .v{{font-weight:600}}
.pbar{{height:4px;border-radius:2px;background:var(--border);margin-top:2px;margin-bottom:4px;overflow:hidden}}
.pbar div{{height:100%;border-radius:2px}}
.bg{{background:var(--green)}}.bo{{background:var(--orange)}}.br{{background:var(--red)}}.bc{{background:var(--cyan)}}.bp{{background:var(--purple)}}
.tm-score{{margin-top:0.6rem;padding-top:0.5rem;border-top:1px solid var(--border);text-align:center}}
.tm-score .n{{font-size:1.5rem;font-weight:800;color:var(--accent)}}
.tm-score .lb{{font-size:0.62rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px}}

/* Sections */
.sec{{padding:0.9rem 1.25rem;border-top:1px solid var(--border)}}
.sec-t{{font-size:0.72rem;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:0.6px;margin-bottom:0.5rem}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.4rem}}
.cd{{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:0.6rem}}
.cd-t{{font-size:0.72rem;font-weight:600;color:var(--accent);margin-bottom:0.35rem}}
.st{{font-size:1.15rem;font-weight:700;color:var(--accent)}}
.st-s{{font-size:0.92rem;font-weight:700}}
.st-l{{font-size:0.62rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.3px}}

/* Badges */
.bdg{{display:inline-block;padding:0.15rem 0.5rem;border-radius:99px;font-size:0.68rem;font-weight:600;vertical-align:middle}}
.bdg-g{{background:rgba(52,211,153,0.12);color:var(--green);border:1px solid rgba(52,211,153,0.3)}}
.bdg-y{{background:rgba(251,191,36,0.10);color:var(--yellow);border:1px solid rgba(251,191,36,0.25)}}
.bdg-m{{background:rgba(122,139,168,0.10);color:var(--muted);border:1px solid rgba(122,139,168,0.2)}}
.bdg-r{{background:rgba(239,68,68,0.10);color:var(--red);border:1px solid rgba(239,68,68,0.25)}}
.ev-p{{color:var(--green)}}.ev-n{{color:var(--red)}}

/* Convergence */
.conv{{border:2px solid;border-radius:10px;padding:1rem;text-align:center}}
.conv-s{{border-color:var(--green);background:rgba(52,211,153,0.04)}}
.conv-h{{border-color:rgba(52,211,153,0.6);background:rgba(52,211,153,0.03)}}
.conv-m{{border-color:rgba(251,191,36,0.5);background:rgba(251,191,36,0.03)}}
.conv-l{{border-color:var(--border2);background:var(--surface)}}
.conv .num{{font-size:1.8rem;font-weight:800}}
.conv .lbl{{font-size:0.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:0.1rem}}

/* Signal rows */
.sig{{display:flex;align-items:center;gap:0.4rem;padding:0.25rem 0;font-size:0.75rem;border-bottom:1px solid rgba(255,255,255,0.03)}}
.sig:last-child{{border:none}}
.sig .dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.sig .nm{{flex:1;color:var(--muted)}}
.sig .dr{{font-weight:600;min-width:35px;text-align:right}}
.sig .sr{{min-width:25px;text-align:right;font-size:0.68rem;color:var(--muted)}}

/* F5 pill */
.pill{{display:inline-flex;align-items:center;padding:0.12rem 0.45rem;border-radius:5px;font-size:0.7rem;font-weight:600}}
.pill-h{{background:rgba(34,211,238,0.12);color:var(--cyan)}}
.pill-a{{background:rgba(251,146,60,0.12);color:var(--orange)}}
.pill-e{{background:rgba(122,139,168,0.1);color:var(--muted)}}

/* Banner */
.ban{{padding:1.1rem 1.25rem;text-align:center;background:linear-gradient(180deg,rgba(59,158,255,0.05),rgba(59,158,255,0.01));border-top:2px solid var(--border2);margin-bottom:0.5rem}}
.ban-rec{{font-size:1.08rem;font-weight:700;letter-spacing:-0.3px}}
.ban-nar{{font-size:0.78rem;color:var(--text);opacity:0.8;margin-top:0.5rem;max-width:650px;margin-left:auto;margin-right:auto;line-height:1.6;padding:0.5rem 0.8rem;background:rgba(255,255,255,0.02);border-radius:6px;border:1px solid var(--border)}}

/* Collapsible */
details{{border:none;outline:none}}
details>summary{{cursor:pointer;list-style:none;-webkit-user-select:none;user-select:none}}
details>summary::-webkit-details-marker{{display:none}}
details>summary::before{{content:'▸ ';color:var(--accent);font-size:0.8rem;margin-right:0.2rem}}
details[open]>summary::before{{content:'▾ '}}
.gc>details>summary{{padding:0.9rem 1.25rem;background:linear-gradient(135deg,#12203a 0%,#0d1525 100%);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem}}
.gc>details>summary:hover{{background:linear-gradient(135deg,#162848 0%,#0f1a2d 100%)}}
.sub-details>summary{{font-size:0.72rem;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:0.6px;padding:0.5rem 0;margin-bottom:0.3rem}}
.line-move{{font-size:0.68rem;padding:0.1rem 0.35rem;border-radius:3px}}
.line-move-up{{background:rgba(239,68,68,0.1);color:var(--red)}}
.line-move-down{{background:rgba(52,211,153,0.1);color:var(--green)}}
.line-move-flat{{color:var(--muted)}}

/* Footer */
.ftr{{text-align:center;padding:1.5rem 0 2rem;color:var(--muted);font-size:0.68rem}}
.ftr a{{color:var(--accent);text-decoration:none}}

/* Responsive */
@media(max-width:700px){{
  .tms,.g2{{grid-template-columns:1fr}}
  .tm:first-child{{border-right:none;border-bottom:1px solid var(--border)}}
  .g3{{grid-template-columns:1fr 1fr}}
  .gc-top{{flex-direction:column;align-items:flex-start}}
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>⚾ MLB <span>Edge</span></h1>
    <div class="sub">{date_str} — {len(games)} Game{'s' if len(games)!=1 else ''} Analyzed</div>
    {acc_html}
    <div class="tags">
      <span class="tag">F5</span><span class="tag">Convergence</span><span class="tag">EV</span>
      <span class="tag">NRFI</span><span class="tag">FIP</span><span class="tag">Kelly</span>
      <span class="tag">Weather Physics</span><span class="tag">Umpire</span><span class="tag">SGP</span>
    </div>
  </div>
"""
    # How to Read key
    html += _legend()

    # Best Bets Summary
    html += _best_bets(games)

    # Regression Radar + Market Divergence (league-wide)
    if extras:
        html += _regression_radar(extras.get("regression_radar", {}))
        html += _market_divergence(extras.get("market_divergences", []))

    for game in games:
        html += _card(game)
    html += f"""
  <div class="ftr">
    <div style="font-size:0.82rem;font-weight:600;color:var(--accent);margin-bottom:0.4rem">⚾ MLB Edge v2.4 — 30 Analytical Signals Per Game</div>
    <p>Report generated {time_str} · {len(games)} game{'s' if len(games)!=1 else ''} analyzed</p>
    <p style="margin-top:0.15rem">Data: MLB Stats API · Baseball Savant · ESPN · Open-Meteo · RefMetrics</p>
    <p style="margin-top:0.15rem">Statcast: xERA/xwOBA cached 12h · Weather: real-time · Lines: DraftKings via ESPN</p>
    <p style="margin-top:0.4rem;font-size:0.62rem;opacity:0.7">⚠️ For entertainment and educational purposes only. Gamble responsibly. Past performance does not guarantee future results.</p>
  </div>
</div>
</body>
</html>
"""
    return html


# ─── HOW TO READ THIS REPORT ─────────────────────────────────────
def _legend():
    return """
  <div class="gc">
    <details class="sub-details">
      <summary style="padding:0.7rem 1.25rem;font-size:0.8rem;font-weight:700;color:var(--accent)">📖 How to Read This Report — Click to Expand</summary>
      <div style="padding:0.6rem 1.25rem;font-size:0.75rem;line-height:1.7">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem">
          <div>
            <div style="font-weight:700;color:var(--accent);margin-bottom:0.3rem">🎨 Color Scale (0-100)</div>
            <div><span style="color:var(--green)">■ Green (70+)</span> — Elite / strong advantage</div>
            <div><span style="color:var(--yellow)">■ Yellow (50-69)</span> — Average / slight edge</div>
            <div><span style="color:var(--orange)">■ Orange (30-49)</span> — Below average / concern</div>
            <div><span style="color:var(--red)">■ Red (0-29)</span> — Poor / major weakness</div>
            <div style="margin-top:0.4rem;font-weight:700;color:var(--accent);margin-bottom:0.3rem">📊 Team Box Metrics</div>
            <div><b>Offense</b> — Higher = better offense. 70+ is elite</div>
            <div><b>Pitch Vuln</b> — Higher = MORE vulnerable. Low is good for that team's pitcher</div>
            <div><b>Bullpen</b> — Higher = MORE tired. Low (green) = fresh pen. High (red) = exhausted</div>
            <div><b>Platoon</b> — Higher = better lineup vs opposing pitcher handedness</div>
            <div><b>F5 Quality</b> — Higher = better starter through 5 innings</div>
            <div><b>Composite</b> — Weighted combination of all factors</div>
          </div>
          <div>
            <div style="font-weight:700;color:var(--accent);margin-bottom:0.3rem">🏆 Grades</div>
            <div><span class="grd grd-ap" style="width:20px;height:20px;font-size:0.6rem;display:inline-flex">A+</span> Elite pick — highest conviction</div>
            <div><span class="grd grd-a" style="width:20px;height:20px;font-size:0.6rem;display:inline-flex">A</span> Strong pick — clear edge</div>
            <div><span class="grd grd-bp" style="width:20px;height:20px;font-size:0.6rem;display:inline-flex">B+</span> Good pick — moderate edge</div>
            <div><span class="grd grd-b" style="width:20px;height:20px;font-size:0.6rem;display:inline-flex">B</span> Decent — lean but not strong</div>
            <div><span class="grd grd-cp" style="width:20px;height:20px;font-size:0.6rem;display:inline-flex">C+</span> Marginal — proceed with caution</div>
            <div><span class="grd grd-d" style="width:20px;height:20px;font-size:0.6rem;display:inline-flex">D</span> Pass — no edge found</div>
            <div style="margin-top:0.4rem;font-weight:700;color:var(--accent);margin-bottom:0.3rem">📈 Key Terms</div>
            <div><b>EV</b> — Expected Value. Positive = profitable long-term</div>
            <div><b>xERA</b> — Expected ERA from Statcast contact quality (more accurate than ERA)</div>
            <div><b>FIP</b> — Fielding Independent Pitching (pitcher skill without defense)</div>
            <div><b>NRFI/YRFI</b> — No Run / Yes Run First Inning</div>
            <div><b>Kelly</b> — Optimal bet size based on your edge</div>
            <div><b>SGP</b> — Same Game Parlay with correlated legs</div>
          </div>
        </div>
      </div>
    </details>
  </div>
"""


# ─── BEST BETS SUMMARY ───────────────────────────────────────────
def _best_bets(games):
    """Top picks across all markets — the first thing you see."""
    bets = []
    for g in games:
        an = g.get("away_team",{}).get("name","?")
        hn = g.get("home_team",{}).get("name","?")
        gr = g.get("grade",{}).get("grade","D")
        cv = g.get("convergence",{})
        ev = g.get("ev_data",{})
        nr = g.get("nrfi",{})
        te = g.get("totals_edge",{})
        props = g.get("props",{})

        fav = cv.get("favored_side","none")
        fn = hn if fav=="home" else (an if fav=="away" else None)

        # ML pick (A/A+ only)
        if gr in ("A+","A") and fn:
            ev_str = f"+{ev['best_ev']:.1f}% EV" if ev.get("has_line") and ev.get("best_ev",0)>0 else ""
            bets.append(("🏆",f"{fn} ML",gr,cv.get("confidence",""),ev_str,f"{an[:8]}@{hn[:8]}"))

        # NRFI/YRFI (high confidence only)
        if nr.get("confidence")=="high" and nr.get("recommendation") in ("NRFI","YRFI"):
            bets.append(("🏏",nr["recommendation"],"",nr["confidence"],f"Score: {nr.get('nrfi_score',0):.0f}",f"{an[:8]}@{hn[:8]}"))

        # Totals (high confidence)
        if te.get("confidence") in ("high",) and te.get("recommendation") in ("OVER","UNDER"):
            bets.append(("📊",f'{te["recommendation"]} {te.get("book_total","")}',""  ,te["confidence"],f"Model: {te.get('model_total','')}",f"{an[:8]}@{hn[:8]}"))

        # K Props (high confidence)
        kp = props.get("k_props",{})
        for kd in [kp.get("home_pitcher"),kp.get("away_pitcher")]:
            if kd and kd.get("confidence")=="high" and kd.get("recommendation") in ("OVER","UNDER"):
                bets.append(("⚡",f'{kd["pitcher"][:12]} {kd["recommendation"]} {kd["likely_line"]:.1f}K',"",kd["confidence"],f"Proj: {kd['proj_k']:.1f}",f"{an[:8]}@{hn[:8]}"))

    if not bets:
        return ""

    rows = ""
    for emoji,pick,grade,conf,detail,matchup in bets:
        gc = _bdg(conf) if conf else "bdg-m"
        grade_str = f' <span class="grd grd-{grade.lower().replace("+","p")}" style="width:24px;height:24px;font-size:0.7rem">{grade}</span>' if grade else ""
        rows += f'<div style="display:flex;align-items:center;gap:0.5rem;padding:0.35rem 0;border-bottom:1px solid rgba(255,255,255,0.03);font-size:0.82rem"><span>{emoji}</span>{grade_str}<span style="font-weight:600;flex:1">{pick}</span><span class="bdg {gc}">{conf.upper() if conf else ""}</span><span style="color:var(--muted);font-size:0.75rem">{detail}</span><span style="color:var(--muted);font-size:0.72rem">{matchup}</span></div>'

    return f"""
  <div class="gc" style="border-color:var(--accent)">
    <div style="padding:0.8rem 1.25rem;background:linear-gradient(135deg,rgba(59,158,255,0.08),rgba(59,158,255,0.02));border-bottom:1px solid var(--border)">
      <div style="font-size:0.85rem;font-weight:700;color:var(--accent)">🎯 TODAY'S BEST BETS</div>
      <div style="font-size:0.7rem;color:var(--muted)">Highest-conviction picks across all markets</div>
    </div>
    <div style="padding:0.6rem 1.25rem">{rows}</div>
  </div>
"""


# ─── REGRESSION RADAR ────────────────────────────────────────────
def _regression_radar(radar):
    if not radar:
        return ""
    sections = ""
    # Unlucky batters (back these — due for improvement)
    ub = radar.get("unlucky_batters", [])
    if ub:
        rows = "".join(f'<span style="display:inline-block;margin:0.15rem;padding:0.15rem 0.5rem;border-radius:4px;background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);font-size:0.72rem"><b>{b["name"]}</b> wOBA {b["woba"]:.3f} → xwOBA {b["xwoba"]:.3f} <span style="color:var(--green)">+{abs(b["gap"]):.3f}</span></span>' for b in ub[:5])
        sections += f'<div style="margin-bottom:0.4rem"><span style="font-size:0.7rem;font-weight:600;color:var(--green)">🍀 Unlucky Batters (back — due UP)</span><div style="margin-top:0.2rem">{rows}</div></div>'
    # Lucky pitchers (fade — ERA will rise)
    lp = radar.get("lucky_pitchers", [])
    if lp:
        rows = "".join(f'<span style="display:inline-block;margin:0.15rem;padding:0.15rem 0.5rem;border-radius:4px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);font-size:0.72rem"><b>{p["name"]}</b> ERA {p["era"]:.2f} → xERA {p["xera"]:.2f} <span style="color:var(--red)">⚠️ +{p["gap"]:.2f}</span></span>' for p in lp[:5])
        sections += f'<div style="margin-bottom:0.4rem"><span style="font-size:0.7rem;font-weight:600;color:var(--red)">⚠️ Lucky Pitchers (fade — ERA will rise)</span><div style="margin-top:0.2rem">{rows}</div></div>'
    if not sections:
        return ""
    return f"""
  <div class="gc">
    <details class="sub-details"><summary style="padding:0.7rem 1.25rem;font-size:0.8rem;font-weight:700;color:var(--accent)">📡 Regression Radar — League-Wide Statcast Divergences</summary>
    <div style="padding:0.5rem 1.25rem">{sections}</div>
    </details>
  </div>
"""

# ─── MARKET DIVERGENCE ───────────────────────────────────────────
def _market_divergence(divs):
    if not divs:
        return ""
    rows = ""
    for d in divs[:5]:
        gc = {"A+":"grd-ap","A":"grd-a","B+":"grd-bp","B":"grd-b"}.get(d.get("grade",""),"grd-d")
        rows += f'<div style="display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0;border-bottom:1px solid rgba(255,255,255,0.03);font-size:0.78rem"><span class="grd {gc}" style="width:24px;height:24px;font-size:0.65rem">{d.get("grade","?")}</span><span style="flex:1">{d["matchup"]}</span><span style="font-weight:600;color:var(--green)">{d["side"]}</span><span style="color:var(--green)">+{d["edge"]:.1f}% edge</span><span style="color:var(--muted)">Model {d["model_prob"]:.0f}% vs Book {d["book_prob"]:.0f}%</span></div>'
    return f"""
  <div class="gc">
    <details class="sub-details"><summary style="padding:0.7rem 1.25rem;font-size:0.8rem;font-weight:700;color:var(--accent)">📊 Biggest Model vs Market Divergences</summary>
    <div style="padding:0.5rem 1.25rem">{rows}</div>
    </details>
  </div>
"""


# ─── helpers ─────────────────────────────────────────────────────
def _c(val, inv=False):
    v = (100-val) if inv else val
    if v>=70: return "var(--green)"
    if v>=50: return "var(--yellow)"
    if v>=30: return "var(--orange)"
    return "var(--red)"

def _bc(val, inv=False):
    v = (100-val) if inv else val
    if v>=60: return "bg"
    if v>=35: return "bo"
    return "br"

def _bdg(conf):
    return {"strong":"bdg-g","high":"bdg-g","medium":"bdg-y","low":"bdg-m"}.get(conf,"bdg-m")

def _fo(o):
    if o is None: return "N/A"
    return f"+{o}" if o>0 else str(o)


# ─── GAME CARD ───────────────────────────────────────────────────
def _card(g: Dict) -> str:
    a = g.get("away_team",{})
    h = g.get("home_team",{})
    ctx = g.get("context",{})
    an = g.get("analysis",{})
    ln = g.get("lines",{})
    f5 = g.get("f5_edge",{})
    cv = g.get("convergence",{})
    ev = g.get("ev_data",{})
    gr = g.get("grade",{})
    ky = g.get("kelly",{})
    nr = g.get("nrfi",{})
    te = g.get("totals_edge",{})
    an_ = a.get("name","Away"); hn_ = h.get("name","Home")
    w = ctx.get("weather",{}); u = ctx.get("umpire",{})

    grd = gr.get("grade","?")
    gc = {"A+":"grd-ap","A":"grd-a","B+":"grd-bp","B":"grd-b","C+":"grd-cp","C":"grd-c","D":"grd-d"}.get(grd,"grd-d")

    # Context line
    from datetime import datetime as _dt
    _now = _dt.now().strftime("%I:%M %p")
    cx_parts = [f"🌤️ {w.get('summary','N/A')}",
                f"🏟️ PF {ctx.get('park_factor',1.0)}",
                f"🧑‍⚖️ {u.get('summary','TBD')}",
                f"🕐 Updated {_now}"]
    # Enhanced context
    cx2 = []
    if ctx.get("splits_summary"):
        cx2.append(ctx["splits_summary"])
    # Weather physics
    wra = w.get("run_adj",0); wout = w.get("out_component",0); wcf = w.get("carry_ft",0)
    if not w.get("is_dome") and (abs(wra)>0.15 or abs(wout)>2):
        wp = []
        if abs(wout)>2:
            d = "OUT" if wout>0 else "IN"
            wp.append(f"🌬️ {d} {abs(wout):.0f}mph")
        if abs(wcf)>2:
            wp.append(f"✈️ {'+' if wcf>0 else ''}{wcf:.0f}ft")
        if abs(wra)>0.15:
            wp.append(f"<b style='color:{_c(50+wra*30)}'>{'+' if wra>0 else ''}{wra:.1f}R</b>")
        cx2.append(" · ".join(wp))
    # Ump detail
    uri = u.get("run_impact",0)
    if u.get("in_database") and abs(uri)>0.2:
        cx2.append(f"⚖️ Ump: <b style='color:{_c(50-uri*20)}'>{'+' if uri>0 else ''}{uri:.1f}R</b> · O:{u.get('over_pct',0.5):.0%}")

    # Summary line for collapsed view
    rec_short = an.get("recommendation", "")
    ev_snip = ""
    if ev.get("has_line") and ev.get("best_ev", 0) > 0:
        ev_snip = f' <span style="color:var(--green);font-size:0.78rem">+EV {ev["best_ev"]:.1f}%</span>'
    game_time_short = ctx.get('game_time', 'TBD')
    venue_short = ctx.get('venue', '')
    # Shorten venue for collapsed view
    venue_short = venue_short.replace(" Park", "").replace(" Stadium", "").replace(" Field", "")

    o = f"""
  <div class="gc">
    <details>
      <summary>
        <div style="display:flex;align-items:center;gap:0.6rem">
          <div class="grd {gc}" style="width:32px;height:32px;font-size:0.8rem">{grd}</div>
          <h2 style="font-size:1.05rem">{an_} @ {hn_}</h2>
        </div>
        <div style="display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap">
          <span style="font-size:0.82rem;font-weight:500">{rec_short}{ev_snip}</span>
          <span style="color:var(--border2)">│</span>
          <span class="gc-meta">{game_time_short} · {venue_short}</span>
        </div>
      </summary>
    <div class="ctx">{' · '.join(cx_parts)}</div>
"""
    if cx2:
        o += f'    <div class="ctx">{" &nbsp;│&nbsp; ".join(cx2)}</div>\n'

    # Teams
    inj = g.get("injury_flags", {})
    o += f'    <div class="tms">{_tm(a,an.get("away_analysis",{}),"away",inj.get("away"))}{_tm(h,an.get("home_analysis",{}),"home",inj.get("home"))}</div>\n'

    # Lines + Totals (always visible)
    o += _lines(ln, te, g)
    # Banner (always visible)
    o += _banner(g, an_, hn_, gc, grd)
    # Expandable sections
    o += _detail_sec("📊 First 5 Innings", _f5(f5, an_, hn_))
    o += _detail_sec("🎯 Convergence Score", _conv(cv, an_, hn_))
    o += _detail_sec("⚾ Pitching + FIP", _fip_sec(g, an_, hn_))
    o += _detail_sec("🧮 Edge Analysis — EV · Kelly · NRFI", _edge(ev, ky, nr, an_, hn_))
    sgp_content = _sgp(g.get("sgp",[]))
    if sgp_content:
        o += _detail_sec("🎰 SGP Correlated Legs", sgp_content)
    # Advanced matchup
    # Props
    props_content = _props(g)
    if props_content:
        o += _detail_sec("🎯 Player Props — K Props · Hit Props", props_content)
    # Situational intelligence
    sit_content = _situational(g)
    if sit_content:
        o += _detail_sec("🧠 Situational Intel — Travel · Script · Fade · Stacks", sit_content)
    # Advanced matchup
    extras_content = _extras(g)
    if extras_content:
        o += _detail_sec("🔬 Advanced Matchup — RISP · Defense · Speed · Shadows", extras_content)

    o += "    </details>\n  </div>\n"
    return o


# ─── METRIC EXPLANATIONS ─────────────────────────────────────────
def _metric_explain(val, metric_type):
    """Short inline explanation based on the value — click ▸ on metric label to see."""
    explanations = {
        "offense": {
            "high": "Elite offense — expect run production",
            "mid": "Average offense — capable but not dominant",
            "low": "Weak offense — struggles to generate runs",
        },
        "pitching_vuln": {
            "high": "Opposing pitcher is very hittable — favorable for this lineup",
            "mid": "Opposing pitcher is average — no clear edge",
            "low": "Opposing pitcher is dominant — tough matchup for batters",
        },
        "bullpen": {
            "high": "⚠️ Bullpen exhausted from recent heavy usage — expect late-inning runs",
            "mid": "Bullpen moderately used — some arms may be unavailable",
            "low": "Bullpen fresh — full arsenal available for late innings",
        },
    }
    if metric_type not in explanations:
        return ""
    if metric_type == "bullpen":
        if val >= 50: tier = "high"
        elif val >= 25: tier = "mid"
        else: tier = "low"
    elif metric_type == "pitching_vuln":
        if val >= 60: tier = "high"
        elif val >= 35: tier = "mid"
        else: tier = "low"
    else:
        if val >= 65: tier = "high"
        elif val >= 40: tier = "mid"
        else: tier = "low"
    text = explanations[metric_type][tier]
    return f'<div style="font-size:0.65rem;color:var(--muted);margin-bottom:0.2rem;font-style:italic">{text}</div>'


# ─── TEAM BOX ────────────────────────────────────────────────────
def _tm(t, an, side, injury_flags=None):
    nm = t.get("name","")
    rec = t.get("record",""); st = t.get("streak",""); l10 = t.get("l10","")
    loc = t.get("home_record","") if side=="home" else t.get("road_record","")
    ll = "Home" if side=="home" else "Road"
    p = t.get("pitcher","TBD"); ph = t.get("pitcher_hand","?")
    pe = t.get("pitcher_era","N/A"); pk = t.get("pitcher_k9","N/A")
    rpg = t.get("rpg",0); rapg = t.get("rapg",0)

    os_ = an.get("offense_score",50); pv = an.get("pitching_vulnerability",50)
    bf = an.get("bullpen_fatigue",0); pl = t.get("platoon_edge",50)
    tr = an.get("trend","neutral"); ts = an.get("total_score",50)
    ti = {"hot":"🔥","warm":"♨️","neutral":"⚖️","cold":"❄️","ice_cold":"🧊"}.get(tr,"⚖️")

    f5e = t.get("f5_era","N/A"); f5q = t.get("f5_quality","N/A")
    f5h = ""
    if f5q not in ("N/A",None):
        fq = float(f5q)
        f5h = f"""<div class="row"><span class="l">F5</span><span class="v" style="color:{_c(fq)}">{f5e} ERA · {fq:.0f}Q</span></div>
      <div class="pbar"><div class="{_bc(fq)}" style="width:{fq}%"></div></div>"""

    # Injury flag badges
    injury_html = ""
    if injury_flags:
        if injury_flags.get("on_il"):
            injury_html = f'<span style="font-size:0.65rem;color:var(--red);font-weight:600;margin-left:0.3rem">🚑 {injury_flags["il_desc"][:40]}</span>'
        elif injury_flags.get("is_questionable"):
            injury_html = f'<span style="font-size:0.65rem;color:var(--orange);font-weight:600;margin-left:0.3rem">⚠️ {injury_flags["questionable_note"][:40]}</span>'
        elif injury_flags.get("first_start_back"):
            injury_html = f'<span style="font-size:0.65rem;color:var(--yellow);font-weight:600;margin-left:0.3rem">🔄 First start back from IL</span>'

    return f"""
      <div class="tm">
        <div class="tm-name">{nm}</div>
        <div class="tm-sub">{rec} · {ll}: {loc} · L10: {l10} · {st}</div>
        <div class="tm-sp"><b>{p}</b> ({ph}) · ERA {pe} · K/9 {pk} · <span style="font-size:0.7rem">{rpg}R/G · {rapg}RA/G</span>{injury_html}</div>
        <div class="row"><span class="l" title="Team offensive strength (0-100). Higher = more dangerous lineup">Offense ▸</span><span class="v" style="color:{_c(os_)}">{os_:.0f}</span></div>
        <div class="pbar"><div class="{_bc(os_)}" style="width:{os_}%"></div></div>
        {_metric_explain(os_, "offense")}
        <div class="row"><span class="l" title="How hittable is the opposing pitcher (0-100). Higher = easier to score against. LOW is good for this team's pitcher">Pitch Vuln ▸</span><span class="v" style="color:{_c(pv,True)}">{pv:.0f}</span></div>
        <div class="pbar"><div class="{_bc(pv,True)}" style="width:{pv}%"></div></div>
        {_metric_explain(pv, "pitching_vuln")}
        <div class="row"><span class="l" title="Bullpen tiredness (0-100). LOW = fresh (good). HIGH = exhausted (bad — expect more runs late)">Bullpen ▸</span><span class="v" style="color:{_c(bf,True)}">{bf:.0f}</span></div>
        <div class="pbar"><div class="br" style="width:{bf}%"></div></div>
        {_metric_explain(bf, "bullpen")}
        <div class="row"><span class="l" title="Lineup advantage vs opposing pitcher handedness (0-100). Higher = more batters with platoon edge">Platoon ▸</span><span class="v" style="color:{_c(pl)}">{pl:.0f}</span></div>
        <div class="pbar"><div class="bp" style="width:{pl}%"></div></div>
        {f5h}
        <div class="row"><span class="l">Trend</span><span class="v">{ti} {tr.title()}</span></div>
        <div class="tm-score"><div class="n">{ts:.0f}</div><div class="lb">Composite</div></div>
      </div>"""


# ─── COLLAPSIBLE SECTION WRAPPER ─────────────────────────────────
def _detail_sec(title: str, content: str) -> str:
    if not content:
        return ""
    return f"""
    <div class="sec">
      <details class="sub-details"><summary>{title}</summary>
      {content}
      </details>
    </div>"""


# ─── F5 ──────────────────────────────────────────────────────────
def _f5(f5, an, hn):
    if not f5: return ""
    adv = f5.get("advantage","even")
    pc = {"home":"pill-h","away":"pill-a"}.get(adv,"pill-e")
    at = hn if adv=="home" else (an if adv=="away" else "Even")
    cb = _bdg(f5.get("confidence","low"))
    def fe(v): return f"{v:.2f}" if isinstance(v,(int,float)) else str(v)
    def fq(v): return f"{v:.0f}" if isinstance(v,(int,float)) else str(v)
    ae = f5.get("away_f5_era","?"); he = f5.get("home_f5_era","?")
    aq = f5.get("away_f5_quality",50); hq = f5.get("home_f5_quality",50)
    ag = f5.get("away_go_deep",0); hg = f5.get("home_go_deep",0)
    return f"""
      <div class="g2">
        <div class="cd"><div style="font-weight:600;font-size:0.78rem;margin-bottom:0.3rem">{an} <span style="color:var(--muted);font-weight:400">(Away SP)</span></div>
          <div class="g3"><div><div class="st-s" style="color:var(--cyan)">{fe(ae)}</div><div class="st-l">F5 ERA</div></div><div><div class="st-s" style="color:{_c(float(aq) if isinstance(aq,(int,float)) else 50)}">{fq(aq)}</div><div class="st-l" title="Composite 0-100 score: ERA + WHIP + K/9 + HR/9 weighted. 70+ = elite, 50 = average, 30- = poor">Quality ⓘ</div></div><div><div class="st-s" style="color:var(--muted)">{fq(ag)}</div><div class="st-l" title="How likely this SP pitches 6+ innings. Based on IP per start / 7.0. 70+ = workhorse, 40- = early pull risk">Go Deep ⓘ</div></div></div>
        </div>
        <div class="cd"><div style="font-weight:600;font-size:0.78rem;margin-bottom:0.3rem">{hn} <span style="color:var(--muted);font-weight:400">(Home SP)</span></div>
          <div class="g3"><div><div class="st-s" style="color:var(--cyan)">{fe(he)}</div><div class="st-l">F5 ERA</div></div><div><div class="st-s" style="color:{_c(float(hq) if isinstance(hq,(int,float)) else 50)}">{fq(hq)}</div><div class="st-l" title="Composite 0-100 score: ERA + WHIP + K/9 + HR/9 weighted. 70+ = elite, 50 = average, 30- = poor">Quality ⓘ</div></div><div><div class="st-s" style="color:var(--muted)">{fq(hg)}</div><div class="st-l" title="How likely this SP pitches 6+ innings. Based on IP per start / 7.0. 70+ = workhorse, 40- = early pull risk">Go Deep ⓘ</div></div></div>
        </div>
      </div>
      <div style="display:flex;justify-content:center;gap:0.7rem;margin-top:0.6rem;flex-wrap:wrap;align-items:center">
        <span class="pill {pc}">F5: {at}</span>
        <span class="bdg {cb}">{f5.get('confidence','low').upper()}</span>
        <span style="font-size:0.75rem;color:var(--muted)">ERA Δ {f5.get('f5_era_diff',0):+.2f} · Qual Δ {f5.get('f5_quality_diff',0):+.0f}</span>
        <span style="font-size:0.8rem;font-weight:600;color:var(--accent)">F5 Total: {f5.get('f5_total_estimate',4.5):.1f}</span>
      </div>"""


# ─── CONVERGENCE ─────────────────────────────────────────────────
def _conv(cv, an, hn):
    if not cv: return ""
    sc = cv.get("score",50); sig = cv.get("signal_count",0); ag = cv.get("agreeing_signals",0)
    ap = cv.get("agreement_pct",0); cf = cv.get("confidence","low")
    fav = cv.get("favored_side","none")
    fn = hn if fav=="home" else (an if fav=="away" else "Even")
    hw = cv.get("home_weight",0); aw = cv.get("away_weight",0)
    tw = hw+aw; hp = (hw/tw*100) if tw>0 else 50

    ccl = {"strong":"conv-s","high":"conv-h","medium":"conv-m"}.get(cf,"conv-l")
    scl = "var(--green)" if cf in ("strong","high") else ("var(--yellow)" if cf=="medium" else "var(--muted)")

    sh = ""
    for s in cv.get("breakdown",[]):
        d = s.get("direction","?")
        strength = s.get("strength", 0)
        note = s.get("note", "")
        dc = "var(--cyan)" if d=="home" else "var(--orange)"
        dl = hn[:3].upper() if d=="home" else an[:3].upper()
        # Dim weak signals
        opacity = "0.4" if strength <= 20 else "1"
        note_html = f' <span style="font-size:0.58rem;color:var(--muted);font-style:italic">({note})</span>' if note else ""
        sh += f'<div class="sig" style="opacity:{opacity}"><div class="dot" style="background:{dc}"></div><div class="nm">{s.get("name","?")}{note_html} <span style="font-size:0.62rem">({s.get("weight",0)*100:.0f}%)</span></div><div class="dr" style="color:{dc}">{dl}</div><div class="sr">{strength:.0f}</div></div>'

    return f"""
      <div class="g2">
        <div class="conv {ccl}">
          <div class="num" style="color:{scl}">{sc:.0f}</div>
          <div class="lbl">Convergence</div>
          <div style="margin-top:0.4rem;font-size:0.82rem;font-weight:600">{fn}</div>
          <div style="font-size:0.7rem;color:var(--muted)">{ag}/{cv.get('strong_signals',sig)} strong signals agree · {ap:.0f}%</div>
          <div style="font-size:0.62rem;color:var(--muted)">{sig} total signals (weak ones dimmed)</div>
          <div style="margin-top:0.5rem">
            <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;background:var(--border)"><div style="width:{hp:.0f}%;background:var(--cyan)"></div><div style="width:{100-hp:.0f}%;background:var(--orange)"></div></div>
            <div style="display:flex;justify-content:space-between;font-size:0.62rem;color:var(--muted);margin-top:0.15rem"><span>{hn[:3]} {hw:.2f}</span><span>{an[:3]} {aw:.2f}</span></div>
          </div>
        </div>
        <div class="cd" style="max-height:200px;overflow-y:auto"><div style="font-weight:600;font-size:0.72rem;color:var(--accent);margin-bottom:0.3rem">Signal Breakdown</div>{sh or '<div style="font-size:0.75rem;color:var(--muted)">No signals</div>'}</div>
      </div>"""


# ─── FIP + PITCHER ───────────────────────────────────────────────
def _fip_sec(g, an, hn):
    pe = g.get("pitcher_edge",{})
    pt = pe.get("adv_text","No data")
    pb = "bdg-g" if pe.get("advantage","even")!="even" else "bdg-m"
    fh = ""
    for sn, fd, sp in [(an, g.get("away_fip"), g.get("away_team",{}).get("pitcher","TBD")),
                        (hn, g.get("home_fip"), g.get("home_team",{}).get("pitcher","TBD"))]:
        if fd:
            # Use xERA if available, fallback to FIP
            has_xera = fd.get("xera") is not None
            metric_val = fd.get("xera") or fd.get("fip") or 0
            metric_label = "xERA" if has_xera else "FIP"
            era_val = fd.get("era", 0)
            gap = fd.get("gap") or fd.get("era_fip_gap", 0)
            fl = fd.get("flag", "") 
            detail = fd.get("detail", fd.get("flag_detail", ""))
            gc_ = "var(--red)" if gap > 0.5 else ("var(--green)" if gap < -0.5 else "var(--muted)")
            flag_line = ""
            if fl:
                flag_line = f'<div style="font-size:0.7rem;margin-top:0.15rem;font-weight:600;color:{gc_}">{fl} {detail}</div>'
            xwoba_line = ""
            if has_xera and fd.get("xwoba"):
                xwoba_line = f'<div style="font-size:0.68rem;color:var(--muted);margin-top:0.1rem">xwOBA: {fd["xwoba"]:.3f}</div>'
            fh += (
                f'<div class="cd" style="flex:1;min-width:130px">'
                f'<div style="font-size:0.7rem;color:var(--muted)">{sp} ({sn[:3]})</div>'
                f'<div style="display:flex;gap:0.6rem;align-items:baseline;margin-top:0.15rem">'
                f'<div><span style="font-size:0.72rem">ERA</span> <span class="st-s">{era_val:.2f}</span></div>'
                f'<div><span style="font-size:0.72rem">{metric_label}</span> <span class="st-s" style="color:var(--accent)">{metric_val:.2f}</span></div>'
                f'<div style="font-size:0.75rem;color:{gc_}">Δ{gap:+.2f}</div>'
                f'</div>{flag_line}{xwoba_line}</div>'
            )
    # Pitcher style + pitch mix (v2.4)
    props_data = g.get("props", {})
    pc = props_data.get("pitcher_cards", {})
    style_html = ""
    for side_key, side_name in [("away", an), ("home", hn)]:
        pcard = pc.get(side_key, {})
        style = pcard.get("style", {})
        dis = style.get("display", "")
        if dis and dis not in ("Unknown", "❓ Unknown"):
            ff = style.get("ff_velo")
            gb = style.get("gb_pct")
            reasons = style.get("reasons", [])
            arsenal_d = style.get("arsenal_detail", "")
            ff_str = f" · {ff:.0f}mph FB" if ff else ""
            gb_str = f" · GB {gb:.0f}%" if gb else ""
            reason_str = " · ".join(reasons[:2]) if reasons else ""
            style_html += (
                f'<div style="font-size:0.72rem;color:var(--muted);margin-top:0.15rem">'
                f'{side_name[:3]} SP: <span style="font-weight:600;color:var(--text)">{dis}</span>{ff_str}{gb_str}'
                f'</div>'
            )
            if arsenal_d:
                style_html += f'<div style="font-size:0.68rem;color:var(--cyan);margin-bottom:0.2rem">🎯 {arsenal_d}</div>'
    return f"""
      <div style="text-align:center;margin-bottom:0.5rem"><span class="bdg {pb}">{pt}</span></div>
      <div style="display:flex;gap:0.6rem;flex-wrap:wrap">{fh}</div>{style_html}"""


# ─── LINES + TOTALS ─────────────────────────────────────────────
def _lines(ln, te, g=None):
    tr = te.get("recommendation","N/A"); tm = te.get("model_total",0)
    tb = te.get("book_total",0); td = te.get("diff",0); tc = te.get("confidence","low")
    tcl = "var(--green)" if tr=="OVER" else ("var(--cyan)" if tr=="UNDER" else "var(--muted)")

    # Line movement + run line
    lm_html = ""
    move_html = ""
    if g:
        parts = []
        spread = ln.get("spread")
        if spread:
            hl = spread.get("home_line", 0)
            hp = spread.get("home_price")
            ap = spread.get("away_price")
            if hp and ap:
                h_s = f"+{hp}" if hp > 0 else str(hp)
                a_s = f"+{ap}" if ap > 0 else str(ap)
                parts.append(f"RL: {hl:+.1f} ({h_s}/{a_s})")
        if parts:
            lm_html = f'<span style="font-size:0.75rem;color:var(--muted)">{" · ".join(parts)}</span>'

        # Moneyline movement: Open → Close
        ml_open = ln.get("moneyline_open")
        ml_close = ln.get("moneyline_raw")
        if ml_open and ml_close and isinstance(ml_close, dict) and isinstance(ml_open, dict):
            an = g.get("away_team", {}).get("name", "")
            hn = g.get("home_team", {}).get("name", "")
            # Find matching team names (ESPN uses full names, we use full names)
            open_home = None
            close_home = None
            open_away = None
            close_away = None
            for name, odds in ml_open.items():
                if hn in name or name in hn:
                    open_home = odds
                elif an in name or name in an:
                    open_away = odds
            for name, odds in ml_close.items():
                if hn in name or name in hn:
                    close_home = odds
                elif an in name or name in an:
                    close_away = odds
            if open_home is not None and close_home is not None and open_away is not None and close_away is not None:
                # Movement: if line gets shorter (e.g., +140 → +120), that's sharp money
                home_delta = close_home - open_home
                away_delta = close_away - open_away
                move_lines = []
                # Show whichever side moved more
                if abs(home_delta) >= 15 or abs(away_delta) >= 15:
                    if home_delta < 0:
                        move_lines.append(f"<span class='line-move line-move-down'>▼ {hn.split()[-1]} {open_home:+d} → {close_home:+d} (sharps)</span>")
                    elif home_delta > 0:
                        move_lines.append(f"<span class='line-move line-move-up'>▲ {hn.split()[-1]} {open_home:+d} → {close_home:+d} (public)</span>")
                    if away_delta < 0:
                        move_lines.append(f"<span class='line-move line-move-down'>▼ {an.split()[-1]} {open_away:+d} → {close_away:+d} (sharps)</span>")
                    elif away_delta > 0:
                        move_lines.append(f"<span class='line-move line-move-up'>▲ {an.split()[-1]} {open_away:+d} → {close_away:+d} (public)</span>")
                if move_lines:
                    move_html = f'<div style="margin-top:0.3rem;display:flex;gap:0.4rem;justify-content:center;flex-wrap:wrap">{ " ".join(move_lines) }</div>'

    return f"""
    <div class="sec">
      <div class="sec-t">💰 Lines + Totals</div>
      <div style="display:flex;gap:1.2rem;justify-content:center;align-items:center;flex-wrap:wrap;font-size:0.82rem">
        <span style="font-weight:600;letter-spacing:0.2px">{ln.get('moneyline','N/A')}</span>
        <span style="font-weight:600">{ln.get('total','N/A')}</span>
        {lm_html}
        <span style="border-left:1px solid var(--border);padding-left:0.8rem;display:flex;align-items:center;gap:0.4rem">
          <span style="color:var(--muted)">Model</span>
          <span class="st-s" style="color:var(--accent)">{tm}</span>
          <span style="color:{tcl};font-weight:700">{tr}</span>
          <span style="font-size:0.75rem;color:{tcl}">({td:+.1f})</span>
          <span class="bdg {_bdg(tc)}">{tc.upper()}</span>
        </span>
      </div>
      {move_html}
    </div>"""


# ─── EV + KELLY + NRFI ──────────────────────────────────────────
def _edge(ev, ky, nr, an, hn):
    # EV
    if ev.get("has_line"):
        evh = f"""<div class="cd"><div class="cd-t">📈 Expected Value</div><div style="display:flex;gap:0.6rem;flex-wrap:wrap">
          <div style="flex:1;min-width:110px"><div style="font-size:0.7rem;color:var(--muted)">{an}</div><div style="font-size:0.75rem">{_fo(ev.get('away_odds'))} · Book {ev.get('away_book_prob',50):.0f}%</div><div style="font-size:0.75rem">Model {ev.get('away_model_prob',50):.0f}% · Edge {ev.get('away_edge',0):+.1f}%</div><div class="st-s {'ev-p' if ev.get('away_ev',0)>0 else 'ev-n'}">EV {'+' if ev.get('away_ev',0)>0 else ''}{ev.get('away_ev',0):.1f}%</div></div>
          <div style="flex:1;min-width:110px"><div style="font-size:0.7rem;color:var(--muted)">{hn}</div><div style="font-size:0.75rem">{_fo(ev.get('home_odds'))} · Book {ev.get('home_book_prob',50):.0f}%</div><div style="font-size:0.75rem">Model {ev.get('home_model_prob',50):.0f}% · Edge {ev.get('home_edge',0):+.1f}%</div><div class="st-s {'ev-p' if ev.get('home_ev',0)>0 else 'ev-n'}">EV {'+' if ev.get('home_ev',0)>0 else ''}{ev.get('home_ev',0):.1f}%</div></div>
        </div></div>"""
    else:
        evh = '<div class="cd"><div class="cd-t">📈 Expected Value</div><div style="font-size:0.75rem;color:var(--muted)">No line — set ODDS_API_KEY</div></div>'

    # Kelly
    ks = ky.get("side","pass"); kb = ky.get("suggested_bet",0)
    if ks!="pass" and kb>0:
        kn = hn if ks=="home" else an
        kyh = f"""<div class="cd"><div class="cd-t">💰 Kelly</div><div style="font-size:0.8rem;font-weight:600">{kn}</div><div style="display:flex;gap:0.8rem;margin-top:0.2rem"><div><div class="st-s" style="color:var(--green)">${kb:.0f}</div><div class="st-l">Bet</div></div><div><div class="st-s" style="color:var(--muted)">{ky.get('quarter_kelly',0):.1f}%</div><div class="st-l">¼ Kelly</div></div></div><div style="font-size:0.62rem;color:var(--muted);margin-top:0.2rem">${ky.get('bankroll',1000):.0f} bankroll</div></div>"""
    else:
        kyh = '<div class="cd"><div class="cd-t">💰 Kelly</div><div style="font-size:0.75rem;color:var(--muted)">No +EV — no bet</div></div>'

    # NRFI
    ns = nr.get("nrfi_score",50); nrc = nr.get("recommendation","SKIP"); nc = nr.get("confidence","low")
    if nrc=="NRFI": ne,ncl,nl = "🟢","var(--green)","NRFI"
    elif nrc=="YRFI": ne,ncl,nl = "🔴","var(--red)","YRFI"
    else: ne,ncl,nl = "⚪","var(--muted)","SKIP"
    nbp = max(2,min(98,ns))
    nbc = "var(--green)" if ns>=60 else ("var(--red)" if ns<=40 else "var(--yellow)")
    nrh = f"""<div class="cd"><div class="cd-t">🏏 NRFI / YRFI</div>
      <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem"><span>{ne}</span><span style="font-size:0.88rem;font-weight:700;color:{ncl}">{nl}</span><span class="bdg {_bdg(nc)}">{nc.upper()}</span><span style="font-weight:600;color:{ncl}">{ns:.0f}</span></div>
      <div style="display:flex;align-items:center;gap:0.4rem;font-size:0.68rem"><span style="color:var(--red)">YRFI</span><div style="flex:1;height:6px;border-radius:3px;background:var(--border);overflow:hidden"><div style="width:{nbp}%;height:100%;border-radius:3px;background:{nbc}"></div></div><span style="color:var(--green)">NRFI</span></div>
      <div style="display:flex;gap:0.8rem;margin-top:0.3rem;font-size:0.68rem;color:var(--muted)"><span>Away SP: {nr.get('away_pitcher_score',50):.0f}</span><span>Home SP: {nr.get('home_pitcher_score',50):.0f}</span></div>
    </div>"""

    return f"""
      <div class="g2"><div style="display:flex;flex-direction:column;gap:0.6rem">{evh}{kyh}</div>{nrh}</div>"""


# ─── SGP ─────────────────────────────────────────────────────────
def _sgp(sgps):
    if not sgps: return ""
    cards = ""
    for s in sgps:
        legs = " + ".join(s.get("legs",[]))
        cr = s.get("correlation","neutral")
        cc = {"strong":"var(--green)","positive":"var(--cyan)"}.get(cr,"var(--muted)")
        cb = _bdg(s.get("confidence","low"))
        cards += f'<div class="cd" style="flex:1;min-width:180px"><div style="font-size:0.8rem;font-weight:600">{legs}</div><div style="font-size:0.7rem;display:flex;gap:0.4rem;align-items:center;margin-top:0.2rem"><span style="color:{cc}">⚡ {cr}</span><span class="bdg {cb}">{s.get("confidence","low").upper()}</span></div><div style="font-size:0.66rem;color:var(--muted);margin-top:0.15rem">{s.get("note","")}</div></div>'
    return f"""<div style="display:flex;gap:0.6rem;flex-wrap:wrap">{cards}</div>"""


# ─── SITUATIONAL INTEL ────────────────────────────────────────────
def _situational(g):
    sit = g.get("situational", {})
    if not sit:
        return ""
    an = g.get("away_team", {}).get("name", "Away")
    hn = g.get("home_team", {}).get("name", "Home")
    rows = ""

    # Game Script
    gs = sit.get("game_script", {})
    if gs:
        rows += f'<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.03)"><span style="font-size:1rem">{gs.get("emoji","")}</span><div><span style="font-weight:600;font-size:0.8rem">{gs["script"].replace("_"," ").title()}</span><div style="font-size:0.7rem;color:var(--muted)">{gs.get("detail","")}</div><div style="font-size:0.7rem;color:var(--accent)">Best bets: {gs.get("bet_advice","")}</div></div></div>'

    # Triple Stack
    ts = sit.get("triple_stack")
    if ts:
        reasons = " + ".join([r for r in ts.get("reasons", []) if r])
        cl = "var(--red)" if ts["direction"] == "OVER" else "var(--cyan)"
        rows += f'<div style="padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.03)"><div style="font-weight:700;color:{cl}">{ts["emoji"]} TRIPLE STACK: {ts["direction"]}</div><div style="font-size:0.7rem;color:var(--muted)">{ts.get("detail","")} ({reasons})</div></div>'

    # Fade the Public
    fp = sit.get("fade_public")
    if fp:
        rows += f'<div style="padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.03)"><div style="font-weight:700;color:var(--yellow)">🔄 FADE THE PUBLIC</div><div style="font-size:0.7rem;color:var(--muted)">{fp.get("detail","")}</div></div>'

    # Travel Fatigue — both teams with details
    for travel in [sit.get("away_travel", {}), sit.get("home_travel", {})]:
        if travel and travel.get("fatigue_level") not in ("unknown", None):
            team = travel.get("team", "?")
            level = travel.get("fatigue_level", "fresh")
            log = travel.get("travel_log", "")
            if level in ("tired", "exhausted"):
                cl = "var(--red)" if level == "exhausted" else "var(--orange)"
                rows += f'<div style="padding:0.2rem 0;font-size:0.75rem"><span style="color:{cl}">✈️ {team}: {level.title()}</span> <span style="color:var(--muted)">({travel.get("detail","")})</span></div>'
                if log:
                    rows += f'<div style="font-size:0.68rem;color:var(--muted);margin-left:1.2rem;margin-bottom:0.2rem">Recent: {log}</div>'
            elif level == "moderate":
                rows += f'<div style="padding:0.2rem 0;font-size:0.72rem;color:var(--muted)">✈️ {team}: Moderate travel ({travel.get("miles_traveled",0)}mi, {travel.get("cities_visited",1)} cities)</div>'

    # Timezone — check both teams
    for tz in [sit.get("away_timezone", {}), sit.get("home_timezone", {})]:
        if tz and tz.get("alert"):
            rows += f'<div style="padding:0.2rem 0;font-size:0.75rem;color:var(--orange)">{tz["alert"]}</div>'

    # Rest Days + Schedule
    for rest in [sit.get("away_rest", {}), sit.get("home_rest", {})]:
        if rest:
            team = rest.get("team", rest.get("detail", "").split(" — ")[0] if " — " in rest.get("detail", "") else "?")
            detail = rest.get("detail", "")
            games_15 = rest.get("games_last_15_days", 0)
            had_yesterday = rest.get("had_game_yesterday", False)
            last_travel = rest.get("last_travel_date", "")
            if detail:
                rows += f'<div style="padding:0.2rem 0;font-size:0.75rem;color:var(--muted)">📅 {team}: {detail}</div>'
            if games_15:
                rows += f'<div style="padding:0.05rem 0;font-size:0.7rem;color:var(--muted);margin-left:1.2rem">Games last 15 days: {games_15}</div>'
            if had_yesterday:
                rows += f'<div style="padding:0.05rem 0;font-size:0.7rem;color:var(--orange);margin-left:1.2rem">⚠️ Played yesterday — no rest day</div>'
            if last_travel:
                rows += f'<div style="padding:0.05rem 0;font-size:0.7rem;color:var(--muted);margin-left:1.2rem">Last traveled: {last_travel}</div>'

    # Early Pull Scenario
    ep = sit.get("pull_scenario", {})
    if ep and ep.get("swing", 0) > 0.8:
        rows += f'<div style="padding:0.2rem 0;font-size:0.75rem;color:var(--muted)">📊 Starter pulled early: total jumps to {ep["early_pull_total"]} (+{ep["swing"]:.1f}R)</div>'

    return rows if rows else ""


# ─── PLAYER PROPS ────────────────────────────────────────────────
def _props(g):
    props = g.get("props", {})
    if not props:
        return ""
    kp = props.get("k_props", {})
    hp = props.get("hit_props", {})
    out = ""

    # K Props
    k_cards = ""
    for label, kd in [("Home SP", kp.get("home_pitcher")), ("Away SP", kp.get("away_pitcher"))]:
        if kd and kd.get("recommendation") != "NO EDGE":
            rec = kd["recommendation"]
            cl = "var(--green)" if rec == "OVER" else "var(--cyan)"
            cb = _bdg(kd.get("confidence", "low"))
            k_cards += (
                f'<div class="cd" style="flex:1;min-width:160px">'
                f'<div style="font-size:0.78rem;font-weight:600">{kd.get("pitcher","?")} ({label})</div>'
                f'<div style="display:flex;gap:0.6rem;margin-top:0.2rem;align-items:baseline">'
                f'<div><span class="st-s" style="color:{cl}">{rec} {kd["likely_line"]:.1f}</span><div class="st-l">K Prop</div></div>'
                f'<div><span class="st-s">{kd["proj_k"]:.1f}</span><div class="st-l">Projected</div></div>'
                f'<div><span class="st-s" style="color:var(--muted)">{kd["k9"]:.1f}</span><div class="st-l">K/9</div></div>'
                f'</div>'
                f'<div style="font-size:0.7rem;color:var(--muted);margin-top:0.2rem">vs {kd["opp_k_rate"]:.1%} K rate (mod: {kd["k_rate_modifier"]:.2f}x)</div>'
                f'<div style="margin-top:0.2rem"><span class="bdg {cb}">{kd["confidence"].upper()}</span></div>'
                f'</div>'
            )
    if k_cards:
        out += f'<div style="margin-bottom:0.5rem"><div style="font-size:0.72rem;font-weight:600;color:var(--cyan);margin-bottom:0.3rem">⚡ Strikeout Props</div><div style="display:flex;gap:0.6rem;flex-wrap:wrap">{k_cards}</div></div>'

    # Hit Props (deep profiler)
    for side_label, hitters in [("Home Hitters", hp.get("home_hitters", [])),
                                  ("Away Hitters", hp.get("away_hitters", []))]:
        if not hitters:
            continue
        h_rows = ""
        for h in hitters[:4]:
            cb = _bdg(h.get("confidence", "low"))
            flags = " ".join(h.get("flags", []))
            flags_html = f' <span style="font-size:0.7rem">{flags}</span>' if flags else ""
            order = h.get("order", "?")
            # Main line
            h_rows += (
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:0.25rem 0;font-size:0.75rem;border-bottom:1px solid rgba(255,255,255,0.03)">'
                f'<div><span style="font-weight:600">{h["name"]}</span> <span style="color:var(--muted)">{h.get("position","?")} #{order}</span>'
                f' <span style="color:var(--muted)">({h.get("bat_side","?")})</span>{flags_html}</div>'
                f'<div style="display:flex;gap:0.4rem;align-items:center">'
                f'<span style="font-size:0.72rem">.{str(h.get("season_avg","?")).replace("0.","").replace(".","")[:3]} AVG</span>'
                f'<span style="font-size:0.72rem">.{str(h.get("season_ops","?")).replace("0.","").replace(".","")[:3]} OPS</span>'
                f'<span class="bdg {cb}">{h["recommendation"]}</span>'
                f'</div></div>'
            )
            # Detail line — splits + recent + statcast + style matchup
            details = []
            if h.get("platoon_ops") and h["platoon_ops"] != "N/A":
                details.append(f'vs hand: .{str(h["platoon_ops"]).replace("0.","").replace(".","")[:3]}')
            if h.get("risp_avg") and h["risp_avg"] != "N/A":
                details.append(f'RISP: .{str(h["risp_avg"]).replace("0.","").replace(".","")[:3]}')
            if h.get("recent_form") and h["recent_form"] != "N/A":
                details.append(f'L5: {h["recent_form"]}')
            if h.get("xba"):
                details.append(f'xBA .{str(h["xba"]).replace("0.","")[:3]}')
            if h.get("season_hr", 0) > 0:
                details.append(f'{h["season_hr"]} HR')
            # v2.4: batter vs pitcher style matchup
            sm = h.get("style_matchup", {})
            sm_note = sm.get("note", "")
            if sm_note and sm_note != "Neutral matchup":
                is_adv = any(w in sm_note.lower() for w in ["advantage", "can do", "contact"])
                is_risk = any(w in sm_note.lower() for w in ["risk", "mismatch", "low power"])
                stl = "var(--green)" if is_adv else ("var(--red)" if is_risk else "var(--muted)")
                details.append(f'<span style="color:{stl};font-size:0.66rem">{sm_note[:65]}</span>')
            detail_str = " · ".join(details)
            h_rows += f'<div style="font-size:0.66rem;color:var(--muted);margin-bottom:0.15rem">{detail_str}</div>'
            # Reasons
            for r in h.get("reasons", [])[:3]:
                h_rows += f'<div style="font-size:0.64rem;color:var(--muted);padding-left:0.5rem">→ {r}</div>'
            # HR opportunity detail
            if h.get("hr_opportunity") and h.get("hr_reasons"):
                hr_text = " + ".join(h["hr_reasons"][:2])
                h_rows += f'<div style="font-size:0.66rem;color:var(--orange);padding-left:0.5rem;margin-bottom:0.3rem">🏠 HR: {hr_text}</div>'
            else:
                h_rows += '<div style="margin-bottom:0.2rem"></div>'
        if h_rows:
            out += f'<div style="margin-bottom:0.5rem"><div style="font-size:0.72rem;font-weight:600;color:var(--cyan);margin-bottom:0.3rem">🔥 {side_label} — Hitter Props</div>{h_rows}</div>'

    return out if out else ""


# ─── ADVANCED MATCHUP ────────────────────────────────────────────
def _extras(g):
    ex = g.get("extras_display", {})
    me = g.get("matchup_extras", {})
    if not ex and not me:
        return ""
    an = g.get("away_team", {}).get("name", "Away")
    hn = g.get("home_team", {}).get("name", "Home")

    rows = ""

    # RISP section
    ar = ex.get("away_risp", "")
    hr = ex.get("home_risp", "")
    if ar or hr:
        rows += '<div style="margin-bottom:0.5rem"><div style="font-size:0.72rem;font-weight:600;color:var(--cyan);margin-bottom:0.2rem">🎯 Runners in Scoring Position</div>'
        if ar:
            rows += f'<div style="font-size:0.75rem"><span style="color:var(--muted)">{an} SP vs RISP:</span> {ar}</div>'
        if hr:
            rows += f'<div style="font-size:0.75rem"><span style="color:var(--muted)">{hn} SP vs RISP:</span> {hr}</div>'
        rows += '</div>'

    # Defense
    ad = ex.get("away_def", "")
    hd = ex.get("home_def", "")
    if ad or hd:
        rows += '<div style="margin-bottom:0.5rem"><div style="font-size:0.72rem;font-weight:600;color:var(--cyan);margin-bottom:0.2rem">🧤 Defense</div>'
        if ad:
            rows += f'<div style="font-size:0.75rem"><span style="color:var(--muted)">{an}:</span> {ad}</div>'
        if hd:
            rows += f'<div style="font-size:0.75rem"><span style="color:var(--muted)">{hn}:</span> {hd}</div>'
        rows += '</div>'

    # Stolen bases + speed
    asb = ex.get("away_sb", "")
    hsb = ex.get("home_sb", "")
    sbm = me.get("sb_matchup", {})
    if asb or hsb:
        sbe = sbm.get("sb_edge", "even")
        sec = "var(--orange)" if sbe == "away" else ("var(--cyan)" if sbe == "home" else "var(--muted)")
        rows += f'<div style="margin-bottom:0.5rem"><div style="font-size:0.72rem;font-weight:600;color:var(--cyan);margin-bottom:0.2rem">⚡ Baserunning + Speed</div>'
        if asb:
            rows += f'<div style="font-size:0.75rem"><span style="color:var(--muted)">{an}:</span> {asb}</div>'
        if hsb:
            rows += f'<div style="font-size:0.75rem"><span style="color:var(--muted)">{hn}:</span> {hsb}</div>'
        if sbe != "even":
            sen = an if sbe == "away" else hn
            rows += f'<div style="font-size:0.75rem;font-weight:600;color:{sec}">SB Edge: {sen}</div>'
        rows += '</div>'

    # Shadows
    shadow = ex.get("shadow", "")
    if shadow:
        rows += f'<div style="margin-bottom:0.3rem"><div style="font-size:0.72rem;font-weight:600;color:var(--cyan);margin-bottom:0.2rem">🌅 Shadow Impact</div>'
        rows += f'<div style="font-size:0.75rem">{shadow}</div></div>'

    if not rows:
        return ""
    return f'<div style="display:flex;flex-direction:column;gap:0.1rem">{rows}</div>'


# ─── BANNER ──────────────────────────────────────────────────────
def _banner(g, an, hn, gc, grd):
    cv = g.get("convergence",{})
    fav = cv.get("favored_side","none")
    fn = hn if fav=="home" else (an if fav=="away" else "No Edge")
    fav_label = f"Grade for: <b style='color:var(--accent)'>{fn}</b>" if fav in ("home","away") else "Grade: No Clear Side"
    rec = g.get("analysis",{}).get("recommendation","⚪ NEUTRAL")
    cv = g.get("convergence",{}); ev = g.get("ev_data",{})
    cf = cv.get("confidence","low")
    bc = {"strong":"var(--green)","high":"var(--green)","medium":"var(--yellow)"}.get(cf,"var(--border2)")
    evb = ""
    if ev.get("has_line") and ev.get("best_ev",0)>0:
        esn = hn if ev["best_side"]=="home" else an
        evb = f' <span style="color:var(--green);font-size:0.82rem">+EV {ev["best_ev"]:.1f}% {esn}</span>'
    nar = g.get("narrative","")
    return f"""
    <div class="ban" style="border-top-color:{bc}">
      <span class="grd {gc}" style="display:inline-flex;margin-right:0.5rem;vertical-align:middle;width:32px;height:32px;font-size:0.85rem">{grd}</span><span style="font-size:0.85rem;font-weight:700;vertical-align:middle">{fav_label}</span>
      <div class="ban-rec" style="margin-top:0.3rem">{rec}{evb}</div>
      {f'<div class="ban-nar">{nar}</div>' if nar else ''}
    </div>"""


def save_report(html: str, filename: str = None) -> str:
    if filename is None:
        filename = "mlb_edge_report.html"
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n✅ Report saved to: {filepath}")
    return str(filepath)
