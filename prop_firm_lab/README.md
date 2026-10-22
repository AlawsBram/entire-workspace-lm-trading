# PROP FIRM LAB — rule-replay checker for prop-firm evaluations

Built 2026-10-14 after the Moon Dev prop-firm stream (transcript archived in
`Prop Firm Bots/`). Our version of his `passed_test.py`: take ANY strategy's
PnL stream and answer one question —

> **Sized so its worst round fits inside the floors, does this PnL shape reach
> +9% before the 3% daily or 3% max-drawdown floor kills it?**

## The rules being simulated (transcript values, all configurable)

- $50,000 SIMULATION account, fee $245 (also models $50/10k, $125/25k, $1k/100k via flags)
- **PASS** = equity ≥ +9%. No time limit.
- **DEATH** = daily loss ≥ 3% of that day's starting equity (UTC days), OR
  equity ≤ initial × 0.97 (STATIC floor — does not trail up with profit)
- Fail → buy another attempt. Pass → funded sim, 80/20 split, balance resets.

## How scoring works

1. Per-round PnL earned on the strategy's own tiny capital D becomes a return
   r = pnl/D.
2. `--auto-scale` sizes r onto the prop account so the **worst single round**
   moves the account at most `--worst-round-cap` (default 1%) — the honest
   sizing a prop trader must use to respect the floors.
3. Replay chronologically; every PASS/DEATH starts a fresh attempt; end of
   data = STALL. Reports pass/death/stall counts, worst daily, worst DD, and
   P(≥1 pass in N attempts) for the multi-buy economics.

## Run

```bash
python3 passed_test.py --maker-csv ../maker_lab/sim_rounds.csv --auto-scale \
        --json-out results/maker_prop_score.json
python3 passed_test.py --s1-csv ../s1_harness/backtest_s1_signals.csv --auto-scale \
        --json-out results/s1_prop_score.json
python3 passed_test.py --csv ANY.csv --ts-col ts --pnl-col pnl --capital 100 --auto-scale
```

## First scores (2026-10-14) — READ THE CAVEATS

| Strategy | Data | Auto-scale | Result | Detail |
|---|---|---|---|---|
| OPEN-BOOK-MAKER (sim) | 5 rounds | 0.0064 | **STALL** @ $49,409 (−1.2%) | too few rounds; early drift slightly negative |
| S1 taker signals | 45 signals / 11.5h | 0.0001 | **STALL** @ $53,457 (**+6.9%** of the 9% target) | worst daily 0.02% — nowhere near floors |

**Caveats (do not skip):**
1. **INSUFFICIENT DATA.** Both stall; neither passed nor died. Re-run at the
   ≥200-round gate (both stacks produce that within days once recording runs).
2. **GIGO.** The checker scores SHAPE, not truth. S1's signals come from the
   synthetic-book backtest that our own `s1_harness/backtest_report.md`
   partially demolished (the +0.435/share headline is a proxy artifact; only
   the lagging-book subset may be real). A 6.9% climb on artifact data is an
   artifact climb.
3. S1's auto-scale (0.0001) shows WHY: its worst round loses ~107% of deployed
   capital (2¢ deep-longshot bets), so prop-safe sizing is a rounding error.
   High per-trade variance strategies are structurally bad prop-firm citizens
   unless the payoff shape changes.
4. The checker assumes the prop firm pays and rules don't change — see
   `VENUE-TRUST-MODEL.md`; prop firms are the MOST regime-prone venue class
   (bot tolerance can vanish overnight, and the streamer already suspects it).

## Why this lab exists

- If any of our streams ever shows a real, floor-safe climb to +9%, a $245
  attempt is a capped-downside option on 80% of uncapped sim profits — the
  "built-in edge" shape from the transcript (rules punish variance, not
  slowness; there's no clock).
- It also flips strategy design the way it did in the stream: at prop venues,
  **pass-rate beats raw return**. Ranking by this checker is a different
  ranking than ranking by PnL — that's the point.
- Same discipline as everything else here: measure first, pay fees never
  (until a gate prints PASS on ≥200 settled rounds).

## Next steps

1. Re-run both scores when sim_rounds.csv passes 200 settled rounds.
2. Feed it the weather-carry PnL stream when that recorder produces one.
3. Only after a strategy shows PASS (not stall) on real-shaped data: consider
   one $245 attempt as an experiment with capped downside — owner approval,
   as always.
