# MAKER LAB — quoting simulator for the maker family (S3 + S6 + S10)

**Paper mode only. Never places orders. No credentials.**

The re-ranked stack promotes the maker family to the top of the incubation
queue: makers pay zero fees, earn the 20% taker-fee rebate (crypto) and daily
liquidity rewards, and the venue *wants* them there. This lab incubates a
two-sided quoting strategy under the same gate discipline as S1 — 50+ rounds,
20+ fills, positive realized edge, >=90% model certification — before any real
money is considered.

## Components
| file | role |
|---|---|
| `book_recorder.py` | VPS daemon: records 1/s snapshots of the live 5m+15m rounds — Chainlink TWAP/spot, S1-verified fair-value model, full top-5 book. Output: `book_data/YYYY-MM-DD.jsonl` (the replay corpus). |
| `make_strategy.py` | Strategy v1 (pure + testable): quote both sides around fair with 1.5c half-spread, stop in the last 20s/30s (settlement gamma), stay inside the 3.5c rewards spread cap, 200-share quotes (rewards min size), inventory guard at ±400 shares. Fill model: book crossing our resting quote fills with 50% probability (conservative queue haircut). |
| `maker_sim.py --live` | Shadow-trades strategy v1 against the real market, settles each round at official resolution (same gamma polling as the S1 arbiter). Writes `sim_rounds.csv`, `sim_fills.jsonl`, `maker_stats.json`. |
| `maker_sim.py --replay F...` | Runs recorded corpus through the exact same code path. |
| `maker_report.py` | Gate report: PASS/FAIL verdict (see below). |
| `history_backfill.py` | Backfills 7 days of settled rounds from the hidden `/api/past-results` endpoint into `history/` (full-precision open/close; note its `outcome` is a DERIVED field — see findings §4). `--symbol BTC --variant fiveminute\|fifteen --days 7`. |
| `history_backfill_gamma.py` | DEEP backfill: every round since series start (2025-12-18) via the gamma series listing — authoritative outcomes + condition_id, no reference prices. 76,666 × 5m / 27,088 × 15m. |
| `chain_verify.py` | Ground truth: reads the CTF payout vector on Polygon per condition_id (batched RPC, ~0.3s/round). 500-round sample of the deep corpus verified 500/500. |
| `chain_relabel.py` | FULL-corpus on-chain relabel: parallel, resumable (jsonl checkpoint), writes `.relabeled.csv` + change report. Runbook: `instructions.md`. |
| `stratified_chain_audit.py` | The audit that measured per-source error rates by round-gap bucket (findings §4). |
| `deploy/history-refresh.sh` | Daily cron entry: rewrites the 7-day price corpus + incrementally extends the deep outcome corpora (cron line in MASTER-RUNBOOK). |

All history findings + column glossary: `history/HISTORY-FINDINGS.md`.

## The gate (identical discipline to S1)
- G1: >= 50 settled simulated rounds
- G2: >= 20 fills
- G3: mean realized edge per filled share > 0  (the fair-value anchor survives adverse selection)
- G4: model certification >= 90% (fair at fill agreed with the round's outcome)

Rebates/rewards are **never** counted toward the gate — the report prints them
separately as an explicit upside estimate (20% of taker fees on our fills,
upper bound). If the spread capture alone doesn't clear the gate, the strategy
doesn't run, even though the house would pay us rebates.

## Honest limitations (read before trusting any number)
1. **No queue-position data.** The 50% fill-on-cross haircut is a guess in the
   conservative direction; real fills could be more (front of queue) or less.
2. **1-second book sampling** in live mode — a cross that happens and reverts
   inside a second can be missed; replay mode (1s snapshots too) has the same
   limit. This biases fill counts DOWN, not up.
3. Rebate share is pro-rata among all makers; our estimate assumes we're the
   only maker (upper bound). Rewards (daily $ rates) are eligibility-modeled,
   not amount-modeled.
4. Settlement semantics are the S1-verified full-round TWAP-average model —
   reuse of the arbiter math that went 70/70 against official resolutions.
   If the venue changes the window again, regime-watch catches it and this lab
   must be re-validated.

## VPS runbook
```bash
sudo mkdir -p /opt/maker_lab && sudo tar xzf maker_lab.tar.gz -C /opt/maker_lab --strip-components=1
cd /opt/maker_lab
sudo cp deploy/maker-recorder.service deploy/maker-sim.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now maker-recorder maker-sim
journalctl -fu maker-sim        # FILL / ROUND-SETTLED lines
python3 maker_report.py         # check the gate whenever you like
# replay a recorded day through the engine:
./run_sim.sh --replay book_data/2026-09-25.jsonl
```
Run it alongside `s1-harness`, `s1-trader` and `regime-watch`. No secrets,
no `.env`, public endpoints only (~3 requests/s).

## Expected accumulation rate
288 five-minute + 96 fifteen-minute rounds per day. Quote-time is roughly the
middle 80% of each round, so fills depend on BTC volatility — expect the 20-fill
gate to take days, the 50-round gate ~half a day. This is a weeks-scale
incubation by design; the house only pays the patient.
