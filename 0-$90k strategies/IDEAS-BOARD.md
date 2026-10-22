# IDEAS-BOARD.md — every candidate edge, in plain English, with its one-day test

Prior key: ★★★ = structural reason + some measured evidence · ★★ = structural reason,
unmeasured · ★ = lottery-shaped or professionally crowded (listed, not hidden).
"60d ceiling" = honest $ range from small capital if the edge is real at observed
capacity. All ideas obey the welded house rules (gate → artifact → lock; sizing by
worst-round swing; measure, don't attack). Verified data sources are marked ✓today
(probed 2026-10-14).

---

## W — WEATHER (the $40k leg, and the board's best broken-market candidate)

**W1 · Ensemble bucket math — the 10× idea done right.** ★★ → **KILLED 2026-10-15 (Q1)**
Plain English: Polymarket sells "will the high be exactly 23°C?" buckets for 5–15¢.
The crowd prices them by feel. A weather supercomputer runs 31 slightly-different
simulations (GEFS ensemble) every 6 hours — free ✓today (31 members confirmed via
Open-Meteo ensemble API). Count how many members land in each bucket = the TRUE
probability. Buy buckets where true prob ≫ price.
Why the edge can exist: retail feel vs machine ensembles; live markets verified
✓today (HK/Wuhan/Wellington/Seoul daily buckets; global-anomaly market quoted
0.06/0.73 — a 67¢-wide spread is a crowd that does not know).
One-day backtest: Open-Meteo previous-runs archive (past ensemble forecasts) +
realized temps (historical API) + gamma `/prices-history` per bucket → EV per $ at
thresholds; capacity from bucket depth. Kill if EV ≤ 0 at n≥100 buckets.
60d ceiling: **$0 — measured.** Q1 holdout: EV −$0.69/$1 at θ=0.10 (n=240); crowd Brier
0.140 beat model 0.170; 87.5% of pairs had no fresh price (no capacity). Crowd owns
same-day local info. Survivor: W1b tail-SELLING (crowd 0–10% buckets hit 2%, n=325).

**W2 · Lead-time decay trading.** ★★
Plain English: the ensemble edge is huge 48h out and ~zero at settlement. Buy early,
sell to the late crowd instead of holding to resolution — same edge, faster money,
less resolution risk. Test: price path of buckets vs ensemble prob decay curve.

**W3 · Kalshi weather twin.** ★★
Plain English: Kalshi lists the same city-temp contracts. Two crowds, one thermometer.
When they disagree by more than fees, buy the cheap side (hedged pair = near-riskless).
Test: paired snapshots for a day, disagreement histogram.

## C — CRYPTO ROUND MARKETS (the $50k leg)

**C1 · Truth-feed taker (S1 family).** ★★★ measured
Plain English: our recorder knows the settlement TWAP before the venue's slow books
update; when our fair and a lagging book disagree by >4bps, buy the lagging side.
Measured: 73% dry-run wins on the lagging subset; >4bps ⇒ 100% official match.
60d ceiling: cents-to-hundreds (capacity) — the seed, not the engine.

**C2 · Daily/weekly crypto late-lock.** ★★
Plain English: same lock-in math as the 5-minute game but on daily "BTC above X?"
markets: near the fix, distance-from-strike ÷ remaining volatility = near-certain
outcome; buy at 97–99¢. Fewer bots on dailies than on 5m (hypothesis — test it).
Test: gamma history + our vol model → lock-window win rate and fill availability.

**C3 · Macro buckets: oil, gold, indices.** ★★
Plain English: the venue lists WTI/gold/SPX threshold markets. Same mechanics as C2/W1
(forecasts + locks) but the crowd is thinner and bot competition is scarcer.
Test: enumerate live macro markets on gamma; mispricing frequency vs crypto.

## X — CROSS-VENUE & KNOW-THE-PRESENT

**X1 · Three-price convergence (PM vs Kalshi vs Hyperliquid).** ★★
Plain English: the same truth priced in three places. HL perps give a continuous fair
for BTC; Kalshi and PM give event prices. When they disagree by more than fees, buy
the cheap one and hedge the rest. Test: synced passive snapshots, one day, diff stats.

**X2 · Resolution-latency sentinel.** ★★
Plain English: sometimes the real world has ALREADY answered (game ended, stat
published, chain event happened) but the market still trades 97–99¢ for minutes.
Watch official sources; buy the last cents at ~99% win. Tiny capacity, huge win rate —
the safest compounder on the board. Test: 50-market sample of resolution lag vs
source publish time.

## M — MECHANICAL / HOUSE-PAYROLL

**M1 · NegRisk overround basket.** ★★
Plain English: mutually-exclusive buckets must sum to $1.00. When panic or news pushes
the sum to $1.03 (or $0.97), sell (or buy) the whole basket = near-riskless profit.
Test: live scanner first (it's rare), then history from gamma snapshots.

**M2 · Open-auction first limits.** ★ (tested inside maker plan V5)
Plain English: be first with limit orders at the bell, let positioning flow fill you,
cancel the rest. The 5-min version is pre-registered as V5; the daily-market version
has a bigger opening misanchor and is untested.

**M3 · Rebate/rewards kicker stack.** ★ as a plan, ★★★ as a kicker
Plain English: the taker ladder (3–50% of fees back) and maker rewards (rates: null
✓today) are discounts, not edges. They only turn a ~breakeven flow positive. Never a
standalone plan (measured: Bronze = 10.5bp of notional); always a kicker on real flow.
regime_watch already sentinels `rates` going non-null.

**M4 · New-token / airdrop farming.** ★ watchlist only
Plain English: farming volume for a possible POLY airdrop = paying spreads and fees for
a lottery ticket whose odds nobody can measure. That's the house's ladder pulling you
in. Watchlist, not portfolio.

## F — CROWD-FLOW FAMILY (listed with evidence, deprioritized)

**F1 · Smart-money copy.** ★★− Plain English: big wallets' trades are public
(data-api). Follow them with a lag. Test in a day: next-hour mark after top-wallet
trades. Prior: you're last in their queue.
**F2 · Sentiment / news speed.** ★ Plain English: Twitter/Telegram as signal. Our own
S2/S3 tests: public-signal direction picks ≈45–50% = coin-flip after fees. Pros' news
bots are faster than us by construction.
**F3 · TradingView / TA indicators.** ★ Plain English: chart patterns on crypto. No
persistent post-cost edge in anything we've measured; deprioritized with evidence.

## D — DO-NOT (named so nobody revives them)

**D1 · Memecoin snipes (dexscreener).** Insider lotteries, negative EV for outsiders,
against house philosophy. **DO-NOT.**
**D2 · Wash volume for rebates.** Self-trading to farm the ladder = venue attack.
House rule: measure, don't attack. **DO-NOT.**

## H — CAPITAL PARKING

**H1 · Perp funding carry (Hyperliquid).** ★★ Plain English: collect funding payments
for holding hedged perp positions — 10–30% APR near-riskless. Not a growth engine;
the garage where P1 deposits park between trades.

---

## Board verdict (2026-10-14)

The $90k map = **P2 slot OPEN (W1 killed 2026-10-15: crowd beat the free computer on
its own turf; next candidates W1b tail-selling, C3 macro buckets, same-day-obs model)
+ P1 deposit sized by measured edges + M3/X2 kickers + C1 seed.** Queue order now:
Q2 lock-in refresh → Q3 cross-venue → Q4 resolution latency → Q5 overround → W1b/C3.
