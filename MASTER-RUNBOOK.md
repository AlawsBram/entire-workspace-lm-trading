# MASTER RUNBOOK — Polymarket Incubation Stack on Your VPS
*2026-09-25 · covers every deliverable: S1 deploy, regime watch, maker lab*

> One goal: get all five services running on the VPS, then let evidence
> accumulate. Nothing here spends money except the S1 trader, and only under
> the conditions YOU set in `/opt/s1/.env`.

---

## 0. What you're deploying (download these from the chat workspace first)

| file | what it is | VPS home |
|---|---|---|
| `s1_deploy.tar.gz` | S1 TWAP Lock-In: harness (observer/arbiter) + gated trader + playbook | `/opt/s1` |
| `regime_watch.tar.gz` | rule-change sentinel (fees, tick, taker delay, docs diffs, US legal docs, US gateway configs, weather-rule canary, updown-round listing sentinel via unified-search) | `/opt/regime_watch` |
| `maker_lab.tar.gz` | maker-family incubator: book recorder + quoting simulator + gate report + history backfill tool | `/opt/maker_lab` |
| `truth_lab.tar.gz` | truth-feed divergence recorder: per-round timestamped record of every source's claim (RTDS/arbiter/book/gamma/past-results/chain/house-v2) vs chain ground truth + `divergence_report.py` | `/opt/truth_lab` |
| `Moondev Docs.zip` *(optional)* | reference docs for the Moon Dev API (strategies #4, #9) | anywhere |

All three tarballs are secret-free and self-contained. Every launcher
self-installs its one pip dependency (`websockets`) on first run.

## 1. VPS requirements

- Ubuntu 22.04+, 1 vCPU / 1 GB RAM is enough, python3 + pip:
  ```bash
  sudo apt update && sudo apt install -y python3 python3-pip curl
  ```
- Outbound internet only (no inbound ports needed).
- Total load: ~5 requests/s of public API calls. Trivial.

## 2. Copy the tarballs to the VPS, then unpack

```bash
# from your local machine (adjust user/host):
scp s1_deploy.tar.gz regime_watch.tar.gz maker_lab.tar.gz truth_lab.tar.gz user@YOUR_VPS:/tmp/

# on the VPS:
sudo mkdir -p /opt/s1 /opt/regime_watch /opt/maker_lab /opt/truth_lab
sudo tar xzf /tmp/s1_deploy.tar.gz   -C /opt/s1
sudo tar xzf /tmp/regime_watch.tar.gz -C /opt/regime_watch --strip-components=1
sudo tar xzf /tmp/maker_lab.tar.gz    -C /opt/maker_lab    --strip-components=1
sudo tar xzf /tmp/truth_lab.tar.gz    -C /opt/truth_lab    --strip-components=1
```

## 3. Wallet + credentials — ONE TIME, done by you alone

Never your main wallet. Never paste a key into chat or any doc.

1. Generate a fresh **burner EVM wallet** used only for this incubation.
2. Fund it: **~$20 USDC on Polygon + ~$1 POL** for gas
   (one one-time token-approval happens automatically on first order).
3. Create the env file yourself on the VPS:
   ```bash
   cd /opt/s1
   sudo -u $(whoami) bash -c 'umask 077 && touch .env'
   echo "POLY_PRIVATE_KEY=0xYOUR_BURNER_KEY" | sudo tee -a /opt/s1/.env >/dev/null
   echo "LIVE_TRADING=0" | sudo tee -a /opt/s1/.env >/dev/null
   # choose ONE incubation mode (see below) — start with the gated default:
   #   gated:    keep LIVE_TRADING=0, later flip to 1
   #   immediate: add a line FORCE_LIVE=1  ($10 incubation starts right away)
   sudo chmod 600 /opt/s1/.env
   ```
   - **Gated mode** (default): trader stays dry until arbiter ≥50 rounds AND
     ≥20 dry signals at ≥90% — then you flip `LIVE_TRADING=1`.
   - **FORCE_LIVE=1** (recommended for the $10 incubation you approved):
     trades immediately under all HARD gates (key present, no KILL, fresh
     feed) and risk caps ($10/trade, 1/round, 3/hour, $20 daily stop → auto-KILL).
     The statistical gates then serve as **scaling gates**, not starting gates.

## 4. Install and start everything (6 services)

```bash
sudo cp /opt/s1/deploy/s1-harness.service /opt/s1/deploy/s1-trader.service /etc/systemd/system/
sudo cp /opt/regime_watch/deploy/regime-watch.service /etc/systemd/system/
sudo cp /opt/maker_lab/deploy/maker-recorder.service /opt/maker_lab/deploy/maker-sim.service /etc/systemd/system/
sudo cp /opt/truth_lab/deploy/truth-recorder.service /etc/systemd/system/
sudo systemctl daemon-reload

# baseline the regime sentinel FIRST (records today's rule set as the reference):
cd /opt/regime_watch && sudo -u $(whoami) python3 regime_watch.py --baseline

sudo systemctl enable --now s1-harness s1-trader regime-watch maker-recorder maker-sim truth-recorder
```

**Upgrading an existing regime_watch** (e.g. to the 2026-09-27 build that adds
the US-venue feeds): re-scp `regime_watch.tar.gz`, extract over `/opt/regime_watch`
(keeps `regime_state.json`), then `sudo systemctl restart regime-watch`. The 7
new sources (us-legal-*, us-incentives-docs, us-gateway-configs, us-gateway-series,
us-venue-5m-sentinel) self-baseline on their first cycle — no false alerts.

**Optional control monitor:** `ui_lab.tar.gz` → `/opt/ui_lab` (+ `deploy/ui-lab.service`)
runs a headless browser that reads the actual UI DOM each round and diffs it
against the APIs (see `ui_lab/UI-VS-API-FINDINGS.md`). It trades nothing; it
only watches for UI-layer regime changes (new rounding, new delays, new feeds).

## 5. Verification checklist (run once, ~10 minutes after start)

```bash
sudo systemctl status s1-harness s1-trader regime-watch maker-recorder maker-sim --no-pager
```

You should see, in each journal (`journalctl -fu <unit>`):

| unit | healthy looks like |
|---|---|
| `s1-harness` | `RTDS connected` … then `ROUND-RESULT … SEMANTICS MATCH ✔` rows after each round |
| `s1-trader` | `DRY SIGNAL`/`LIVE` lines, `arbiter=X/50` counter climbing |
| `regime-watch` | `baseline written` then quiet; `cycle done` every 10 min with no `REGIME-CHANGE` |
| `maker-recorder` | `recorded 60s of data (twap=84xxx.x)` every minute, `book_data/YYYY-MM-DD.jsonl` growing |
| `maker-sim` | `HEARTBEAT … feed_age=0-2s` every minute, `FILL live …`, `ROUND-SETTLED live …` after each round |

Arbiter pace: ~16 rounds/hour (12×5m + 4×15m) → **50 rounds ≈ 3–4 hours of uptime.**

## 6. Daily operations (2 minutes a day)

```bash
sudo systemctl is-active s1-harness s1-trader regime-watch maker-recorder maker-sim truth-recorder
tail -5 /opt/regime_watch/regime_watch.log                      # any REGIME-CHANGE?
python3 /opt/regime_watch/regime_watch.py --status              # watcher health
wc -l /opt/s1/rounds.csv                                        # arbiter accumulating?
python3 /opt/maker_lab/maker_report.py                          # maker gate verdict
python3 /opt/truth_lab/divergence_report.py                     # truth-feed divergence stats
```

## 7. When something happens — protocols (do not improvise)

**`REGIME-CHANGE` alert** (fees / feeSchedule / seconds_delay / tick / settlement):
```bash
touch /opt/s1/KILL                       # 1. stop the trader FIRST
sudo systemctl restart s1-trader         #    (it sees KILL and drops to dry)
cat /opt/regime_watch/regime_watch.log   # 2. read the diff + snapshots/
# 3. decide: rules still suit our edge? if unsure, stay dry and re-validate
#    (harness arbiter keeps proving semantics under the new rules)
rm /opt/s1/KILL && sudo systemctl restart s1-trader   # 4. resume only by choice
```

**`WATCHER-BLIND`** — the watcher itself is failing. Fix it before trusting
any "no change" output (check network; restart `regime-watch`).

**`FEED-STALE` in maker logs** — auto-recovers (forces RTDS reconnect). Only
act if it repeats constantly (network/firewall issue).

**Trader misbehaving / anything weird:** `touch /opt/s1/KILL` first, diagnose second.
The $20 daily stop writes KILL automatically — if you find it, read
`trader.log` before removing it.

## 8. Milestones & decision tree

1. **Day 0–1:** all five services up; arbiter fills to 50/50 (~4 h);
   regime baseline holds. If FORCE_LIVE=1, the first qualifying S1 signal
   trades $10 within a day or two (signals need volatility).
2. **Week 1:** compare `rounds.csv` live-match rate with backtest (expect
   ~100% semantics match on full-coverage rounds). Maker lab passes the
   50-round gate (~half a day) — expect **INSUFFICIENT/FAIL at first**;
   that is information, not failure.
3. **Maker tuning loop** (after ≥50 simulated rounds): inspect losses in
   `sim_rounds.csv` → change one knob in `/opt/maker_lab/make_strategy.py`
   (candidate order: skip quoting in first ~60 s, widen `HALF_SPREAD`,
   tighten `MAX_NET_SHARES`) → replay the corpus
   (`./run_sim.sh --replay book_data/*.jsonl`) → if replay improves, restart
   `maker-sim` and let it re-accumulate. Never tune from a single round.
4. **Scaling rule (S1):** scale size only after 2–4 weeks where live results
   match backtest expectations; the house notices size, not skill — stay small.
5. **Maker family goes live ONLY when the gate report says PASS** (≥50 rounds,
   ≥20 fills, mean realized edge > 0, ≥90% certification) — and then at
   minimal size, with regime-watch running. Rebates/rewards are upside on top,
   never the reason to run.
6. **Moon Dev key (later):** strategies #4 (cascade) and #9 (wallet coattails)
   unlock when you add a key to the VPS — see `Moondev Docs/` (sections
   *Multi-Exchange Liqs* and *Polymarket Traders*). Not needed before then.
7. **2026-10-24 — Data API v1 retired.** Our stack has NO v1 dependency
   (history uses gamma + CLOB + chain). New v2 reads available from that
   platform if ever needed: `/v2/prices-history` (token price history),
   `/v2/resolutions` (resolution state), `/v2/user-pnl`, `/v2/status`.
   Envelope = `{data, pagination}` cursors; fields snake_case. Full mapping
   mirrored in `Entire polymarket API Reference docs/Migrate from Data API v1 to v2.md`.

## 9. House rules (why this stack is shaped this way)

- The venue edits its own physics — sometimes silently. Regime-watch exists
  because rule-change risk is the #1 risk, above market risk.
- Edges are perishable (alpha decay): plan harvests in weeks, not years.
- Stay below the house's attention threshold: small size, compound fast.
- Trust what you measure, not what docs claim: every component validates
  against official resolutions, never against its own assumptions.
- Maker family = house payroll (zero fees + rebates + rewards) → top of queue.
  Taker edges (S1) = tolerated crumbs → stay tiny. Latency sniping = banned.
- Adversarial-venue posture: `VENUE-TRUST-MODEL.md` — assume regime change is
  weather, quoted depth is untrusted (verify fills), no strategy may depend on
  counterparty identity/honesty, and max damage is capped by the stakes ladder
  even if every hostility theory is true.

### Rules added 2026-10-14 — the OPEN-BOOK-MAKER post-mortem ("the $32.60 rules")

On 2026-10-10 a gate-FAILED backtest (15:19) was followed by live money (16:01)
under the rationale "I don't trust this data." The live test added no information
the backtest didn't already have, and cost a third of the account. These rules exist
so that sequence is mechanically impossible, not just forbidden:

1. **A failed gate is a verdict, not a hypothesis. Live money never validates a
   backtest.** Distrust of data is answered by auditing the pipeline (see the
   12-error REVIEW checklist in `open_book_maker/postmortem-2026-10-10/`), never by
   trading. Welded in code: no strategy bot may leave DRY_RUN without a fresh
   `gate_pass.json` (criteria values + CIs + code/corpus hashes, <7 days old) that
   the bot itself verifies (revival criteria R7–R8 in
   `open_book_maker/VARIANT-EXPERIMENT-PLAN.md`).
2. **No bundle deploys until its settlement path has run end-to-end on its own
   output** (sim → CSV → chain verify → report), and sim and bot share ONE
   quoting/fill/sizing code path. v1 shipped a gate whose verifier crashed on the
   sim's own CSV (E6) — a "chain-verified" claim that had never executed.
3. **Size by worst-round swing, not by account vibes:** worst round ≤1–2% of
   capital, else the shape does not trade at that capital (the prop-firm checker's
   auto-scale logic is the universal sizing gate). $65 hosting a $10-swing shape
   put 19–46% of the account on single rounds; that shape's honest minimum was
   ~$500–1,000 — and even then only with a positive gate.

## 10. Troubleshooting quick table

| symptom | check / fix |
|---|---|
| service fails on boot | `journalctl -u <unit> -n 50` — usually pip/network; rerun, launchers self-install |
| `rounds.csv` not growing | harness needs to be alive AT the round bell; check uptime/`RTDS connected` |
| trader stuck in dry unexpectedly | `cat /opt/s1/.env` (mode), arbiter count, `KILL` file, feed age |
| maker report stuck at 0 rounds | `maker-sim` needs ≥1 full round per market it settles; check HEARTBEAT lines |
| replay says "resolution not final" | gamma was slow; rerun replay later — nothing lost |
| disk worry | `book_data/` is ~30–60 MB/day; prune or gzip monthly |

## 11. Files that matter on the VPS

```
/opt/s1/            harness+trader, .env (600), rounds.csv (arbiter), KILL switch
/opt/regime_watch/  regime_state.json, regime_watch.log, snapshots/
/opt/maker_lab/     book_data/*.jsonl (corpus), sim_rounds.csv, sim_fills.jsonl,
                    maker_stats.json, maker_sim.log, history/*.csv (past-results)
/opt/truth_lab/     truth_data/divergences.csv (one verdict row/round),
                    truth_data/timeline-YYYY-MM-DD.jsonl (1 Hz live + verdicts),
                    KILL file pauses writes (no keys anywhere in this lab)
```

Optional maintenance — history corpora:
`python3 /opt/maker_lab/history_backfill.py --symbol BTC --variant fiveminute --days 7`
(and `--variant fifteen`) refreshes the full-precision 7-day price corpus
(endpoint keeps only ~1 week). `history_backfill_gamma.py` extends OUTCOMES back
to series start (2025-12-18); `chain_verify.py` re-labels any corpus against the
on-chain payout vector (the only authoritative source on razor rounds — see
`maker_lab/history/HISTORY-FINDINGS.md` §4; never settle from past-results `outcome`).

**Daily cron (recommended)** — one line runs the whole refresh (7-day price
corpus rewrite + incremental deep-outcome extend):

```cron
10 0 * * * /opt/maker_lab/deploy/history-refresh.sh >> /var/log/history-refresh.log 2>&1
```

Install: `chmod +x /opt/maker_lab/deploy/history-refresh.sh && crontab -e` and
paste the line. Runs 00:10 UTC so yesterday's final rounds are settled. Log
rotation: add `/var/log/history-refresh.log { monthly; rotate 6; compress; missingok; notifempty }`
to `/etc/logrotate.d/history-refresh`.

**One-time full on-chain relabel (belt-and-braces labels for all ~76k rounds):**
follow `maker_lab/instructions.md` — test with `--limit 1000`, then
`python3 /opt/maker_lab/chain_relabel.py --csv history/BTC_fiveminute_long.csv --workers 4`
(~2-3.5h, resumable; repeat for `BTC_fifteen_long.csv`). After it completes once,
uncomment the two `chain_relabel.py` lines inside `history-refresh.sh` so new
rounds stay chain-verified daily.

**Fourth witness (2026-10 build):** `chain_verify.py` now also pulls the
house's own Data API v2 resolution record (`/v2/resolutions`, 20 ids/call) on
every run and writes `house_status/house_disputed/house_extended/house_tx/
cross_verdict` columns into `*.chain.csv`. Expect `house_flags: 0`; any
`DISPUTED`/`EXTENDED_REVIEW`/`NOT-RESOLVED`/`HOUSE-MISSING` row is printed for
manual review (chain stays authoritative for direction; the house record
certifies the lifecycle). Standalone batch scan: `resolutions_check.py`.
No v1 routes are used anywhere — the Oct 24, 2026 Data API v1 retirement is
a non-event for this stack (see milestone 7).

---

## 12. US realtime-measurement stack (optional, research-grade)

Two standalone recorders for the Polymarket US venue (see
`app_lab/REALTIME-STACK-PLAYBOOK.md`). Both are measure-only, secret-free,
and need only `websockets` + outbound internet. Copy from the chat workspace:
`app_lab/us_round_recorder.py` and `app_lab/nws_watch.py`.

**A. US updown round recorder + BRTI proxy** — anonymously subscribes to the
public `wss://gateway-ws-markets.polymarket.us` feed for the live 15m/1h BTC
Up-or-Down rounds, archives every frame with a ns clock, samples
Coinbase/Kraken/Bitstamp/Gemini order books at 1 Hz, and computes a BRTI-proxy
TWAP60 at each boundary. Writes `us_rounds/frames-*.jsonl`, `brti-proxy-*.jsonl`,
and `rounds.csv` (proxy direction vs venue `settlementPx` → OK/DIVERGENCE).
```bash
mkdir -p /opt/us_measure && cp us_round_recorder.py /opt/us_measure/ && cd /opt/us_measure
python3 -m pip install --user websockets
python3 us_round_recorder.py        # run under systemd/tmux; outputs in ./us_rounds/
```
**B. NWS weather watcher** — diffs `api.weather.gov` forecast updates for the 5
priced cities, snapshots the affected Polymarket temperature buckets at
t+0/10/60/300 s into a reaction-lag table, and runs an hourly bucket-sum
coherence scan (verdicts use the executable ask-sum, not mids).
```bash
cp nws_watch.py /opt/us_measure/ && cd /opt/us_measure
python3 nws_watch.py --once         # test pass; then run continuously
```
Neither writes secrets nor places orders. The BRTI proxy is a research replica —
validate it against ≥200 rounds of venue `settlementPx` before trusting it as an
arbiter for anything.

---
**One-line summary:** unpack → baseline the watcher → create `.env` → enable
the five services → read one dashboard daily → KILL first, think second.
