# Polymarket+Kalshi Secrets — index

Captured 2026-10-07. Source thread:
https://www.reddit.com/r/PredictionMarkets/comments/1ubletl/i_spent_a_few_weeks_trying_to_beat_polymarket_ten/
("I spent a few weeks trying to beat Polymarket ten different ways. Every
single one failed. Here's the data." — u/marvmarv2693, ~June 2026)

The post links to a 4-part reproducible series + a code bundle. EVERY linked
piece is saved verbatim in this folder, in reading order:

| # | file | content |
|---|---|---|
| — | `Reddit post - ten ways, every one failed.md` | full post body + FULL comment thread (cross-venue arb methodology, tennis/Bet365 wedge, overround.pro, drift-test design) |
| 0 | `Part 0 - series front door.md` | the front door: series map, update (Kalshi cross-venue test, resolving end-July 2026) |
| 1 | `Part 1 - AI swarm loses to the price.md` | 8-agent MiroFish swarm: Brier 0.38 vs market 0.30; 27¢/run; 29% crash rate; the drama problem |
| 2 | `Part 2 - six ways that all don't work.md` | longshot bias reversed; calibration honest; 0.84 momentum mirage; thin markets sharp; calendar arb = his bug; bot-repo audit |
| 3 | `Part 3 - smart money copytrading.md` | 105,885 wallets → 157; persistence corr 0.035; champions −13.6% OOS; vig 2.7%; opening-noise ~2¢; settlement lag = parking fee |
| 4 | `Part 4 - two more ways.md` | sportsbook-line signal (no product to trade) + passive market-making +4.6% → **−5.5%** after toxicity + sample |
| + | `Code bundle - reproducible study ($19 Gumroad).md` | the shop page: what the $19 bundle contains (we don't need it — annotation inside) |
| + | `YouTube transcript - More Perfect Union - scam expose.md` | critical investigative video, verbatim transcript + extracted claims/numbers + our annotations (regulatory risk, profit concentration, accuracy metrics) |

Part 1's tool: https://github.com (MiroFish project, name as described).
Series home: https://research.marvoproduction-apps.de/can-you-beat-polymarket/

## Headline findings (the numbers that matter)

- 648 liquid markets, Sept 2025–July 2026; only 16.8% resolved YES.
- Longshots ≤0.20: implied 0.73%, ACTUAL 1.15% — underpriced; no FLB.
- 0.90–1.00 bucket: avg 0.982 vs actual 0.9765 — honest to half a percent.
- Momentum 0.8386 = untradeable convergence; honest early version 0.541.
- Thin markets Brier 0.022 vs 0.024 liquid — NOT sloppier.
- AI swarm Brier 0.38 vs market 0.30; one lucky night carried the P&L.
- Smart-money persistence 0.035 (16-wallet pilot ghost: 0.43); champions
  −13.6% OOS; avg trader −2.7% = the vig.
- Opening prices ~2× as noisy — real inefficiency, <2¢, toll 2.7%.
- Settlement-lag discount 0.3–1.7% < round-trip cost.
- Passive MM: +4.6% → −5.5% (−7%+ on large informed fills); 30-min markout
  zero the whole time.
- Open thread: Kalshi-vs-Polymarket cross-venue test, pre-registered,
  resolving end of July 2026.

### From the comment thread (equally important)
- **Cross-venue methodology (author's live snapshot, ~130 paired contracts):**
  naive screen 52% "positive" → almost all resolution mismatches; after
  equivalence filter the gap collapses to **−0.9¢…+1.9¢**, cleanest identical
  pairs negative. THE RULE: gate on resolution-equivalence FIRST (action
  verb + deadline + resolution source = the "resolution triplet"), spread
  second. Jaccard ~0.45 token overlap is a RECALL net only; the nastiest
  phantoms (run-vs-win) have HIGH overlap. 50¢+ cross-venue gap ≈ phantom.
- **Gómez-Cram et al. (Apr 2026):** ~3% of accounts drive essentially all
  price discovery; calibration persistence of those wallets is the cleaner
  (unrun) question vs ROI persistence.
- **Specialist-latency hypothesis (docksbox29 ↔ author, agreed testable):**
  in THIN markets, 2 minutes after a specialist trade captures meaningful
  pre-discovery drift; the agreed measurement: mid drift in the 2 min after
  a suspected-specialist trade, NET OF the spread you'd cross, out of sample.
- **Tennis wedge (norholt1337):** obscure ATP matches priced ~8% off Bet365
  on both sides, ~200k liquidity; counter-claim (Infamous_Dish_4348): esports
  arb died scaling to traditional sports; needs obscure low-liquidity only.
- **overround.pro (C_Pointers_Are_Great):** 6/9 quarterly windows alert
  wallets beat prices paid (CIs clear of zero); all 9 cutoffs rank-monotone;
  top wallets' mid-range trades +3.6 points vs price paid. A measurable
  minority, a few cents, not every quarter.
- **Author's data confession:** structure tests used reference snapshots +
  flat 2%; NO true live-order-book simulation ("a real gap and the honest
  next step"); approximations flattered strategies and edges died anyway;
  "granularity decided it twice, and both times it killed an edge, never
  created one."
- **Used-Swimming-5875:** 0.06-edge bot eaten by Kelly+fees; Poly+Kalshi
  lattice cross-arb same result; "the only thing I can see is figure out how
  to be a maker. Everybody else is bait."
- **aenews (sharp):** real trading = +EV per trade + fractional Kelly +
  opportunistic news reaction; never a single "strategy".

## Our annotations (cross-referenced against our measured stack)

1. **Confirms our house rules.** Independent, pre-registered confirmation
   that famous edges are dead on .com liquid markets; same verdict as our
   REALITY-CHECK in different units (his 0.43-vs-0.035 ghost = our
   1-in-65,536 ladder math).
2. **Open-book maker: his failure defines our gate.** His MM backtest held
   fills to resolution, modeled no rebates, never cancelled. Our design
   differs on exactly those three axes (GTD+pull-on-move vs his toxicity
   losses; BRTI-skewed quotes; 20–25% rebate stream). His −5.5% is the prior
   maker_sim must beat before live size — OPEN-BOOK-MAKER.md §8 gate stands.
3. **Settlement-lag carry survives his critique.** His toll assumes a round
   trip; our weather carry enters once (~0.05¢ taker fee at 0.99) and holds
   to resolution. His 0.3–1.7% discount vs our sub-cent entry quantifies the
   edge instead of killing it.
4. **His 2¢ opening-noise inefficiency is our opening-straddle window.** He
   pays the 2.7% taker toll to reach it; we enter post-only (zero maker fees
   + rebates). That asymmetry is the thesis.
5. **Thin weather markets: static laziness is dead, dynamic repricing is
   untested.** His result kills "lazy pricing"; our NWS-update lag-table
   approach is an information-event edge his study never measured. The lag
   table will give the number.
6. **Copytrading dead (0.035).** Strategy #9 (wallet coattails) = low prior;
   if revived, activity-selected split-half persistence is the only honest
   gate.
7. **AI-forecasting swarm dead vs the price (0.38 vs 0.30)** — any plan that
   says "ask an AI swarm" loses to the screen; our stack uses AI for
   measurement, the market for probability.
8. **Cross-venue Kalshi/Polymarket arb** stays on the watchlist; add a
   regime_watch source if/when his July-2026 result or our own access lands.
   If built, import his pipeline order: equivalence triplet FIRST, spread
   second; treat Jaccard as recall-only.
9. **Our US-vs-.com round "arb" is basis, not arb.** His equivalence lesson
   applies to our own cross-venue idea: .com rounds settle on Chainlink TWAP,
   US rounds on BRTI — different resolution sources = non-fungible contracts.
   Any spread between them is a basis-risk position, priced like one; the
   OPEN-BOOK/lock-in edges must be evaluated WITHIN each venue's own oracle,
   exactly as our three-oracle table already does.
10. **The drift test they agreed on = what we already built.** "Mid drift in
    the 2 minutes after a suspected-specialist trade in thin markets, net of
    spread, out of sample" is precisely our weather lag table (NWS update →
    bucket drift at t+0/10/60/300s) and the recorder's opening-burst capture.
    Our stack implements the methodology the thread called "the cleanest
    question" — run it as designed and keep the out-of-sample discipline.
11. **"Everybody else is bait; be the maker"** (Used-Swimming) and "who
    actually prints runs latency arb / calibration on illiquid / holds
    resolution risk" (PropMarket) independently converge on our house rules:
    maker-side economics, information-event edges, carry — never taker
    prediction bets.
12. **Tennis-vs-Bet365 wedge**: untested single claim with a scaling
    counter-claim; needs a sportsbook account (out of scope). Parked on the
    watchlist; if ever pursued, our US-venue thin sports books are the
    Polymarket leg and the equivalence/obscurity filters apply.
13. **overround.pro's calibration-persistence ranking** is the better
    smart-money gate if strategy #9 (wallet coattails) is ever revived:
    rank by calibration persistence among price-discovery wallets, not ROI;
    expect a few cents, not every quarter.
