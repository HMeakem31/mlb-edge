# MLB Edge — Deep Research: Umpire, Weather, Statcast
**Date:** June 5, 2026  
**Objective:** Identify exactly what data exists, what's free, and what's buildable for our zero-budget, poor-computer constraints.

---

## 1. UMPIRE IMPACT — WHAT THE DATA SAYS

### The Science
- A **wide-zone umpire** (pitcher-friendly) adds +1.5–2.5 K/game and **suppresses scoring by 0.5–1.5 runs/game**
- A **tight-zone umpire** (hitter-friendly) removes 1.5–2.5 K/game and **inflates scoring by 0.5–1.5 runs/game**
- Some umpires show measurable **home team bias** — up to +0.5 runs/game home advantage beyond normal HFA
- ABS Challenge System in 2026 has **shrunk shadow zone called strikes from 2.3% (2022) to 1.5% (2026)** — umpires are tightening overall, but individual variance remains large

### Key Metrics That Move Lines

| Metric | What It Measures | Betting Impact |
|--------|-----------------|----------------|
| **Avg Runs/Game** | Total runs in games this ump calls | Direct O/U impact — ranges from 5.7 (Marvin Hudson) to 12.25 (Jen Pawol) |
| **K/Game** | Strikeouts per game | Affects pitcher K props — ranges from 13.6 to 20.2 |
| **BB/Game** | Walks per game | More walks = more baserunners = more runs |
| **O/U Record** | Historical over/under results | Some umps hit 56% overs, others 44% |
| **Home Win Rate** | Home team win % | Some umps give measurable home bias |
| **Home Advantage (runs)** | Home team scoring edge | Ranges from -0.5 to +0.5 runs vs visitor |
| **Favor** (UmpScorecards) | Run impact favoring one team | Measures systematic bias per game |
| **Accuracy / Accuracy Above Expected** | Correctness of calls vs expected | Low accuracy = more chaos = more variance |
| **BA / OBP / OPS** (FantasyInfoCentral) | Batting stats in this ump's games | Direct proxy for offensive environment |
| **Vis Score / Home Score** | Avg runs for visitor vs home under this ump | Home/away run split |

### Our Current State vs What's Available

| Feature | Our Current | What's Available for Free | Gap |
|---------|-------------|--------------------------|-----|
| **Tendency** | Hardcoded dict of 30 umps ("tight"/"loose"/"neutral") | OddsShark: avg total, walks, Ks, home W/L for every ump. FantasyInfoCentral: BA, OBP, OPS, Home Adv, Hits/G, BB/G, SO/G for ALL umps. UmpScorecards: accuracy, consistency, favor, run impact with downloadable data | Massive — we use a 3-value label when rich numeric data exists |
| **Run impact** | None — just "tight/loose" which maps to ±3 pts in game score | Actual avg runs/game per umpire available from OddsShark/RefMetrics | Critical gap |
| **O/U tendency** | None | OddsShark tracks O/U record per ump | High-value gap |
| **Home bias** | None | FantasyInfoCentral tracks Vis Score vs Home Score per ump | Medium gap |
| **K/BB rates** | None | OddsShark + FantasyInfoCentral both track per-ump | Affects pitcher K props |

### Data Sources (Free, No API Key)

1. **UmpScorecards.com** — Per-game scorecards with accuracy, consistency, favor, run impact. Downloadable CSV. Has API-like URL structure: `umpscorecards.com/data/single-umpire/{NAME}`
2. **OddsShark MLB Umpire Stats** — Season avg total, walks, Ks, home W/L, O/U record, moneyline results per ump
3. **FantasyInfoCentral.com/mlb/umpires** — BA, OBP, OPS, Hits/G, BB/G, SO/G, Home Adv, Favors (Pitchers/Hitters/Neither) for ALL umps
4. **RefMetrics.com** — We already scrape this for assignments. Also has avg runs and pace data
5. **Covers.com/sport/baseball/mlb/umpires** — Full betting stats and records per ump for 2026
6. **RotoWire** — Daily umpire stats page

### Implementation Plan

**Immediate (Zero extra API calls):**
- Build a comprehensive umpire database dict with numeric fields: `avg_runs`, `k_per_game`, `bb_per_game`, `over_pct`, `home_adv`, `favors` — hardcoded from OddsShark/FantasyInfoCentral data for top 40 active umps
- Replace the binary "tight/loose/neutral" with a **continuous Umpire Run Impact score** (e.g., -1.5 to +1.5 runs vs league avg)
- Feed into: convergence score (weighted signal), totals model adjustment, NRFI adjustment, narrative

**Phase 2 (1 API call/run):**
- Scrape today's assignments from MLB API game feed (we already get game data — umpire is in the boxscore hydration)
- Match to our database for automatic lookup

**Phase 3 (Optional, 1 scrape/day):**
- Scrape UmpScorecards or FantasyInfoCentral for live 2026 data (once daily, cache 24 hours)
- Self-updating umpire database

---

## 2. WEATHER — WHAT THE PHYSICS SAYS

### The Science (Quantified)

| Factor | Mechanism | Magnitude | Betting Impact |
|--------|-----------|-----------|----------------|
| **Temperature** | Warm air = less dense = less drag | +4 feet carry per 10°F rise | ~20 feet diff between 45°F and 95°F game |
| **Wind (blowing out)** | Tailwind adds carry to fly balls | +19 feet per 5 mph tailwind; Wrigley: >10mph out = **60%+ overs since 2005** | **Biggest single weather factor** |
| **Wind (blowing in)** | Headwind kills fly balls | Similar magnitude in reverse | Strong under signal |
| **Air Pressure** | Low pressure = thinner air = less drag | +2 feet per 0.3 inHg drop; **Denver 15% less pressure → +30 feet on HRs** | Already captured in park factor for altitude |
| **Humidity** | Water vapor lighter than N₂/O₂ → technically LESS dense air | Only +2 feet from 0% to 100% humidity aerodynamically | **OVERRATED by public** — ball absorbs moisture, gets heavier, offsetting benefit. Net effect ≈ neutral or slightly negative |
| **Altitude** | Permanent pressure reduction | +30 feet at 5,280 ft (Coors) vs sea level; also reduces pitch break by 2-3 inches | Already in park factors, but breaking ball impact isn't |

### What MLB Just Added (2025)
- **Weather Applied Metrics** were added to Statcast in Feb 2025
- Tracks balls "aided" vs "prevented" by weather conditions per stadium
- Data shows Seattle loses ~25 HRs per season to wind; Wrigley gains significantly in June-July
- This data is on Baseball Savant but requires per-game lookup

### Our Current State vs What's Available

| Feature | Our Current | What We Should Do | Impact |
|---------|-------------|-------------------|--------|
| **Temperature** | ✅ Fetch from Open-Meteo (`temperature_2m`) | Good — but convert to run adjustment (+0.1 runs per 10°F above 70°F) | Low lift |
| **Wind speed** | ✅ Fetch (`wind_speed_10m`) | Good | Already done |
| **Wind direction** | ✅ Fetch (`wind_direction_10m`) but **direction relative to stadium is wrong** | 🔴 CRITICAL FIX: We need **stadium orientation** (which direction is home plate → CF). Wind 270° means nothing without knowing if CF faces 270° | High lift |
| **Surface pressure** | ❌ Not fetched | Open-Meteo has `surface_pressure` — one extra parameter, zero extra API calls | Easy fix |
| **Humidity** | ✅ Fetch (`relative_humidity_2m`) but **treat as positive** | Research says humidity is overrated/neutral. Reduce its weight or flip its sign | Easy fix |
| **Air density calc** | ❌ Not done | Can calculate: `ρ = (P_d / (R_d × T)) + (P_v / (R_v × T))`. Or simplified: use T + P + humidity to estimate density index | Medium lift, huge accuracy gain |
| **Stadium orientation** | ❌ Missing | **Required** to determine if wind is blowing IN or OUT. Each stadium has a known azimuth (degrees from home plate to center field). This is static, hardcode it once | Critical |
| **Run adjustment** | ❌ Wind_impact is categorical ("blowing_out") | Convert to numeric: estimated feet of carry change → estimated run adjustment (±0.3 to ±1.0 runs) | High lift |

### Stadium Orientations (Home Plate → Center Field Azimuth)
This is the **missing piece** — the direction from home plate looking toward center field. Without this, we cannot correctly determine if wind is blowing in or out.

Approximate azimuths (degrees clockwise from North):
```
ARI: 3°,   ATL: 190°, BAL: 12°,  BOS: 65°,  CHC: 225°,
CWS: 255°, CIN: 330°, CLE: 170°, COL: 340°, DET: 15°,
HOU: 347°, KC: 255°,  LAA: 205°, LAD: 335°, MIA: 195° (dome),
MIL: 180° (retractable), MIN: 335°, NYM: 135°, NYY: 70°,
OAK: 285°, PHI: 195°, PIT: 100°, SD: 190°, SF: 265°,
SEA: 185° (retractable), STL: 180°, TB: 315° (dome),
TEX: 195° (retractable), TOR: 315° (dome), WSH: 355°
```

**Wind Impact Formula:**
```
wind_heading = wind_direction_degrees  (direction wind comes FROM)
cf_azimuth = stadium_cf_direction
relative_angle = wind_heading - cf_azimuth
# If wind is coming from behind home plate (blowing out):
# relative_angle near 180° = blowing OUT to CF
# relative_angle near 0°/360° = blowing IN from CF
out_component = cos(relative_angle - 180°) * wind_speed
# out_component > 0 = blowing OUT, < 0 = blowing IN
```

### Open-Meteo Upgrade (Zero Extra Cost)
Add `surface_pressure` to existing API call:
```python
"current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,surface_pressure"
```
One extra field, same API call, same rate limit.

---

## 3. STATCAST — WHAT'S AVAILABLE AND HOW TO GET IT

### Key Metrics For Betting

#### Hitter Metrics
| Metric | What It Is | Betting Use |
|--------|-----------|-------------|
| **Exit Velocity (EV)** | How hard ball leaves bat (mph) | High EV = quality contact, leads to more hits and HRs |
| **Barrel %** | % of batted balls at optimal EV+angle | Best single predictor of HR rate |
| **Hard Hit %** | % of balls hit ≥ 95 mph | Correlates with overall offensive production |
| **xBA** | Expected batting avg based on EV + launch angle | Shows true skill — BA vs xBA gap = luck |
| **xSLG** | Expected slugging based on EV + launch angle | Same concept for power |
| **xwOBA** | Expected weighted on-base avg | Best single expected stat — combines contact quality |
| **wOBA vs xwOBA gap** | Luck indicator | Positive gap = overperforming (regression down). Negative = underperforming (regression up) |
| **Launch Angle** | Angle ball leaves bat | 25-35° = optimal HR angle |
| **Sprint Speed** | Running speed | Affects infield hit probability, SB props |

#### Pitcher Metrics
| Metric | What It Is | Betting Use |
|--------|-----------|-------------|
| **xERA** | Expected ERA based on quality of contact allowed | ERA vs xERA gap = luck/regression signal |
| **xwOBA Against** | Expected wOBA on contact allowed | Better than ERA for evaluating pitcher |
| **Whiff %** | % of swings that miss | High whiff = dominant stuff = K props |
| **Barrel % Against** | % of barrels allowed | Low = quality, high = getting crushed |
| **Hard Hit % Against** | % of hard contact allowed | Same concept |
| **Avg EV Against** | Avg exit velocity against | How hard batters hit this pitcher |
| **Chase %** | How often batters swing at pitches outside zone | High chase = pitcher is deceptive |

### Data Access (All Free)

| Source | What You Get | Method | Cost | Compute |
|--------|-------------|--------|------|---------|
| **Baseball Savant Leaderboards** | Season-level xBA, xSLG, xwOBA, EV, barrel% for ALL qualified players | Single CSV download URL | Free | **Light** — one 100KB CSV per leaderboard |
| **pybaseball** | Python library wrapping all Savant data | `pip install pybaseball` | Free | **Medium** — pandas dependency |
| **FanGraphs Leaderboards** | wRC+, FIP, xFIP, BABIP, K%, BB% for ALL players | CSV export or API | Free | **Light** |
| **Baseball Savant per-player** | Pitch-level data per batter/pitcher | Web scrape or pybaseball | Free | **Heavy** for pitch-level, **light** for season aggregates |
| **Statcast Search CSV** | Raw pitch-by-pitch data | `baseballsavant.mlb.com/statcast_search/csv` | Free | **Very heavy** — 700K+ pitches per season |

### What We Can Build (Ranked by Feasibility)

#### TIER 1: One CSV scrape per day (~100KB, cache 24h)
**Baseball Savant Expected Stats Leaderboard** — gives us xBA, xSLG, xwOBA, EV, barrel%, hard_hit% for every qualified pitcher and hitter in one call.

```
URL: https://baseballsavant.mlb.com/leaderboard/expected_statistics?type=pitcher&year=2026&position=&team=&min=1&csv=true
```

This gives us:
- **Pitcher xERA/xwOBA against** → regression flags (way better than our FIP calc)
- **Batter xwOBA** → identifies underperformers (bet on) and overperformers (fade)
- **Barrel %** → HR prop fuel
- **Hard Hit %** → general offensive quality indicator

#### TIER 2: pybaseball integration (heavier compute)
- `statcast_pitcher_expected_stats(2026)` → all pitcher expected stats
- `statcast_batter_expected_stats(2026)` → all batter expected stats
- `statcast_batter_exitvelo_barrels(2026)` → EV + barrel leaderboard

These return pandas DataFrames. One call per leaderboard, cacheable for 24h.

**Concern:** pybaseball requires pandas + numpy. On a poor computer, installing these adds ~100MB. But they're standard Python libraries with pip.

#### TIER 3: Per-pitcher Statcast (NOT recommended for poor computer)
- Pitch-level data is 700K+ rows per season
- Per-player queries are fast but multiplied across all today's pitchers = many requests
- Save this for when Statcast is explicitly enabled

### Implementation Architecture

```
Option A: Direct CSV scrape (NO pybaseball dependency)
- requests.get(savant_csv_url) → parse with csv module (no pandas needed)
- ~100KB download, cached 24h
- Gives us xERA, xwOBA, barrel%, EV for all qualified pitchers/batters
- Zero new dependencies

Option B: pybaseball (heavier but cleaner)
- pip install pybaseball
- statcast_pitcher_expected_stats(2026) + statcast_batter_expected_stats(2026)
- Returns pandas DataFrames with all expected stats
- Requires: pandas, numpy, requests (requests already installed)
```

**Recommendation: Option A** — direct CSV scrape with built-in csv module. No new dependencies. One HTTP call. Cache for 24 hours. Gets us 90% of the value with 10% of the compute.

---

## 4. SYNTHESIS — HOW THESE THREE CONNECT

The power isn't in any single upgrade — it's in how they feed each other:

```
UMPIRE (tight zone)
  → +1.5 K/game → affects pitcher K prop projections
  → -0.8 runs/game → feeds into TOTALS model
  → feeds into NRFI score (tight zone = fewer 1st inning runs)

WEATHER (wind blowing out 15mph)
  → +0.5 runs estimated → feeds into TOTALS model
  → increases HR probability → feeds into hitter HR props
  → NRFI gets penalty (wind out = easier to score)

STATCAST (pitcher has xERA 4.50 but ERA 3.00)
  → FIP/xERA regression flag (already built)
  → xwOBA against shows TRUE quality
  → Barrel% against shows HR vulnerability
  → Feeds into: F5 quality, convergence, EV, narrative

COMBINED EXAMPLE:
  - Umpire: Mark Carlson (tight zone, -0.5 runs/game, 46% overs)
  - Weather: 62°F, wind 12mph blowing IN from CF
  - Pitcher A: xERA 3.10, barrel% 5.2 (elite)
  - Pitcher B: xERA 2.80, barrel% 4.8 (elite)
  → ALL four signals say UNDER
  → Convergence: STRONG UNDER with 4/4 signals aligned
  → Totals model adjusts DOWN by 1.3 runs from baseline
  → NRFI confidence: HIGH
  → Narrative: "A+ UNDER. Tight-zone ump + cold wind in + two elite-contact-suppression pitchers.
     Model total 6.8 vs book 8.0 — 1.2 run edge."
```

---

## 5. IMPLEMENTATION PRIORITY

### Immediate Wins (Session 1 — Zero new dependencies)

| # | Task | What Changes | API Cost |
|---|------|-------------|----------|
| 1 | **Add stadium CF azimuths** to config.py (30 values) | Accurate wind in/out calculation | Zero |
| 2 | **Fix wind direction logic** in weather_fetcher.py using azimuth | Correct wind impact determination | Zero |
| 3 | **Add `surface_pressure` to weather API call** | One extra field, same call | Zero |
| 4 | **Build air density index** from temp + pressure + humidity | Physics-based ball carry estimate | Zero |
| 5 | **Build umpire database** with numeric metrics (avg_runs, k/g, over_pct, home_adv) for top 50 umps | Rich umpire signals replacing binary labels | Zero |
| 6 | **Umpire run adjustment** feeds into totals model, NRFI, convergence | All models improve | Zero |

### Second Session — One daily scrape

| # | Task | What Changes | API Cost |
|---|------|-------------|----------|
| 7 | **Scrape Baseball Savant expected stats CSV** (pitchers) | xERA, xwOBA, barrel%, EV for all qualified pitchers | 1 HTTP call/day |
| 8 | **Match today's starters** to Savant data → xERA regression flags | Replaces FIP with superior xERA | Zero (cached) |
| 9 | **Scrape Savant batter expected stats CSV** | xwOBA, barrel%, EV for all qualified batters | 1 HTTP call/day |
| 10 | **Surface top matchup batters** per game using xwOBA + barrel% | Player-level prop foundation | Zero (cached) |

---

*Research sources: WeatherApplied.com, Predictem, BetFirm, BettorEdge, FanGraphs, KXAN, CBS2Iowa, mlbprediction.com, OddsIndex, Baseball Savant, FanSided (ABS article), PracticalWebTools, OddsShark, FantasyInfoCentral, Covers, UmpScorecards, Outlier.bet, SportsInfoSolutions, ParlaySavant, pybaseball docs, Open-Meteo API docs, Sportradar, Reddit r/baseball*
