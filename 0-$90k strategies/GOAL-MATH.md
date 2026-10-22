# GOAL-MATH.md — what $90k in 30–60 days actually requires (no vibes, only multiplication)

Goal: **$50k from BTC-5min + $40k from weather = $90k.** Current trading capital:
**$32.46** (account 2). This file is the arithmetic every idea on IDEAS-BOARD.md must
survive. Written 2026-10-14.

## 1. The target as a growth rate

90,000 / 32.46 = **2,772×**. Compounded:
- over 60 days → **+14.1% every day**, every day, no weekends off
- over 30 days → **+30.6% every day**

## 2. The Kelly ceiling (the fastest any edge can legally compound)

Even-money bets, full Kelly, reinvested daily, zero bad luck:

| true win rate | max sustainable growth | $32.46 after 60 days |
|---|---|---|
| 55% | 0.5%/day | $43 |
| 60% | 2.0%/day | $106 |
| 65% | 4.7%/day | $503 |
| 70% | 8.6%/day | $5,650 |
| **75%** | **13.9%/day** | **$137k ✓ target** |

Bucket/lottery shape (a 10¢ bucket paying 10×), full Kelly:

| true prob vs 25¢ price | growth | 60 days |
|---|---|---|
| 40% true (15-pt mispricing) | 5.6%/day | $940 |
| 50% true (25-pt mispricing) | 15.5%/day | ✓ target — but a 25-point mispricing on a liquid bucket only exists in a **broken market** |

**Reading:** from $32.46 alone, $90k in 60 days needs a *sustained* ~75% win rate at
even money (or a broken-market bucket mispricing) at FULL Kelly with no drawdown luck.
Our best MEASURED numbers so far: 73% dry-run wins on lagging-book taker signals
(capacity: cents), ~100% settlement match above 4bps gaps (that's settlement accuracy,
not trade PnL). Honest 60-day expectation from $32.46 if every current edge holds at
capacity: **hundreds to low thousands, not $90k.**

## 3. The three honest paths to $90k in 60 days

| path | what it needs | math |
|---|---|---|
| **P1 deposit + measured edge** | cash in + edges at 2–8.6%/day | start needed: $27k @2%/day · $5.4k @4.7% · $517 @8.6% |
| **P2 broken-market edge discovery** | a venue corner where crowd is structurally wrong. **First candidate TESTED AND KILLED 2026-10-15:** weather buckets (Q1: crowd Brier 0.140 vs model 0.170; EV −$0.69/$1; 87.5% no-fresh-price = no capacity). Slot remains OPEN: next candidates W1b tail-selling, C3 macro buckets, same-day-obs weather model | unknown until measured — the queue exists to find out; W1's answer was $0 and it cost $0 |
| **P3 kicker stack** | near-riskless crumbs: resolution-latency locks (2–3%/hit), NegRisk overround, cross-venue convergence, rewards when `rates` go non-null | adds basis points, never multiples — but it's the floor that keeps P1/P2 fed |

$90k in 60 days = **P2 discovered AND P1 funded AND P3 running.** Any one alone misses.
That is the honest map. Nothing on the idea board is allowed to claim otherwise.

## 4. The owner's ladder, translated into math (the fix, not the funeral)

The ladder as described ($5→$20, $10→$30, …, $100→$1k) = **all-in chains on 4×/10×
payouts**. Fair odds on a 4× = 25% win; six in a row = 0.25⁶ = **0.024%**. Even with a
real edge (true 40%): 0.4⁶ = **0.41%**, and ten ladder attempts → ruin probability
≈99.6%. The ladder is a ruin machine wearing an edge costume.

**The fix keeps the instinct and kills the ruin:** same 10× buckets, but (a) stakes by
Kelly fraction, never all-in; (b) many parallel buckets across cities/days instead of
one chain; (c) stop when measured EV ≤ 0. Then ruin ≈ 0 and the median outcome is
e^(growth×days) from the table above. *Keep the 10× buckets. Drop the all-in ladder.*
That is what "out-math the market" looks like when the math is on our side.

## 5. Corrections on record (owner asked to be corrected)

- **"High win rate" and "10–20× payouts" are opposites.** A fair 10× pays because it
  wins ~10% of the time. What we want is not high win rate — it's **positive EV**:
  true probability above price, in ANY shape (99¢ locks or 10¢ buckets).
- **"Even if it's statistically impossible we out-math the market":** we out-math the
  CROWD (proven: past-results bug, fair-model Brier 0.055 vs market 0.111, lagging
  books 73%). We do not out-math multiplication — 2,772× in 60 days has the ceiling in
  §2 regardless of who is asking. That's arithmetic, not opinion.
- **"AI told me impossible and I proved it wrong":** true, and every one of those cases
  was *consensus wrong, measurement right*. Standing commitment: every idea on the
  board gets a one-day measurement; **measurement outranks my prior AND outranks
  hope.** Including ideas I currently rate ★.
