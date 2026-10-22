# Q1 RESULTS MEMO — interpretation + next wave (2026-10-15)

## What was tested
434 settled city-day events (14 cities, 2026-09-14→10-14). Prob model = calibrated
deterministic GFS forecasts at 4 leads (L0 same-day short-lead stitched archive,
L1/L2/L3 = Previous-Runs 24/48/72 h offsets), bias+sigma fit on first 60% of days per
(city, lead), holdout = last 40%. Market price = CLOB prices-history at the lead
timestamp, carry-forward ≤24 h, +2¢ slippage. Trades: buy bucket YES when
prob − ask > θ ∈ {0.10, 0.15, 0.20}, hold to resolution.

## Verdict: KILL (pre-registered criteria)
- θ=0.10: n=240 holdout buys, hit 6.2%, **EV −$0.69 per $1** (θ=0.20: −$0.78).
- Brier holdout: **crowd 0.1401 beats our model 0.1697.**
- The kill shot: our model is calibrated IN AGGREGATE (prob bins 10/14/26/34/43/47%
  hit 10/14/26/34/43/47%) but gets crushed exactly where it DISAGREES with the crowd
  (mean prob 0.27 vs mean ask 0.09 → hit 6.2%). That signature means the crowd holds
  information our 00Z-run + bias model lacks (same-day local observations, station
  micro-behavior). On disagreement, the retail crowd is the smarter player.
- Capacity finding independent of edge: **87.5% of candidate (bucket, lead) pairs had
  no fresh price within 24 h** — these markets barely trade before resolution day.
  The 67¢-wide spreads seen on live markets are illiquid young quotes, not tradable
  mispricings. Even a real edge here would have ~zero room to deploy.

## What survives (honest scraps)
1. Crowd OVERPRICES extreme tails: price 0–10% buckets hit 2% (n=325). The inverse
   shape — SELLing overpriced tail buckets (buying NO) — is the only positive-EV
   candidate visible in this data. Pre-register as **W1b** if owner wants: sell YES
   tails when price ≥ 2× our prob, Kelly-fractional, negative-skew risk budgeted
   (one hit ≈ −20 wins), capacity same thin-market caveat.
2. The probability machinery (fetch → calibrate → price-align → holdout) is built and
   reusable for W2/W3 and for any future forecast-vs-crowd test (macro buckets C3).
3. L0/L1/L2/L3 lead infrastructure verified: Previous-Runs API works, prices-history
   works, resolutions clean.

## Board consequences
- W1 (buy mispriced buckets): **KILLED** at 30-day/14-city scale. The "broken market"
  slot in GOAL-MATH P2 is OPEN again — next candidates: C3 macro buckets (thinner
  crowd?), W1b tail-selling, or a same-day-observations model (feed live local obs
  into the model so OUR info set matches the crowd's — that is the only version of W1
   that attacks the actual loss mechanism).
- No capital was risked. The system worked exactly as welded: measurement first,
  verdict by pre-registered numbers, $0 lost.
