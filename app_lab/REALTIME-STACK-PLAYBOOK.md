# REALTIME-STACK × BTC-UPDOWN × WEATHER PLAYBOOK

Date: 2026-09-27 · Status: ACTIVE RESEARCH · Discipline: measure, never attack
Companion docs: `US-VENUE-BASELINE.md`, `MOBILE-APP-DEEP-ANALYSIS.md`, `MASTER-RUNBOOK.md`

---

## 0. The ground shifted under us today

Three discoveries, all verified live (anonymous, read-only):

1. **The US venue ALREADY runs BTC Up-or-Down rounds** — `15 min` and `60 min`
   horizons, live rounds on a 15-minute cadence (`btc-updown-15m-YYYY-MM-DD-HHMMz`).
   No 5m round exists yet — but the ladder (60m → 15m → ?) points one direction.
2. **These rounds are INVISIBLE to GetSeries/GetEvents.** They are search-only
   products, discoverable only via `unified-api.polymarket.us` unified-search.
   Our sentinel missed them for exactly this reason — **now patched**
   (`regime_watch.tar.gz` re-packaged; sentinel probes unified-search, normalizes
   round timestamps so it only re-alerts when a NEW round type — e.g. 5m — appears).
3. **The US updown oracle is NEITHER Binance NOR Chainlink.** Per the live market
   description it settles on **CF Benchmarks' Bitcoin Real-Time Index (BRTI)**:
   60 BRTI prices collected in the last minute at each boundary, simple average,
   rounded to 2dp, **ties settle Up**.

Three venues/products, three oracles — this is now the single most important
fact in the whole research corpus:

| product | venue | oracle | rounding | ties |
|---|---|---|---|---|
| BTC updown 5m/15m/1h | polymarket.com | Chainlink TWAP | 1¢ | Up |
| BTC touch markets (US app) | polymarket.us | Binance BTCUSDT 1m candles | — | — |
| **BTC updown 15m/1h** | **polymarket.us** | **CF Benchmarks BRTI TWAP60** | **2dp on index** | **Up** |

No strategy assumption transfers between these rows. Each needs its own audit.

## 1. Applying the realtime stack to BTC-15m (and future 5m)

The anonymous WS streams the updown rounds exactly like sports — verified live
on `cpc-btc-updown-15m-2026-09-27-1100z`:

- `MARKET_DATA_LITE`: currentPx, bestBid/Ask + depths, volume, OI,
  **`settlementPx` (null until resolution → venue's own resolved value)**, ns timestamps
- `MARKET_DATA`: full order-book levels both sides (book moved between two frames 1s apart)
- `TRADE`: tape with maker side + intent

Concrete implications:

- **Slug prediction**: next round's slug is computable from wall-clock
  (`btc-updown-15m-2026-09-27-1115z`). A recorder can pre-subscribe before
  trading opens — same trick as .com's round grid.
- **`settlementPx` is a free audit trail.** After every round, the venue pushes
  the value it used. Record it every round; compare against our own BRTI
  reconstruction; drift or mismatch = dispute-grade evidence (the house-edits-rules
  playbook applies verbatim).
- **Live measured state (11:13:48z of the 11:00z round)**: Up @ 0.99, one-sided
  book (`bestAsk: null, askDepth: 0, bidDepth: 25`), 64.8k shares traded.
  Final-minute books go one-sided — see §4.5.

### Replicating BRTI (the new arbiter problem)
BRTI is a multi-exchange composite (Coinbase, Kraken, Bitstamp, LMAX Digital,
Gemini…). Replication plan before ANY trade on US rounds:
1. Stand up WS feeds for the constituents (all have public market-data feeds).
2. Compute rolling TWAP60 at boundaries; compare vs `settlementPx` for N≥200 rounds.
3. Publish the reconstruction-error distribution (in bps). Only when error <
   ½ tick in p99 do we treat the replica as an arbiter.
Until then: measure only.

## 2. Manipulation & data-accuracy angles (BTC rounds)

1. **TWAP-window gaming is the only viable manipulation vector** (same as .com):
   the boundary value is an average of 60 one-second-ish samples in the final
   minute. Watch: constituent-exchange order flow in the last 60s vs the rest of
   the round. If venue books ever show someone lifting the tape in the boundary
   minute on a constituent, that's the smoking gun.
2. **Market-vs-oracle divergence monitor**: subscribe lite feed + run BRTI proxy.
   Implied p(Up) from the oracle walk vs market px — persistent divergence
   beyond model noise = either informed flow or a stale quote to exploit/avoid.
3. **Cross-venue round arb (structural)**: .com runs the SAME underlying event on
   Chainlink TWAP; US runs it on BRTI. When the two oracles agree (usual case),
   the two books should price near-identically; near-boundary divergences are
   structural. Requires a US account (KYC) — gated, logged as constraint, not action.
4. **Resolution audit triangle** (the trust model, ported):
   `venue settlementPx` × `our BRTI replica` × `market tape at boundary` —
   all three must agree within tolerance every round. Any leg diverging =
   automatic freeze + evidence file. This is exactly the chain-audit machinery
   we built for .com, re-targeted.
5. **Rounding asymmetry**: 2dp rounding on the *index* (not on 1¢ market prices)
   + ties→Up gives a systematic Up bias on dead-flat rounds. Measure flat-round
   frequency from settlementPx history once recorder runs.

## 3. Weather markets — the slowest markets on the venue, which IS the edge

Structure (verified live):
- 5 cities: **NYC (KNYC/Central Park), Miami, San Francisco, Los Angeles, Chicago (MDW)**
- Daily **high temperature**, $1°F buckets, `tc-temp-{city}high-{date}-{bucket}` slugs
- Resolution: **NWS Climatological Report (Daily) at the named station** —
  a free public government feed with known issuance behavior
- Trading window: event start 05:00Z (midnight ET) → 23:59Z; CLI report itself
  publishes next morning → the event is *de facto decided* hours before official
  resolution data exists.

Measured today (NYC, Sep 27, ~11:15Z / 7:15AM ET):
- NWS grid forecast: "high near 66°F", rainy, windy
- KNYC current obs: 59°F (obs cadence ~20–60 min)
- Market buckets: ≤64 → 37.5¢ · 65–66 → 52.5¢ · 66–67 → 12.5¢ · 67–68 → 1.5¢
- **Bucket sum = 1.060** → 6% overround on the buy side (see §4.2)

### The "regular data source" verification (exactly what was asked)
A regular user watches weather.com or a phone app. We can do strictly better,
all from public feeds:
- `api.weather.gov` forecast endpoint carries `updateTime` — we diff forecast
  highs across updates. Each update is a **timestamped public information event**.
- Measure: Δt between NWS update and the affected bucket prices moving (WS
  frames have ns clocks). If the market takes minutes to reprice, that lag is
  the entire edge. Today's snapshot suggests the market tracks the *headline*
  number but reprices slowly on updates — to be confirmed with the lag table.
- Observations (KNYC every ~20–60 min) create a **hard floor**: no bucket below
  the running high can win. Mispriced below-floor buckets (px > noise) during the
  day = free-money audit targets.

### Weather-carry (the boring, compounding one)
After sunset the day's high is almost surely in. Buckets containing the running
high drift to ~99¢ with hours still to run → buying them is lending at
absurd annualized rates until the CLI resolves. Small absolute, near-zero risk —
the classic way to farm a small bankroll without directional view.

## 4. Cross-market synthesis — where it gets abnormal

### 4.1 One information clock
Log every event into one timeline with ns clocks: NWS forecast update, NWS obs,
BRTI-proxy moves, venue WS frames, .com CLOB ticks. Cross-correlate which market
moves first per information type. Lead-lag tables ARE the strategy list; anything
that moves second is tradeable against whatever moves first.

### 4.2 Bucket-sum coherence scanner (no-view arb)
Probabilities across a full bucket set must sum to 1. Measured: **1.060** today
(no buy-arb; sell-side overround exists but needs a basket short). Scan hourly
across all 5 cities: sum < 0.985 → **buy every bucket = riskless $1 at
resolution**; sum > 1.05 → the venue/joint-MM is taxing entrants, fade the buy
side. During resolution-panic (frontier bucket flipping late) sums can briefly
break — the scanner's only job is to be watching at that exact second.

### 4.3 Oracle-canary for weather rules
The market description embeds the station code (`KNYC`). If the venue quietly
switches stations (KNYC → LGA shifts the basis by ~1°F on many days), every
priced bucket is suddenly mispriced against the new rule. **Action: hash the
weather market description text daily** (add to regime_watch — cheap, high value;
pairs with the existing legal-PDF watch).

### 4.4 The level-playing-field proof (why the edge must be cognitive)
The mobile app consumes the same anonymous WS we do (DPoP was proven web-only;
no privileged feed in the binary). **No access edge exists or can exist for
retail.** Therefore edges can only come from: (a) reading public oracles faster
(NWS, BRTI constituents), (b) structural consistency arbs (bucket sums,
cross-venue), (c) carry. Anyone selling "premium Polymarket data feeds" is
selling the same bytes we get free — that itself is a useful litmus for scam
detection in this niche.

### 4.5 Ghost-liquidity detector
On the 15m round's final minute we measured `bestAsk: null, askDepth: 0` —
one-sided books near resolution. Systematically measuring how often and how long
books go one-sided (per market family, per minute-to-resolution) tells us:
when NOT to be in a position needing an exit, and when the venue's internal MM
has withdrawn — a manipulation-friendly window by construction.

### 4.6 Diversify the incubation bankroll by information source
BTC-round bankroll and weather bankroll are exposed to **uncorrelated oracles**
(BRTI vs NWS) and uncorrelated risks (exchange microstructure vs meteorology).
A $10/day budget split across both diversifies *epistemic* risk — the kind that
matters when the failure mode is "our model of the resolution source is wrong."

## 5. Build queue (measure-first ordering)

1. ✅ **US round recorder** — `app_lab/us_round_recorder.py`, RUNNING as
   background process: pre-subscribes current 15m+1h rounds by slug formula,
   archives every lite frame with ns recv clock → `us_rounds/frames-*.jsonl`,
   watches `settlementPx`, polls `GetMarketSettlement` as second witness,
   writes `us_rounds/rounds.csv` per closed round.
2. ✅ **BRTI proxy (v1)** — built into the recorder: 1 Hz samples from
   Coinbase+Kraken (REST, matching BRTI's order-book-retrieval model) and
   Bitstamp+Gemini (WS), staleness>30s and >25%-deviation exclusion per the
   official methodology, mid-of-mids → rolling TWAP60 at each boundary →
   `us_rounds/brti-proxy-*.jsonl` + `match/DRIFT` column in rounds.csv.
   ⚠️ Coinbase ADV websocket level2 now REQUIRES AUTH (regime fact, logged);
   REST 1 Hz is the faithful substitute. Validation target: ≥200 rounds before
   the proxy is trusted as arbiter.
3. ✅ **NWS watcher** — `app_lab/nws_watch.py`, RUNNING: diffs forecast
   `updateTime` per city every 30 min; on change snapshots affected buckets at
   t+0/+10s/+60s/+300s → `weather/lag_table.jsonl`.
4. ✅ **Bucket-sum scanner** — hourly pass inside nws_watch; verdicts use the
   EXECUTABLE ask-sum, not mids (mid-only fakes signals on thin books — proven
   today: nyc-next-day mid-sum 0.98 looked like buy-arb, ask-sum was 1.52).
   First measurements: today-books ≈ 1.05–1.08 mid / 1.08–1.13 ask overround;
   next-day books wildly wide (mid ~1.7, ask ~3.15) → untradeable, ignore.
5. ✅ **Weather-rule canary** — `us-weather-rules` source in regime_watch
   (tar re-packaged): hashes date/threshold-normalized rule text per city;
   station or source swap → Telegram diff alert. Tested stable across runs.
6. **One-sided-book statistic** — derivable from archived frames (next pass).
7. Only after 1–6 produce data: re-open the trading question for US rounds,
   under the standing constraints ($10/trade, $20 daily stop, KILL switch).

## 6. Instrumentation log (measured facts, session 2026-09-27)

- **11:30:00.000z**: round `1115z` closed; venue pushed `settlementPx=0.01`
  (Down won) over the anonymous WS **within ~1s of the boundary** — resolution
  is effectively instantaneous. Our BRTI-proxy TWAP60 for the same minute
  computed 84895.55 from n=60 samples across Coinbase/Kraken/Bitstamp/Gemini.
- Coinbase Advanced WS `level2` now requires auth (regime fact); 1 Hz REST
  book snapshots used instead — faithful to BRTI's order-book-retrieval model.
- Weather bucket-sum (ask-side, executable): today-books 1.08–1.13 overround;
  next-day books mid≈1.7 / ask≈3.15 → illiquid, not tradeable. Mid-only sums
  faked a buy-arb signal (0.98) that ask-checking (1.52) killed — scanner now
  verdicts on asks only.
- Search-only products: updown rounds invisible to GetSeries/GetEvents;
  sentinel patched to probe unified-search. Process lesson recorded.

## 7. Discipline notes (this session)
- WS sessions: one connection, seconds-long, clean unsubscribes. No hammering.
- No authenticated surface touched. No promo/bonus interaction.
- NWS access: standard api.weather.gov with plain UA, low poll rate.
- The sentinel false-negative was our process failing, not luck: search-only
  products beat list-only watchers. Lesson generalized: **watch discovery
  surfaces (search), not just catalog surfaces (list).**
