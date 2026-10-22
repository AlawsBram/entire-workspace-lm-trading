# PROMPT — hand this, plus the workspace ZIP, to your other AI

---

You are taking over a Polymarket BTC-5m/15m + weather-markets research project.
Attached is the full research workspace (ZIP). Your job: **read it, reconcile it
with the deployed code, and finish building the measurement + backtest stack
described below.**

## 0. Two sources of truth — reconcile them first

1. **The attached workspace ZIP** = the research & measurement foundation
   (discovery, audits, recorders, trust model). Read these FIRST, in order:
   - `MASTER-RUNBOOK.md` — deployment map, house rules, KILL-switch discipline
   - `app_lab/REALTIME-STACK-PLAYBOOK.md` — the current plan + build queue
   - `app_lab/US-VENUE-BASELINE.md` — US-venue protocol/latency measurements
   - `app_lab/MOBILE-APP-DEEP-ANALYSIS.md` — decompiled Android app findings
   - `maker_lab/instructions.md`, `maker_lab/README.md` — chain-verified history corpus
   - `STRATEGY-STACK-RERANKED.md`, `BTC-5m-15m-POLYMARKET-10-STRATEGIES.MD`
   - `USER-PREFERENCES.md` — MANDATORY explanation style: explain like the user is
     15; open every explanation with "I'm explaining this in simple language a
     15 year old can understand:"
   - `polymarket secrets/00 - INDEX.md` — DevTools + endpoint audit index
   - `VENUE-TRUST-MODEL.md` — adversarial-venue threat analysis (what if the
     venue is hostile: three claims, evidence status, mitigations)
2. **GitHub repo** https://github.com/georgeskarlatos89-byte/btc-5min-twap-lockin.git
   = what is ALREADY built/deployed (strategies #1–#10 folders, `s1_harness`,
   `s1_monitor`, living-record write-ups). **Clone it. Do NOT rebuild what
   exists there — integrate and extend.** Where workspace and repo disagree,
   the repo's living records describe production reality; the workspace
   describes the measurement evidence. Note disagreements explicitly.

## 1. Key findings you must encode (non-negotiable facts)

**READ FIRST: `VENUE-TRUST-MODEL.md`** — adversarial-venue threat analysis
(regime-change-vs-winners: documented; planted-whale strong form: unsupported;
information asymmetry: permanent). It defines why the stack is designed to be
unaffected by venue hostility regardless of which theory is true.

**Trust model / why our backtests beat public-API backtests:**
- Ground truth = Polygon CTF `payoutNumerators` (contract
  `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`, selector `0x0504c814`, idx0=Up).
  `maker_lab/chain_relabel.py` + `chain_verify.py` produce the relabeled corpus
  in `maker_lab/history/`.
- Public sources are WRONG near boundaries: `/api/past-results` `outcome` is
  wrong vs chain on ~27.5–35% of sub-2bp rounds; gamma `gamma_fresh` column is
  garbage; UI "Current Price" = TWAP60 rounded to cents. Any strategy whose
  edge concentrates in the final seconds (all of ours do) gets systematically
  mis-backtested on public labels. **Every backtest must run twice: once on the
  chain-verified corpus, once on public-API labels, and report the delta.**

**Three oracles — no assumption transfers between rows:**
| product | venue | oracle | rounding | ties |
|---|---|---|---|---|
| updown 5m/15m/1h | polymarket.com | Chainlink TWAP | 1¢ | Up |
| touch markets | polymarket.us | Binance BTCUSDT 1m candles | — | — |
| updown 15m/1h (LIVE) | polymarket.us | CF Benchmarks BRTI TWAP60 | 2dp on index | Up |

**US venue (already measured, verified):**
- 15m+1h "BTC Up or Down" rounds are LIVE on polymarket.us, slug formula
  `btc-updown-15m-YYYY-MM-DD-HHMMz`, but invisible to GetSeries/GetEvents —
  discoverable only via `unified-api.polymarket.us` SearchUnifiedService.
  No 5m round yet.
- Anonymous websocket protocol (verified): connect
  `wss://gateway-ws-markets.polymarket.us/v1/ws/subscriptions`, send
  `{"subscribe":{"requestId":"<uuid>","subscriptionType":"SUBSCRIPTION_TYPE_MARKET_DATA_LITE|MARKET_DATA|TRADE","marketSlugs":[...]}}`,
  unsubscribe same shape. TRADE frames include maker side + intent.
- `settlementPx` arrives over WS within ~1s of round boundary — free audit trail.
- HTTP latency p50 from East Africa 115–213ms; Go+ConnectRPC behind Cloudflare;
  strict exact-path routing; NO private retail feed exists (app uses the same
  anonymous WS) → edge must be cognitive (oracle-read speed, structure, carry).

**Weather markets (LIVE on US venue):**
- 5 cities (NYC/MIA/SFO/LAX/MDW), daily-high temp, $1°F buckets
  (`tc-temp-{city}high-{date}-{bucket}`), resolve off NWS Climatological Report
  (Daily) at the named station (e.g. KNYC). Rule text embeds station code.
- Measured: today-books carry 8–13% ask-side overround; next-day books are
  illiquid (ask-sum ≈3.15 for a $1 ensemble). Bucket-sum coherence must be
  judged on EXECUTABLE ask-sums — mid-sums fake signals (caught one: mid 0.98
  "arb" was ask 1.52).
- NWS `api.weather.gov` forecast `updateTime` diffs = timestamped public
  information events; market reaction-lag is the edge to measure.

**Security posture (do not violate):** no probing authenticated surfaces, no
promo/bonus interaction, no schema brute-forcing, no endpoint hammering.
Measure, never attack. Config store is read-only (no Set RPC exists). Keys
only in user-created `.env` chmod 600, never in chat/output.

## 2. Build list (deliverables)

1. **7-day backtest engine** — for strategy S1 (TWAP Lock-In, per repo `#1`
   folder + `s1_deploy` in workspace) and any other repo strategy with data
   available: backtest the last 7 days of rounds on (a) chain-verified corpus,
   (b) public-API labels. Report: win-rate, fee-adjusted PnL at $10/trade and
   $20 daily stop, per-session split, and the accuracy delta (a vs b) with the
   specific boundary-round cases where labels disagree. CSV outputs with
   proper named columns.
2. **US round recorder + BRTI proxy** — workspace `app_lab/us_round_recorder.py`
   is the reference implementation (4-constituent books: Coinbase+Kraken REST
   1Hz, Bitstamp+Gemini WS; staleness>30s & >25% exclusion; TWAP60 at
   boundaries; settlementPx capture; rounds.csv OK/DIVERGENCE column).
   Productize it: systemd unit, log rotation, and a validation report once
   ≥200 rounds have proxy-vs-settlement comparisons.
3. **NWS watcher + bucket-sum scanner** — reference `app_lab/nws_watch.py`
   (forecast-diff lag table at t+0/10/60/300s; ask-side bucket-sum verdicts).
   Productize likewise.
4. **Regime-watch upgrade** — workspace `regime_watch/` now has:
   weather-rule canary (`us-weather-rules`, hashes station/source rule text),
   unified-search updown sentinel (fires once if a new round type like 5m
   appears). Reconcile with the VPS-deployed version per MASTER-RUNBOOK §4
   upgrade note; deploy the new tarball.
5. **Mispricing monitors** (from recorder data, no trading): one-sided-book
   statistic per minute-to-resolution; market-vs-oracle divergence series;
   cross-venue .com-vs-US round comparison when both run the same window.
6. **One integrated daily dashboard/report** summarizing all of the above,
   in the style of the repo's living records.

## 3. Constraints (standing)

Measure-don't-attack discipline everywhere; KILL switch before any trading
code runs; $10/trade, $20/day caps; burner wallet only; no real orders until
the user explicitly re-approves after seeing backtest + validation results.
Do not modify the decompiled-app ZIPs (evidence archive) — use `app_lab/`
extracted findings instead.

## 4. Output

Start by producing: (a) a reconciliation table workspace-vs-repo (what exists
where, what's missing, what disagrees), then (b) build order with the 7-day
backtest FIRST because its accuracy-delta result dictates everything else.
