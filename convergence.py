# MLB Edge v2.2 — Competitive Analysis v2 (Post-Phase 1)
**Date:** June 5, 2026  
**Context:** Phase 1 shipped (EV, Grades, Kelly, NRFI). This analysis identifies what to steal next and — critically — gaps the *entire market* has that we can fill first.

---

## WHAT PHASE 1 CHANGED IN OUR COMPETITIVE POSITION

| Feature | Before Phase 1 | After Phase 1 | Who Still Beats Us |
|---|---|---|---|
| EV Calculation | ❌ None | ✅ Model prob vs devigged line | OddsJam (sharper devig across 100+ books) |
| Letter Grades | ❌ Raw numbers only | ✅ A+ through D | Monster.bet (similar), Oddible (Great/Good/Fair/Bad) |
| Bet Sizing | ❌ None | ✅ Quarter-Kelly with cap | OddsJam, HyperPicks |
| NRFI | ❌ None | ✅ Score + YRFI/NRFI rec | HeatCheck HQ (deeper — uses Statcast 1st-inning data) |

**We now match or exceed 80% of features in tools costing $20-50/month. The remaining gaps are specific and attackable.**

---

## PART 1: FEATURES WE CAN STEAL

### 🔴 HIGH PRIORITY — Clear competitive lift, feasible on our budget

#### 1. Regression Flags (xERA vs ERA / FIP vs ERA)
**Who does it:** FanGraphs (free data), WinnersAndWhiners (AI F5 model uses xERA/FIP regression), Baseball Savant  
**What the market says:** "A starter with a 2.50 ERA but a 4.00 xERA is due for regression. His F5 line is priced on the shiny 2.50 ERA. You know that ERA is propped up by luck. Fade him." — mlbprediction.com  
**Why it matters:** Our pitcher quality score uses surface ERA/WHIP. Every sharp bettor knows surface stats lie. xERA, FIP, and BABIP separate skill from luck. WinnersAndWhiners specifically builds their entire F5 model on xERA/FIP regression. We have F5 built — adding regression flags makes it elite.  
**Implementation:**
- Scrape FanGraphs leaderboard CSV once daily (free, public, ~50KB)
- Or calculate FIP ourselves: FIP = ((13×HR + 3×BB - 2×K) / IP) + constant
- We already have HR/9, BB/9, K/9, IP from pitcher stats — **FIP is just math on existing data**
- Flag: "ERA 2.95 but FIP 3.82 → ⚠️ Overperforming by 0.87 runs"
- **Cost: Zero if we calculate FIP. One tiny scrape if we want xERA from FanGraphs.**

#### 2. Prediction History / Accuracy Log
**Who does it:** SportBot AI (public ROI), Leans.ai (verified 9-10% ROI), HeatCheck (63.6% hit rate on convergence picks), Oddible (auto-tracked CLV)  
**What the market says:** "Transparency is the only feature that pays the bills in 2026. If a tool hides its losing streaks behind deleted posts, it's not AI; it's a scam." — FantasyLabs  
**Why it matters:** Without a track record, we have zero credibility. Every serious tool publishes hit rates. This is the #1 thing separating us from legitimacy.  
**Implementation:**
- After each run, save predictions to `data/predictions/YYYY-MM-DD.json`
- Include: game, favored side, grade, convergence score, EV, NRFI pick
- Next-day script checks MLB API for results, scores accuracy
- Running tally in report header: "Season: 127-98 (56.4%) | ROI: +8.2% | NRFI: 42-31 (57.5%)"
- **Cost: One extra API call per day for yesterday's scores. ~2KB storage per day.**

#### 3. Run Line / Alt Line Analysis
**Who does it:** Unabated (alt-line pricing calculator), OddsJam (alt spreads), VegasInsider  
**What the market says:** Run lines (-1.5 / +1.5) are the bread and butter of MLB betting. Most tools only analyze moneyline.  
**Why it matters:** Our model predicts direction, but not margin. A team favored at -150 ML might be +130 on the -1.5 run line. If our convergence score is A+ with 5/6 signals, the run line might be the better value play.  
**Implementation:**
- Our EV engine already has model probability. Convert to implied run margin.
- If model prob > 60% → flag run line as potentially +EV
- If model prob 52-58% → flag moneyline only
- The Odds API already returns spread data (we fetch it but don't display)
- **Cost: Zero — data already fetched, just unused.**

#### 4. Over/Under Total Analysis
**Who does it:** Every tool — but most only show the line, not the analysis  
**What nobody does well:** Combining pitcher F5 projections + park factor + weather + bullpen into a total estimate and comparing it to the book total  
**Why it matters:** We already compute F5 total estimate. We have park factor. We have weather. We have bullpen fatigue. We're sitting on a totals model and not using it.  
**Implementation:**
- F5 total estimate → extrapolate to full-game total (F5 × ~1.85 modifier adjusted by bullpen fatigue)
- Compare our projected total vs book total
- Display: "Model Total: 8.7 | Book: 8.0 | Edge: Over +0.7 runs"
- **Cost: Zero. Pure math on existing data.**

#### 5. Same-Game Parlay (SGP) Correlations
**Who does it:** HeatCheck HQ (SGP correlation guide), Monster.bet (parlay builder), Dimers  
**What the market says:** "Parlays are where sportsbooks make money — and where informed bettors with correlated legs can find value." Correlated SGPs (e.g., team to win + over on total + pitcher under on strikeouts) beat uncorrelated parlays.  
**Why it matters:** SGPs are the fastest-growing market segment. We have all the components — we just need to suggest logical combos.  
**Implementation:**
- If convergence says "strong home" + F5 says "under" + NRFI → suggest SGP: "Home ML + F5 Under + NRFI"
- Flag correlation: "These legs are positively correlated (dominant home pitching = fewer runs = NRFI)"
- No actual parlay odds calculation needed — just surface the logical combo
- **Cost: Zero. Logic on existing signals.**

---

### 🟡 MEDIUM PRIORITY — Meaningful edge, moderate effort

#### 6. Injury-Aware Adjustments
**Who does it:** BetQL (injury alerts), Action Network (injury news), Outlier (injury integration)  
**What bettors say:** "Most tools that scrape stats don't factor in ballpark effects or... missing some key player news." — Reddit r/EVbetting  
**Why it matters:** A lineup missing its #3 hitter changes everything. We currently ignore injuries entirely.  
**Implementation:**
- MLB API has injury endpoint: `/api/v1/injuries?sportId=1`
- One API call → get all current IL players
- Cross-reference with today's lineups
- Flag: "⚠️ [Team] missing [Player] (IL since 5/20)"
- **Cost: 1 additional API call per run.**

#### 7. Public vs Sharp Money Indicator (Pseudo)
**Who does it:** BetQL (public betting %), Action Network (public/sharp splits), OddsJam (sharp action alerts)  
**What the market says:** Line movement without public money = sharp action. This is the gold signal.  
**Why it matters:** If our model agrees with sharp money (reverse line movement), confidence is maximum.  
**Implementation:**
- We can't get real public betting data without premium subscriptions
- BUT: we can infer it. If the line moves toward the underdog despite the public likely being on the favorite, that's reverse line movement = sharp money
- Compare opening line (if available from Odds API) vs current line
- Flag: "Line moved FROM favorite TO dog = 🦈 possible sharp action"  
- **Cost: Potentially zero if Odds API returns opening lines in our existing call.**

#### 8. Pitcher Workload / Days Rest Tracking
**Who does it:** Nobody does this well — most tools just show season stats  
**What bettors miss:** A pitcher on 4 days rest vs 6 days rest performs differently. A pitcher after a 110-pitch outing is different than after 85 pitches.  
**Why it matters:** This is a gap in the ENTIRE market. Nobody integrates this.  
**Implementation:**
- We already fetch recent team games. Parse to find the starter's last outing date.
- Calculate days rest: "Cole: 5 days rest (last start 5/31, 98 pitches)"
- Adjust F5 quality: >5 days rest = +bonus, <4 days rest = -penalty
- **Cost: Zero extra API calls — derive from existing recent games data.**

#### 9. Weather Impact on Totals (Enhanced)
**Who does it:** HeatCheck HQ (dedicated weather-totals dashboard), ScoresAndOdds  
**What the market says:** HeatCheck publishes research: "How wind direction, temperature, humidity, and altitude impact MLB game totals, home runs, and player props."  
**Why it matters:** We already fetch weather and park factor. But we only use it as a minor signal in convergence. We should surface a clear weather-adjusted total.  
**Implementation:**
- Already have temp, wind speed, wind direction, park factor
- Calculate weather modifier: hot + wind out = +0.5 runs, cold + wind in = -0.5 runs
- Apply to total estimate: "Base Total: 8.0 → Weather-Adjusted: 8.5 (🌬️ wind blowing out 15mph)"
- **Cost: Zero. Data already fetched.**

---

## PART 2: GAPS THE ENTIRE MARKET HAS (Where We Can Be First)

These are things **nobody** does well or at all. If we build them, we have genuine differentiation — not just parity.

### 🏆 GAP 1: Full-Context "Why" Explanation Per Game
**The problem:** Every tool either gives you a black-box grade/pick OR raw data. Nobody writes a human-readable explanation of WHY. ParlaySavant notes: "Most tools that give picks don't explain the why." FantasyLabs says: "If it doesn't explain the why, you're betting blind."  
**Our opportunity:** We have ALL the signals — convergence breakdown, F5 edge, EV, pitcher matchup, platoon, weather, bullpen. We can auto-generate a 2-3 sentence English narrative per game.  
**Example output:**
> "**A+ STRONG Away — Yankees (+125).** Cole's F5 ERA (2.80) dominates Bello's (4.05) giving a 20-point quality edge. 5/6 convergence signals align away with +12.3% EV. Bullpen fresh (18) vs tired (42). Only headwind: home/road splits slightly favor Boston. Kelly suggests $20 on $1000 bankroll."

**Implementation:** Template-based text generation from existing data. Zero API calls. ~50 lines of Python.

### 🏆 GAP 2: "Confidence-Adjusted" Total Estimate
**The problem:** Every tool shows the book total (O/U 8.5). Some show a model total. NOBODY adjusts their total by confidence level — a total estimate with high confidence is very different from one with low confidence.  
**Our opportunity:** We have signal count, agreement %, weather certainty, and pitcher data quality. We can output: "Model Total: 8.7 (HIGH confidence — 5 signals agree, both pitchers have 15+ starts)" vs "Model Total: 7.2 (LOW confidence — one pitcher has 3 starts, weather uncertain)"

### 🏆 GAP 3: "Fade the Public" Signal
**The problem:** BetQL and Action Network show public betting % behind a paywall. Nobody synthesizes it with model disagreement for free.  
**Our opportunity:** When our model strongly disagrees with what the public would likely bet (e.g., public loves the big-name team but our convergence says fade), we flag it.  
**Implementation:** Heuristic — favorites with losing recent trends, bad F5 ERA, tired bullpen = "likely public side." If our model disagrees → "🔄 FADE alert."

### 🏆 GAP 4: Offline-First Progressive Report
**The problem:** Every competitor requires internet. If their server goes down, you get nothing.  
**Our advantage:** We already cache aggressively. We could generate a "stale report" from yesterday's cache even when API is down, flagging data age.  
**Implementation:** Already mostly there with our caching infrastructure.

### 🏆 GAP 5: Pitcher vs Lineup Handedness Matrix (Visual)
**The problem:** Tools show team batting average or platoon edge as a number. Nobody visualizes the actual lineup composition vs pitcher handedness as a clear matrix.  
**Our opportunity:** We already have lineup_lefty_pct, lineup_righty_pct, and pitcher_hand. Display a visual: "R-handed pitcher vs 55% lefty lineup = platoon advantage" with a simple graphic.

---

## PART 3: WHERE COMPETITORS ARE WEAKEST (Their Pain Points = Our Opportunity)

| Competitor Pain Point | Source | Our Advantage |
|---|---|---|
| **"Black box — you trust a model without seeing inputs"** | HeatCheck blog, multiple Reddit threads | Our convergence shows every signal, weight, direction. Full transparency. |
| **"45 minutes of setup per slate defeats the purpose"** | HeatCheck blog | One click. Double-click .bat, report in browser. |
| **"$200/month subscription makes no sense for $200/month bankroll"** | HeatCheck blog | $0. Forever. |
| **"Most trackers are terrible at multi-leg bets"** | Reddit r/arbitragebetting | We don't track bets — we generate the analysis. Stay focused. |
| **"Can't tell if the number I took was good relative to market"** | Reddit r/arbitragebetting | Our EV calculation tells you exactly this. |
| **"Injury news is where I mess up my bets"** | Reddit r/passive_income | Gap we can fill with 1 API call. |
| **"No ballpark effects or weather conditions"** | Reddit r/EVbetting | We already do both. Ahead of the pack. |
| **"Stale data — tools update once in the morning"** | HeatCheck blog | Our cache system + run-on-demand = fresh data every run. |
| **"Limited live streaming / no bet builder"** | Monster.bet reviews | Not our lane. Stay focused on pre-game analysis. |
| **"Tools feel like an AI bot firing picks without context"** | SportsHandle article | Our signal breakdown IS the context. Gap 1 (narrative) makes this bulletproof. |

---

## UPDATED PRIORITY ROADMAP

### Phase 2A — Quick Wins (Zero or near-zero API cost)
| # | Feature | Effort | Impact | API Cost |
|---|---------|--------|--------|----------|
| 1 | **FIP Regression Flags** | 2 hrs | 🔥🔥🔥🔥🔥 | Zero (math on existing data) |
| 2 | **Auto-Narrative ("Why" text)** | 2-3 hrs | 🔥🔥🔥🔥🔥 | Zero |
| 3 | **Run Line Analysis** | 1-2 hrs | 🔥🔥🔥🔥 | Zero (data already fetched) |
| 4 | **Over/Under Total Model** | 2 hrs | 🔥🔥🔥🔥 | Zero |
| 5 | **SGP Correlation Suggestions** | 2 hrs | 🔥🔥🔥 | Zero |

### Phase 2B — Low-Cost
| # | Feature | Effort | Impact | API Cost |
|---|---------|--------|--------|----------|
| 6 | **Prediction History Log** | 3-4 hrs | 🔥🔥🔥🔥🔥 | 1 call/day |
| 7 | **Injury Flags** | 2 hrs | 🔥🔥🔥🔥 | 1 call/run |
| 8 | **Pitcher Days Rest** | 1-2 hrs | 🔥🔥🔥 | Zero (existing data) |
| 9 | **Enhanced Weather-Adjusted Total** | 1 hr | 🔥🔥🔥 | Zero |

### Phase 3 — Bigger Lifts (From Original Roadmap, Updated)
| # | Feature | Effort | Impact | API Cost |
|---|---------|--------|--------|----------|
| 10 | **Player Prop Engine** | 6-8 hrs | 🔥🔥🔥🔥🔥 | Moderate |
| 11 | **Statcast/xERA Integration** | 4-6 hrs | 🔥🔥🔥🔥 | 1 scrape/day |
| 12 | **Parlay Builder with Fair Odds** | 4-5 hrs | 🔥🔥🔥 | Zero |

---

## BOTTOM LINE

After Phase 1, we're no longer a "cool project." We're a free tool with EV, grades, sizing, and NRFI that competes with $20-50/month subscriptions.

**The biggest remaining gaps:**
1. **No track record** — Start logging today. This is existential for credibility.
2. **No regression flags** — Surface ERA lies. FIP exposes it. We can calculate it from data we already have.
3. **No narrative** — We show the data but don't tell the story. Every reviewer says "if it doesn't explain the why, you're betting blind."
4. **No totals model** — We're sitting on all the ingredients (F5 total, park factor, weather, bullpen) and not combining them.
5. **No run line analysis** — We fetch spread data and throw it away.

**The market's biggest weakness is transparency.** Every competitor is either a black box (Monster.bet, BetQL, Leans.ai) or requires expensive subscriptions (OddsJam, Unabated). We are the only free, transparent, full-context MLB analysis tool in existence. The narrative feature would make that unassailable.

**Phase 2A costs zero API calls and ~10 hours of work.** Five features, five competitive leaps, zero dollars.

---

*Updated analysis based on 30+ sources including: Monster.bet, OddsJam, Unabated, BetQL, Action Network, HeatCheck HQ, Outlier, Rithmm, Dimers, FanGraphs, ParlaySavant, Leans.ai, SportBot AI, Oddible, HyperPicks, PickLabs, Pikkit, BetStamp, WinnersAndWhiners, Props Optimizer, ScoresAndOdds, VegasInsider, BaseballBible, mlbprediction.com, FantasyLabs, Reddit (r/sportsbook, r/EVbetting, r/arbitragebetting, r/sportsbetting, r/baseball)*
