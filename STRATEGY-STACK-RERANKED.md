# STRATEGY STACK — RE-RANKED BY VENUE-INCENTIVE ALIGNMENT
*2026-09-25 · supersedes the original S1–S10 ordering in BTC-5m-15m-POLYMARKET-10-STRATEGIES.MD*

## Why we re-ranked
Three facts, all verified this session:

1. **The venue monetizes taker churn.** Fees (up to ~1.75% at 50¢) apply only to
   the fastest, most compulsive markets; hourly markets are fee-free. Makers pay
   **zero** and receive daily USDC rebates funded by those taker fees (20% of
   crypto taker fees) plus rewards for resting liquidity.
2. **The venue edits its own physics, sometimes silently.** Taker fees introduced
   Jan–Mar 2026; the taker-delay speed bump was removed in Feb 2026 *without
   announcement*; settlement windows changed twice (Aug 2025). The docs now warn
   against hardcoding fees because they keep changing. Live proof in our own data:
   current CLOB market objects show `seconds_delay = 0` — the speed bump is gone.
3. **Big winners trigger rule edits.** The $800K 5-minute-market trader and your
   own 6x run are the same phenomenon: an edge real under one rule set, gone after
   the venue changed that rule set. Whether deliberate or incentive-driven doesn't
   matter — the practical fact is: **the rules are a variable, not a constant.**

Therefore the ranking criterion flips: not "which edge looks biggest," but
**"which edges does the venue pay you to run, which does it tolerate, and which
does it hunt?"**

## Scoring rubric (0–3 each, max 15)
- **A — Incentive alignment:** does the venue pay you (rebates/rewards) to do this?
- **R — Rule-change resilience:** survives a typical changelog (adaptive), or dies in one line?
- **V — Visibility headroom:** how big can you scale before the house notices/cares?
- **E — Evidence velocity:** how fast can RBI produce proof on your VPS?
- **C — Capital efficiency:** small bankroll sufficient?

## The new order

| # | Strategy | A | R | V | E | C | Σ | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **S3+ S6 — MAKER FAMILY: two-sided scalping + rebate/spread harvesting** | 3 | 2 | 3 | 2 | 3 | **13** | **Top of queue.** The house payroll: zero fees, 20% taker-fee rebate in crypto, liquidity rewards. Adaptive quoting survives fee edits. The whales are almost all makers for exactly this reason. |
| 2 | **S10 — Rewards-program farming** (rest size/spread for daily rewards) | 3 | 2 | 3 | 2 | 2 | **12** | The venue literally pays you to be present. Rewards config is what the regime watcher diffs. Overlaps the maker family — run as one system. |
| 3 | **S9 — Wallet coattails** | 2 | 2 | 3 | 2 | 3 | **12** | Venue-supplied feed (`/api/poly/profitable-traders` via Moon Dev), aligned use. Needs the endpoint wired to VPS. |
| 4 | **S1 — TWAP Lock-In** | 1 | 1 | 2 | 3 | 3 | **10** | Keep running at $10 (incubation already approved, arbiter proven 70/70) but treat it as **tolerated mechanical crumbs with an expiry date** — the venue already changed the window twice. Never scale on hope; scale only on live match. |
| 5 | **S2 — Open-print displacement** | 1 | 1 | 2 | 2 | 3 | **9** | Same class as S1, evidence still collecting. Ride-along, no extra infra. |
| 6 | **S4 — Cascade continuation** | 1 | 1 | 2 | 1 | 3 | **8** | Needs Moon Dev liq feed on VPS; taker edge, fragile to venue tuning. |
| 7 | **S5 — Vol breakout** | 1 | 1 | 2 | 1 | 3 | **8** | Taker; needs 1s tape accumulation first. |
| 8 | **S7 — News calibration** | 1 | 2 | 3 | 1 | 3 | **10→8** | Slow evidence loop; keep as background research only. |
| 9 | **S8 — Cross-market hedge / complement arb** | 0 | 0 | 2 | 1 | 2 | **5** | Deprioritized: fees were explicitly engineered to kill thin complement spreads (a 2¢ gross edge is ~0 on crypto fees). |
| — | **Latency sniping / speed-bump racing** | — | — | — | — | — | **BANNED** | Do not build. The venue actively hunts this class; the speed bump's removal shows it controls that axis absolutely. |

## What changes operationally
1. **Incubation queue:** maker family (S3+S6+S10 as one quoting system) → S9 → then
   everything else. S1 continues its $10 live incubation in parallel — it's already
   running and costs nothing extra; it just stops being "the plan."
2. **Regime watch is mandatory infrastructure**, not optional: `regime_watch.tar.gz`
   runs next to the stack on the VPS. REGIME-CHANGE on fees/feeSchedule/
   seconds_delay/tick/settlement ⇒ `touch KILL` on the trader first, read the diff,
   then decide. (Already written into S1-PLAYBOOK.md.)
3. **Stay small, compound fast.** Size below the house's attention threshold is part
   of the edge. Your $10→6x was the right shape; the 800K trader's failure mode was
   becoming visible to a rule-maker.
4. **Every edge is priced as perishable.** Plan on weeks-to-months of harvest per
   edge, not years. The watcher buys us reaction time; the maker alignment buys us
   durability.

## Next build (already specified)
**Maker quoting simulator** — the RBI "I" step for the promoted family:
- Inputs: our own CLOB book snapshots (already collectable), rewards config
  (min_size=200, max_spread=3.5¢ on sampled markets), zero maker fee + 20% rebate.
- Models: fill probability vs queue position, adverse selection (who lifts us and
  why), spread capture vs inventory risk over 5m horizons.
- Output: paper-trade PnL + rebate accounting + adverse-selection metric,
  same gate discipline as S1 (≥50 rounds simulated, ≥90% model-certified)
  before a maker mode in the trader ever touches real money.
