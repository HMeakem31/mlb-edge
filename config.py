# MLB Edge v2.1 — Competitive Analysis & Improvement Roadmap
**Date:** June 5, 2026  
**Objective:** Identify features from competitors we can steal, adapt, or leapfrog — all within our zero-budget, low-compute constraints.

---

## THE LANDSCAPE AT A GLANCE

| Competitor | Price | Core Strength | Our Edge Over Them | What They Have That We Don't |
|---|---|---|---|---|
| **Monster.bet** | $20-50/mo | AI assistant (MonsterGPT), odds comparison across 30+ books, confidence grades (A+ to C) | We're free, offline, no subscription, no token gimmick | AI chat assistant, odds comparison, parlay builder, confidence letter grades, DFS optimizer |
| **OddsJam** | $99-399/mo | Real-time +EV scanning, no-vig odds, arbitrage finder, CLV tracking | Free, no account needed, runs locally | +EV calculator, no-vig fair odds, closing line value tracking, arbitrage detection, Kelly criterion sizing |
| **Unabated** | $39-69/mo | Sharp consensus line ("Unabated Line"), F5 own pricing (not derived), professional calculators | We already do F5 analysis for free | Dedicated F5 Unabated Line, hedge calculator, alt-line pricing, vig-free consensus, CLV calculator |
| **BetQL** | ~$30/mo | Model-driven star ratings (1-5), public vs sharp money splits, line movement alerts | Our convergence score is more transparent (shows signal breakdown) | Star rating system, public/sharp money %, line movement visualization, trend engine |
| **Action Network** | $10-30/mo | Bet tracking + syncing, expert picks, public betting %, live odds | Our matchup analysis is deeper | Bet tracker, live odds feed, public betting percentages, expert written analysis, community |
| **HeatCheck HQ** | Free/$12/mo | 9-factor convergence engine (63.6% hit rate), DVP matchups, streak tracker, pitch mix analysis | Similar convergence concept — theirs is more mature | Multi-factor "Heat Score", DVP by position, pitch mix barrel/EV analysis, NRFI dashboard, streak detection, weather impact on props |
| **Outlier** | $20-130/mo | AI model marketplace, custom no-code model builder, Smart Signals (lightning bolt picks) | We're fully transparent, no black box | Custom model builder, injury integration, prop finder, community competitions |
| **Rithmm** | $30/mo | AI predictions for player props, batter-pitcher simulation | Our F5 focus is unique | ML-driven player prop projections, multi-season blended models |
| **Dimers** | Free/$25/mo | Monte Carlo simulations, probability forecasts, best bet picks | We have more depth per game | Simulation-based win probabilities, parlay builder, broad sport coverage |
| **FanGraphs** | Free | Sabermetric gold standard — wRC+, xERA, FIP, barrel rates | Different purpose, but their data could feed ours | xERA, FIP, wRC+, barrel rate, sprint speed, zone contact%, Statcast leaderboards |

---

## CRITICAL GAPS (What We're Missing That Actually Matters)

### 🔴 TIER 1 — HIGH IMPACT, FEASIBLE ON OUR BUDGET

#### 1. **Expected Value (EV) Calculation**
**Who does it:** OddsJam, Unabated, Monster.bet, HeatCheck  
**What it is:** Compare our model's implied probability against the sportsbook line to show the mathematical edge.  
**Why it matters:** This is THE metric sharp bettors care about. Without it, our convergence score is just directional — it says "lean home" but not "this bet has +4.2% EV."  
**Implementation:**
- We already have convergence score → convert to implied win probability
- Compare against Vegas moneyline (we already fetch from The Odds API)
- Display: `Our Prob: 58.2% | Book Implied: 52.4% | Edge: +5.8% | EV: +$5.80/100`
- **Cost: Zero extra API calls.** Pure math on data we already have.

#### 2. **Confidence Letter Grades (A+ to C)**
**Who does it:** Monster.bet (A+ through C grades), BetQL (1-5 stars)  
**What it is:** A single, instantly-digestible grade per game instead of making users parse numbers.  
**Why it matters:** Most users don't want to interpret "convergence 72.3, 5/7 signals." They want to see **A+** and know it's a strong play.  
**Implementation:**
- Map convergence score + agreement % + signal count to letter grades
- Strong (80%+ agreement, 5+ signals) = A+ / A
- High (67%+ agreement, 4+ signals) = B+ / B  
- Medium = C+ / C
- Low / Split = D (PASS)
- **Cost: Zero. Pure logic on existing data.**

#### 3. **Line Movement Indicator**
**Who does it:** Action Network, OddsJam, BetQL, SpankOdds  
**What it is:** Show if the line has moved since open (e.g., "Opened -135, Now -150 → sharp money on this side").  
**Why it matters:** Line movement is the single best indicator of where sharp money is going. If our model agrees with line movement direction, confidence skyrockets.  
**Implementation:**
- The Odds API returns opening and current lines — we may already have this or can get it
- Display arrow + delta: `NYY -135 → -150 (▼ 15 pts, sharp action)`
- Cross-reference with our convergence direction for "Model + Market Agree" signal
- **Cost: Possibly zero if already in API response, or 1 extra call.**

#### 4. **NRFI / YRFI (No Run First Inning)**
**Who does it:** HeatCheck HQ (dedicated NRFI dashboard), various tipsters  
**What it is:** Predict whether either team scores in the 1st inning.  
**Why it matters:** Hugely popular market. We already have pitcher ERA, K/9, WHIP, and leadoff hitter data proximity. This is low-hanging fruit.  
**Implementation:**
- Use starting pitcher's 1st-inning ERA proxy (WHIP * modifier)
- Combine with opposing team's 1st-inning scoring tendency (derivable from recent game data)
- Output: NRFI confidence score + recommendation
- **Cost: Zero extra API calls.** Derived from existing pitcher + team stats.

#### 5. **Bet Sizing Recommendation (Kelly Criterion)**
**Who does it:** OddsJam (rec bet size column), Unabated  
**What it is:** Given your edge and bankroll, how much should you bet?  
**Why it matters:** Most recreational bettors have no idea how to size bets. This is a massive value-add.  
**Implementation:**
- Kelly % = (bp - q) / b where b = decimal odds - 1, p = our probability, q = 1 - p
- Display fractional Kelly (quarter-Kelly for conservative): "Suggested: 1.2% of bankroll"
- Let user set bankroll in config (default $1000)
- **Cost: Zero. Pure math.**

---

### 🟡 TIER 2 — MEDIUM IMPACT, MODERATE EFFORT

#### 6. **Streak Detection Engine**
**Who does it:** HeatCheck HQ (automatic streak surfacing), Action Network  
**What it is:** Auto-detect hot/cold streaks beyond just "W3" — e.g., "Team has scored 5+ runs in 6 of last 7" or "Pitcher has allowed 2 ER or fewer in 5 straight."  
**Why it matters:** Streaks are the most intuitive signal for recreational bettors. Our current streak data is just W/L from standings.  
**Implementation:**
- We already fetch recent games (3 games) — increase to 7-10
- Parse run differential, pitcher performance, offensive output patterns
- Flag notable streaks: "BOS: Over 8.5 total has hit in 5 of last 6"
- **Cost: Slight increase in API calls (more recent games), but cacheable.**

#### 7. **Player Prop Recommendations**
**Who does it:** Monster.bet, HeatCheck HQ, Outlier, BetQL, Rithmm, FTA Prop Edge  
**What it is:** Specific player-level picks — "Gerrit Cole Over 6.5 Ks (-120) — Heat Score 78"  
**Why it matters:** Player props are the fastest-growing betting market. Our current prop section is generic team-level.  
**Implementation:**
- We already fetch pitcher stats (K/9, ERA, HR/9)
- Cross-reference with opposing team's K rate, contact rate
- Generate: "Cole O 6.5 Ks — K/9: 10.2, vs team that Ks 25% of the time"
- For hitters: use top-of-order batters vs pitcher handedness
- **Cost: Some additional API calls for lineup/batter stats, but cacheable.**

#### 8. **Historical Model Accuracy Tracking**
**Who does it:** SportBot AI (public ROI), Leans.ai (verified 9-10% ROI), HeatCheck (63.6% hit rate)  
**What it matters:** Without a track record, users have no reason to trust our model. Every serious platform publishes hit rates.  
**Implementation:**
- Save each day's predictions to a JSON log
- Next day, fetch results and compare
- Build cumulative: "Season Record: 127-98 (56.4%) | ROI: +8.2%"
- Display in report header
- **Cost: One API call next day for results. Disk storage for history.**

#### 9. **Statcast / Advanced Metrics Integration**
**Who does it:** FanGraphs, HeatCheck HQ (barrel rate, exit velocity, xSLG), Baseball Savant  
**What it is:** xERA, FIP, barrel rate, hard hit %, expected stats that reveal true pitcher/hitter quality vs luck.  
**Why it matters:** Our current pitcher quality score uses surface stats (ERA, WHIP). xERA and FIP separate skill from luck. A pitcher with 3.00 ERA but 4.50 xERA is due for regression — that's a bet.  
**Implementation:**
- We have Statcast infrastructure (statcast_fetcher.py) but it's disabled
- Could scrape Baseball Savant leaderboards (free, public data) for xERA, FIP, barrel%
- Or use pybaseball library (already in ecosystem)
- **Cost: Moderate — one bulk scrape per day, cacheable. Heavy on compute though.**

#### 10. **Hitter vs Pitcher Arsenal Matchup**
**Who does it:** HeatCheck HQ (per-pitch barrel rate, exit velocity, ISO by pitch type)  
**What it is:** How does this specific batter perform against this pitcher's pitch mix?  
**Why it matters:** A batter might crush fastballs but whiff on sliders. If tonight's pitcher throws 60% sliders, that batter is in trouble regardless of overall stats.  
**Implementation:**
- Would need pitch-level data from Statcast or Baseball Savant
- Heavy compute/data requirement
- **Cost: High — may exceed our compute budget. DEFER unless Statcast is enabled.**

---

### 🟢 TIER 3 — NICE-TO-HAVE / FUTURE

#### 11. **Parlay Builder**
**Who does it:** Monster.bet, OddsJam, Dimers, HOF Bets  
**What it matters:** Parlays are where sportsbooks make money — and where informed bettors with correlated legs can find value.  
**Implementation:** Combine our best convergence picks + F5 + props into suggested parlays with calculated fair odds.

#### 12. **AI Chat Assistant**
**Who does it:** Monster.bet (MonsterGPT), ParlaySavant  
**What it matters:** Natural language queries ("Who should I bet tonight?") are the future of the interface.  
**Implementation:** Would need LLM integration — not feasible on current budget/compute.

#### 13. **Live / In-Game Betting Signals**
**Who does it:** Unabated (in-game betting tool), OddsJam  
**What it matters:** Live betting is growing fast but requires real-time data pipeline.  
**Implementation:** Far beyond our current architecture. DEFER.

#### 14. **Odds Comparison Across Books**  
**Who does it:** Everyone (OddsJam, Unabated, BetStamp, Action Network, Monster.bet)  
**What it matters:** Line shopping is the single easiest way to increase ROI.  
**Implementation:** The Odds API supports multiple books — we'd need the paid tier for broad coverage.

---

## WHAT COMPETITORS GET WRONG (Our Advantages)

### ✅ Things we already do better than most:

1. **Transparency** — Our convergence score shows every signal, weight, direction, and strength. Monster.bet and BetQL are black boxes. HeatCheck is the only competitor with similar transparency.

2. **F5 as first-class citizen** — Most tools bolt F5 on as an afterthought. We built it into the core pipeline. Only Unabated treats F5 with dedicated pricing (and they charge $39+/mo for it).

3. **Zero cost** — Every competitor charges $10-400/month. We're free, local, no account, no data collection.

4. **Offline-capable** — Once cached, our report works without internet. No competitor offers this.

5. **Full-game context** — We combine weather + umpire + park factor + bullpen fatigue + platoon + splits + F5 + convergence in one view. Most tools specialize in one slice.

6. **No black box** — Users see exactly why we recommend a side. The signal breakdown is the report. BetQL gives you "4 stars" with no explanation. OddsJam gives you "+EV 3.2%" with no matchup context.

---

## PRIORITY IMPLEMENTATION PLAN

### Phase 1 — Quick Wins (Zero API cost, pure logic)
| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | **EV Calculation** | 2-3 hrs | 🔥🔥🔥🔥🔥 |
| 2 | **Letter Grades (A+ to D)** | 1 hr | 🔥🔥🔥🔥 |
| 3 | **Kelly Criterion Bet Sizing** | 1 hr | 🔥🔥🔥 |
| 4 | **NRFI Score** | 2 hrs | 🔥🔥🔥🔥 |

### Phase 2 — Low-Cost Enhancements
| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 5 | **Line Movement Indicator** | 2-3 hrs | 🔥🔥🔥🔥 |
| 6 | **Enhanced Streak Detection** | 3-4 hrs | 🔥🔥🔥 |
| 7 | **Historical Accuracy Log** | 3-4 hrs | 🔥🔥🔥🔥 |

### Phase 3 — Bigger Lifts
| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 8 | **Player Prop Engine** | 6-8 hrs | 🔥🔥🔥🔥🔥 |
| 9 | **Statcast / xERA Integration** | 4-6 hrs | 🔥🔥🔥 |
| 10 | **Parlay Suggestions** | 4-5 hrs | 🔥🔥🔥 |

---

## BOTTOM LINE

The market charges $10-400/month for tools that do pieces of what we do. Our biggest gaps are:

1. **No EV calculation** — This is non-negotiable for credibility with sharp bettors
2. **No simplified grade** — Casual bettors need A/B/C, not convergence scores
3. **No track record** — Start logging predictions TODAY so we can publish accuracy
4. **No NRFI** — Massive popular market we can serve with zero extra data
5. **No line movement** — The market is telling us where the smart money is and we're ignoring it

The good news: **Items 1-4 cost us ZERO additional API calls.** They're pure math on data we already collect. We can implement all four in a single session and leap from "cool project" to "legitimate competitor" overnight.

---

*Analysis based on: Monster.bet, OddsJam, Unabated, BetQL, Action Network, HeatCheck HQ, Outlier, Rithmm, Dimers, RebelBetting, Pikkit, BetStamp, FanGraphs, ParlaySavant, Leans.ai, SportBot AI, Props.cash, SpankOdds, HOF Bets, FTA Prop Edge, PropsMadness, Linemate, Oddible, ScoresAndOdds, RotoGrinders, Sportsbook Scout*
