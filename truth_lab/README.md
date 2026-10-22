# TRUTH LAB — the truth-feed divergence recorder

**Spec + build, 2026-10-14.** Measurement-only: no keys, no orders, no capital.
Complies with house rules ("measure, don't attack": public read endpoints only,
polite rates). Runs alongside — not instead of — `maker_lab/book_recorder.py`.

## Why this exists (the one-paragraph doctrine)

Everyone competes on predicting the future — the unknowable thing. Almost
nobody competes on knowing the PRESENT better than the venue's own displays.
We already proved the asymmetry exists: Polymarket's `/api/past-results`
`outcome` field is wrong vs the blockchain on **27.5–35% of sub-2bp rounds**,
gamma replicas serve stale sides for hours, and the UI "Current Price" is just
TWAP60 rounded to cents. That audit (2026-09-27) was *retrospective*. This lab
makes it **prospective**: a continuous, timestamped record of every source's
claim vs the chain's truth, per round, forever. A measurement history can't be
copied — it has to be lived. (See `VENUE-TRUST-MODEL.md`: trust chain over
venue, our own fills over everything.)

## What it records

Per round (BTC 5m + 15m up/down), three phases:

| Phase | Source | What we capture |
|---|---|---|
| LIVE (1 Hz) | RTDS `crypto_prices_twap_sixty` | the settlement feed itself (Chainlink TWAP60) |
| | RTDS `crypto_prices_chainlink` | spot |
| | our arbiter | accumulated-TWAP reconstruction vs open ref → p(Up), gap_bps (S1-verified semantics: 100% match to official resolution above 4 bps) |
| | CLOB book (every 2s) | best bid/ask/mid for UP token — what traders believe |
| SETTLEMENT (poll) | gamma `outcomePrices` | **first-final timestamp** + display direction |
| | `/api/past-results` `outcome` | the known-buggy derived field (our divergence target) |
| GROUND TRUTH (poll) | Polygon CTF `payoutNumerators` (0x4D97…a045, sel 0x0504c814, idx0=Up) | direction + **finality lag** |
| | Data API v2 `/v2/resolutions` | lifecycle: resolved / disputed / extended review |

## Outputs (`truth_data/`)

- `timeline-YYYY-MM-DD.jsonl` — every 1 Hz live record + one `verdict` record per round
- `divergences.csv` — one verdict row per round; columns include `gap_bps`,
  `coverage`, `arbiter_outcome/match`, `chain_outcome/lag_s`,
  `gamma_outcome/first_final_ts/lag_s`, `pr_outcome/match`, `book_mid_end`,
  `house_status/disputed/extended/verdict`, `arbiter_early_s`

## Analysis

```bash
python3 divergence_report.py
```
Reports: (1) past-results wrong-rate by |gap| bucket — prospective replication
of the 27.5–35% finding; (2) finality-lag distributions (gamma display vs
chain); (3) arbiter-vs-chain agreement (coverage ≥0.95 only) and the
**head start in seconds** we hold over the house display when we agree with
chain; (4) house lifecycle flags.

## The three questions this data answers (pre-registered, before results)

1. **Is the display wrong where it matters?** If pr_wrong% concentrates in
   <2bp buckets (as the retrospective audit says), the house's own UI/API
   misleads traders exactly on razor rounds — measurable, persistent, public.
2. **How many seconds is the truth early?** `arbiter_early_s` = gamma finality
   lag on rounds where our arbiter already matched chain at t=round-end. If
   median head start is large in thin markets, the fourth-witness family of
   strategies gets a real, bounded number to design against.
3. **Does the house ever disagree with the money?** gamma final display vs
   chain, and dispute flags. Any nonzero count is a trust-model event →
   escalate per `VENUE-TRUST-MODEL.md` / `MASTER-RUNBOOK.md` §7.

Decision rule: this recorder informs strategy design; it does NOT trade. Any
strategy that consumes its numbers still passes the normal gates (≥200 rounds,
chain-verified, cost-net) before a single dollar.

## Run

```bash
pip install websockets
python3 truth_recorder.py          # foreground; or:
./run_recorder.sh                  # tmux
# stop cleanly: touch truth_lab/KILL  (pauses writes) or kill the process
python3 divergence_report.py       # after a day or two of data
```

Rate budget: 1 ws connection + ~0.5 REST/s live + settlement polls (~12/min
gamma, ~4/min RPC per settling round). Far below every published limit.

## First live findings (smoke test, 2026-10-14, n=2 — anecdote, not stats)

1. **Display wrongness caught live on round 2.** Chain said Down; the house's
   `past-results` display said "Up". Mechanism fully visible in the data:
   price spent the window ~$79 below the open (settlement TWAP → Down), then
   rebounded +$7 in the final seconds, so sign(close−open) → "Up".
2. **The right bucket axis is the HOUSE's, not ours.** Our TWAP gap for that
   round was −9.58 bp (looked "safe"), but the house's own |close−open| was
   +0.85 bp (razor). `divergence_report.py` therefore buckets display
   wrongness by BOTH axes; `pr_gap_bps` (house axis) is the primary predictor.
3. **Chain truth is ~2–3 minutes faster than the house display.** Both smoke
   rounds: chain final at +57 s, gamma display final at +153/+183 s. Our
   arbiter matched chain at t=round-close on both (head start 153–183 s).
4. **Open-ref drift exists.** House recorded openPrice 82751.95 vs our snapped
   o_ref 82747.95 ($4 ≈ 0.5 bp). The report tracks this per round — if it is
   systematic, settlement-boundary math must use the house's print, not ours.

## Known limits (honest section)

- Arbiter needs coverage ≥0.95 (recorder must see the round open) — late-join
  rounds are recorded but excluded from agreement stats.
- Chain finality polling stops at 45 min/round; slower resolutions log as
  pending and can be re-verified later with `maker_lab/chain_verify.py`.
- `book_mid_end` is the last poll ≤2s stale, not a tick-perfect close print.
- Sandbox/VPS clock must be NTP-synced: all lag math is wall-clock vs round grid.
