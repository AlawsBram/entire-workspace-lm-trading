# BACKTEST-QUEUE.md — day-one test order (each ≤1 day, each pre-registered)

Rules: every queue item ends in PASS/FAIL numbers written back to IDEAS-BOARD.md and
GOAL-MATH.md §3. Nothing trades on a ★ rating. The welded gate (gate_pass.json →
bot lock) applies to ANY idea that ever wants live money, not just maker.

## Q1 — W1 weather ensemble bucket EV  ← DONE 2026-10-15: **KILL** (EV −$0.69/$1 @θ=0.10, n=240 holdout; crowd Brier 0.140 < model 0.170; 87.5% pairs unpriced-fresh). Memo: w1_backtest/RESULTS-MEMO.md. Survivor pre-registered as W1b (tail-selling).
- Data: Open-Meteo **previous-runs** archive (past GEFS ensemble forecasts, 31 members
  ✓today), realized temps (historical API), market prices (gamma `/prices-history` per
  bucket token; live slugs verified: `highest-temperature-in-<city>-on-<date>`).
- Build: for each settled city-day bucket: ensemble prob at −48h/−24h/−6h leads vs
  market mid/ask at same timestamps; signal = ens_prob − ask.
- Backtest: buy at ask when signal > θ ∈ {0.10, 0.15, 0.20}; hold to resolution.
- Report: n buckets, hit rate, EV per $ staked, Kelly growth/day, capacity (depth at
  signal prices), calibration plot (ens prob vs realized frequency).
- PASS to next stage: EV/$ ≥ +20% at n ≥ 100 buckets AND calibration honest.
- KILL: EV ≤ 0, or ensemble miscalibrated vs realized (then the crowd wasn't dumber
  than the machine and the idea dies with numbers).

## Q2 — C1/C2 lock-in refresh on fresh truth_lab data  ← IN PROGRESS since 2026-10-15 10:14Z
Analyzer: truth_lab/q2_lockin.py (reads truth_lab timelines + retro-settled rounds).
Recorder v2 additions live: top-of-book SIZES (capacity) + daily-market C2 tracker
(Binance 1m-candle open ref via data-api.binance.vision mirror — api.binance.com
451s in this region; daily boundary 12:00 ET, one corpus point per day).
Verdict only at pooled lagging-book n>=100 (~8-10 h of rounds); interim reports labelled INTERIM.
- truth_lab already logs gap_bps + book mids per 5m round; extend recorder config to
  daily crypto markets; re-measure lagging-book win rate and >4bps lock accuracy on
  NEW days; capacity estimate from book depth at signal time.
- PASS: replicates 73% / 100% on held-out new days.

## Q3 — X1 three-price divergence scan (one passive day)
- Synced snapshots: PM 5m/daily crypto + Kalshi twins + HL perp-implied fair.
- Report: disagreement distribution vs fee+spread cost; count of tradeable gaps/day.

## Q4 — X2 resolution-latency sample (50 markets)
- Measure: official-source publish time vs market price reaching 0.99 vs chain
  resolution, across sports/stats/crypto markets; count minutes of buyable lag.

## Q5 — M1 overround live scanner (then history)
- Scan all multi-outcome events for bucket-sum > 1.02 or < 0.98 after fees; log
  frequency and size; history from gamma snapshots if live hits are rare.

## Q6 — W3 / C3 / F1 (second wave, only if Q1–Q5 leave time)
- Kalshi weather twins paired-snapshot diff; macro-market mispricing census;
  smart-wallet next-hour mark study.

---
Cadence: one queue item per day, results memo same day. Owner approves capital only
against a PASS row + the welded gate + sizing rule (worst round ≤1–2% of capital).
