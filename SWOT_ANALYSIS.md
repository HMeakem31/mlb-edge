# MLB Edge — SWOT Analysis + Outside-the-Box Growth Ideas
**Date:** June 5, 2026

---

## STRENGTHS (What we do that nobody else combines)

1. **22 signals synthesized per game** — no other free tool combines weather physics, umpire analytics, Statcast xERA, FIP regression, F5, RISP splits, defense, stolen base impact, shadow analysis, convergence scoring, EV, Kelly, NRFI, K props, hit props, SGP, and auto-narrative in one view
2. **Physics-based weather** — actual air density calculation, cosine wind projection against stadium azimuth. Nobody else does the math
3. **68% NRFI backtest** — our best-performing market, above industry standard
4. **59% moneyline at A/A+ confidence** — strong high-conviction picks with 67% hit rate
5. **Full transparency** — every signal, weight, direction, and strength is visible. No black boxes
6. **Zero friction, zero cost** — download, double-click, get a full analytical report in 60-90 seconds
7. **Auto-narrative** — plain English explanation of WHY for every pick. Unique among free tools
8. **Statcast xERA integration** — 664 pitchers with expected stats from Baseball Savant, no signup

## WEAKNESSES (Where we honestly fall short)

1. **MLB only** — no NBA, NFL, NHL. Limits total addressable market
2. **No verified long-term track record** — only 3-day backtest. Credibility gap
3. **No bet tracking** — can't log results, measure CLV, or show P&L over time
4. **Desktop-only HTML** — no mobile app, no responsive dashboard
5. **Static report** — runs once, generates static file. No real-time updates
6. **No odds comparison** — single book (ESPN/DraftKings). Can't line-shop
7. **Player props are shallow** — we identify regression candidates but don't project specific lines
8. **No contrarian/public money indicator** — we don't know which side the public is on
9. **No pitcher workload tracking** — days rest, pitch count trends, fatigue over starts
10. **No lineup confirmation** — we analyze rosters but don't confirm today's actual lineup

## OPPORTUNITIES (Market gaps we can exploit)

### 🔥 HIGH IMPACT — NOBODY DOES THESE WELL

#### 1. Travel + Fatigue Model
**The gap:** Research shows teams with 2+ days rest perform measurably better against fatigued opponents. Baseball Prospectus found that the number of games played in the last 7/14/21 days has "across-the-board negative effect on all sorts of hits." Yet NO betting tool systematically tracks team travel schedules and rest days.
**What we'd build:** Track each team's last game date, travel distance (we have stadium coordinates!), and games in last 7 days. Flag: "NYY: 3rd game in 3 cities in 4 days — fatigue risk" or "SEA: 2 days rest + home — fresh."
**Data source:** Already have all game dates from MLB schedule API. Calculate travel miles from STADIUM_COORDS. ZERO new API calls.

#### 2. Returning-From-Injury Pitcher Pricing
**The gap:** "The market underprices uncertainty after IL stints, opening with conservative totals that move late. First-time call-ups: public bettors fade rookies; sharps look at minor-league xERA." (DeuceCracked, May 2026)
**What we'd build:** MLB API has an injuries endpoint. 1 call gets all current IL players. Cross-reference with today's starters. Flag: "⚠️ First start back from IL" or "🆕 MLB debut / call-up."
**Data source:** `statsapi.mlb.com/api/v1/injuries?sportId=1` — free, no key, 1 call.

#### 3. "Fade the Public" Score
**The gap:** "Public bettors love betting favorites and overs. Sportsbooks shade opening lines to account for public money. This has historically created value on underdogs and unders." (SportsInsights) "Road underdogs at +110 to +160 have been a consistent value spot." (DeuceCracked)
**What we'd build:** Heuristic-based public side detection. Big-name team + home favorite + primetime + high total = likely public side. When our model disagrees → "🔄 FADE THE PUBLIC" flag. No real data needed — it's a structural pattern.
**Data source:** Pure logic on team names, odds, and time slots. ZERO API calls.

#### 4. Pitcher Velocity Trend Tracking
**The gap:** "Velocity gains of 1 mph or more, K% above 28%, and swinging-strike rate above 13% are the primary signals for pitcher strikeout props." (ParlaySavant) A pitcher whose velocity is trending up/down over recent starts is a leading indicator the market often misses.
**What we'd build:** Track pitcher velo from Statcast search (last 3 starts). Flag: "Cole: velo +0.8mph over last 3 starts → K prop value" or "Bello: velo -1.2mph → fade."
**Data source:** Baseball Savant CSV per-pitcher or game-level. One additional CSV call, cacheable.

#### 5. Role Change Detection
**The gap:** "Role changes are the most underrated signal in the prop market. A player moved to leadoff gets more at-bats, more steal opportunities." (ParlaySavant)
**What we'd build:** Track batting order positions from lineup data. Flag when a player moves up in the order vs their season average position.
**Data source:** Already fetch lineups. ZERO new calls.

### 💡 OUTSIDE-THE-BOX IDEAS

#### 6. "Game Script" Probability Model
**Concept:** Instead of just predicting who wins, predict HOW the game plays out. Pitcher duel (low scoring, tight, late drama) vs slugfest (high scoring, volatile, bullpen game) vs blowout (one-sided, starters pulled early). This changes which bets make sense — F5 ML in pitcher duels, full-game ML in blowouts, YRFI + Over in slugfests.
**Implementation:** Combine pitcher quality, bullpen depth, and offensive strength into a "game script" classification. Display as "🎭 Script: Pitcher Duel | Slugfest | Blowout potential."

#### 7. "Regression Radar" Dashboard
**Concept:** A dedicated section showing the top 5 players league-wide whose actual stats most diverge from expected stats. Not per-game — just a daily watchlist. "These players are due for regression (up or down) based on Statcast." It becomes a daily prop hunting ground.
**Implementation:** Already have the Savant data. Sort by |wOBA - xwOBA| gap. Display top 5 each direction.

#### 8. "If This Pitcher Gets Pulled" Scenario
**Concept:** Show what happens to the totals model if the starter is pulled after 4 innings vs 6 innings. "If Cole goes 6 IP: model total 7.8. If pulled after 4 IP: model total 9.4." This helps bettors think about live betting thresholds.
**Implementation:** Two runs of the totals model with different starter IP assumptions. Pure math.

#### 9. "Park + Weather + Ump Triple Stack" Alert
**Concept:** When park factor, weather, AND umpire all point the same direction (all favor scoring or all suppress it), flag it as a rare triple-stack alignment. These are the highest-conviction totals plays.
**Implementation:** Already have all three data points. Just add a detection layer.

#### 10. Daily "Market vs Model" Divergence Scanner
**Concept:** For every game, show our model's win probability next to the book's implied probability. Sort by the largest divergence. The biggest gaps are where the most value lives.
**Implementation:** Already compute model prob and book prob in EV calculation. Just sort and surface the top 3.

#### 11. "Catcher Impact" Factor
**Concept:** The catcher is the most undervalued defensive position in betting analytics. Catcher framing (extra strikes called), pop time (stolen base prevention), and game-calling ability measurably impact scoring. A backup catcher vs the regular starter can swing a game by 0.5+ runs.
**Implementation:** Track catcher framing data from Savant (one additional CSV). Flag: "⚠️ Backup catcher starting — framing impact -0.3 runs."

#### 12. "First Pitch After Travel" Alert
**Concept:** Teams arriving for an away series after a cross-country flight (e.g., SEA → MIA, LAD → BOS) historically underperform in Game 1. The jet lag + time zone change is a real physiological factor nobody prices.
**Implementation:** Calculate time zone difference between previous and current venue from STADIUM_COORDS longitude. Flag: "West→East 3hr timezone shift — Game 1 fatigue."

## THREATS (What could undermine us)

1. **MLB API terms change** — if MLB restricts their free API, our data pipeline breaks
2. **ESPN removes odds from scoreboard** — our lines source disappears
3. **Baseball Savant blocks CSV downloads** — our Statcast source goes away
4. **Market efficiency improves** — as more tools like ours emerge, edges shrink
5. **ABS (robot umps) reduce umpire impact** — our umpire database becomes less relevant (already happening — shadow zone calls down from 2.3% to 1.5%)
6. **Competitor goes free** — if HeatCheck or Outlier drops pricing, our cost advantage narrows

---

## PRIORITY RANKING FOR NEXT BUILD

| # | Feature | Effort | Impact | API Cost |
|---|---------|--------|--------|----------|
| 1 | **Travel fatigue model** | 2-3 hrs | 🔥🔥🔥🔥🔥 | Zero (existing data) |
| 2 | **Park+Weather+Ump triple-stack alert** | 1 hr | 🔥🔥🔥🔥 | Zero |
| 3 | **Fade the public heuristic** | 2 hrs | 🔥🔥🔥🔥 | Zero |
| 4 | **Game script classification** | 2-3 hrs | 🔥🔥🔥🔥 | Zero |
| 5 | **Regression radar (top divergences)** | 1-2 hrs | 🔥🔥🔥🔥 | Zero (existing Savant) |
| 6 | **Market vs model divergence sort** | 1 hr | 🔥🔥🔥 | Zero |
| 7 | **Injury/IL status flags** | 2 hrs | 🔥🔥🔥🔥 | 1 API call |
| 8 | **Timezone/jet lag alert** | 1 hr | 🔥🔥🔥 | Zero (existing coords) |
| 9 | **Prediction logging** | 3-4 hrs | 🔥🔥🔥🔥🔥 | 1 call/day |
| 10 | **"Pulled after 4 IP" scenario** | 2 hrs | 🔥🔥🔥 | Zero |

**Total for top 10: ~18 hours, 2 API calls. All free.**
