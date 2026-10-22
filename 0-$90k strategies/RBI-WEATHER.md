# RBI-WEATHER — research loop restart (2026-10-21)

RBI = Research → Backtest → Implement (Moon Dev cadence, our wording: every idea
gets a pre-registered sealed backtest before a dollar; implementation starts paper).
Weather chapter re-opened after Q1 KILL + hk-repo convergence: the crowd is efficient
against FAIR info; the remaining questions are info-SET and microstructure questions.

## 0. City resolution-source map (verified from live rules text, 2026-10-21)

| city family | source | microstructure |
|---|---|---|
| Hong Kong | HKO Daily Extract "Absolute Daily Max" | finalized ONCE daily; floor cut-off (31.9→31); no intraday updates → today's market prices HKO-published values + crowd belief |
| London EGLC, Seoul RKSI, Tokyo RJTT, Singapore WSSS, Wellington NZWN, + ~20 more | NOAA weather.gov/wrh/timeseries, max of "Temp" column over all reported times, whole °C | **hourly live updates**; gaps change the resolved max; fallback to Weather Underground if NOAA missing by 23:59 ET next day; "no data → lowest bracket" (Miami rule); erroneous-data correction window |
| US cities (Miami etc.) | same NOAA timeseries, whole °F, **2-degree buckets (88-89°F)** | °F rounding + wider buckets = different prob mass; separate sub-universe (Q1 never covered US cities — series slugs differ) |

Leverage note: mastering HKO microstructure transfers to 1 city; mastering NOAA
timeseries microstructure (update lag, gap patterns, rounding, fallback switches)
transfers to ~25 cities. Owner's London instinct = the higher-leverage "one city".
Plan: HK = method depth (HKO archive + the cloned repo); London = NOAA-family
representative; passive scans keep all cities accumulating evidence in parallel.

## 1. Candidate board (pre-registered)

**W4a — live-scan revision lag (TOMORROW rows only).** Today's rows are contaminated:
the market sees same-day observed max, a forecast-only model doesn't (the 42 raw flags
of 2026-10-21 with ask≈0 are that contamination, not alpha). Fix before trusting any
flag: (i) condition today's rows on LIVE observations (NOAA timeseries current table +
HKO latest); (ii) rolling bias/sigma calibration (last 14-45 days, refreshed daily —
seasonal bias drifts; hk repo's `calibrate --days 45` is the pattern); (iii) re-scan
daily; a dislocation counts only on rows where both sides share the info set
(tomorrow's markets, or today-pre-observations). Surviving candidates from first scan:
wuhan/amsterdam Oct-22 buckets (edge +0.31..+0.35) — verify by hand vs NOAA table
before believing.
**W4b — 5-day term structure (owner's horizon question).** At D−5/D−3/D−1: calibrated
prob from Previous-Runs day5/day3/day1 vs market price AT THE SAME TIMESTAMP (px
history), EV + edge-decay curve by lead. The trade shape: buy at D−5 when the market
price lags the public forecast, harvest revision convergence, exit D−1. You are not
betting on weather at D−5; you are betting the D−5 price is further from the final
consensus than the D−5 forecast is. Forecasts changing is the mechanism that pays,
not the risk that kills — the risk is the market being RIGHT at D−5 (efficient) and
capacity (thin long-lead books). Q1's 87.5% stale-price stat says long-lead prices are
often old → hypothesis is live. Data: previous-runs day4/5 fetch (28 calls) + px cache.
**W5 — source microstructure.** Per station: NOAA update-lag distribution (hour printed
vs hour published), gap frequency + which hours go missing, WU-fallback days history,
rounding rules; resolved-max vs ECMWF-analysis bias by station. Edge shapes: gap-day
cool bias the crowd doesn't price; fallback-switch days (different source = different
rounding) mispriced; US °F 2-degree bucket tail mass mispriced.
**W1b — tail NO-selling.** Q1: crowd 0-10¢ buckets hit 2% (n=325). Cross-check on the
hk repo's 6-month daily rows + BallesJr's stated limitation (Gaussian underprices
heat-wave tails → NO-selling blows up in extremes): pre-register extreme-day exclusion
rule BEFORE testing (heat-wave flag = ensemble max > bucket + 3°C).
**X-seed ledger (unverified claims, research inputs only):** suislanchez/polymarket-
kalshi-weather-bot (Kalshi KXHIGH cross-venue ensemble fraction, edge>8% gate, claims
$1.8k) → feeds Q3 cross-venue; BalresJr/polymarket-weather-edge (NO-side + live METAR,
Gaussian limits admitted); polydao X thread (+$20.2k/4mo, 20+ cities: NO at 80-99¢ +
cheap YES lotteries, exit 99-100¢) = W1b+W4a shapes; 0xPhilanthrop (27-city stale scan,
"1-8¢ vs public forecast"); kirillk/0x_Discover ($80.7k / $100→$8k threads = funnel-
shaped, treat as marketing); chrisjeansonne1232-jpg/weatherbot (rules doc matches our
verified findings); DonaldEOgbame bot (sane gates: ensemble agreement ≥75%, spread sd
<1.05°F, Kelly cap 8%, $2/position — copy the RISK frame, not the edge).
**recogard listicle (2026-10-15, 497★, reply-thread → Telegram "my results" = funnel):**
6 repos triaged; cloned+audited 2 → /home/user/PolyWeather (★334, active Oct-14,
freemium: has src/payments/ USDC layer; valuable: scripts/iem_cn_asos_truth.py =
IEM ASOS METAR truth feed → basis for our observations feed; generate_city_datasource_map.py;
backtest_metar_calibrated_path.py) and /home/user/polymarket_lp_tool (★585, passive
LP-rewards farmer + rust_mm_bot → queue #8 maker revival reading material; wants
PRIVATE_KEY — audit before any keys). Skips: AutoPilotPM (poster's own repo, created
17d pre-post), polymarket-mcp-server, HarrierOnChain toolkits (copy-trading, maybe later
for wallet research), evan-kolberg/prediction-market-backtesting (★1250 Nautilus ext,
stale May-16; our sealed harness already covers needs).
**PARIS TAMPERING INCIDENT (Apr 2026, Guardian/CNN/NYT/Telegraph/FT-sourced):** CDG
airport sensor spiked to 22°C twice (~Apr 6 + Apr 15, ~9:30pm local, +4-6°F in seconds,
real high ~18°C); 21-22°C buckets had been <1%; anonymous winners $14k + $20-21k,
~$1.4M volume over 2 days; Météo-France filed police complaint (physical tampering
suspected — "hairdryer or lighter"); winner also held Seoul/Toronto weather positions;
Polymarket switched Paris metric CDG→Le Bourget (EGLB) WITHOUT cancelling/refunding.
Board impact: (a) tail-NO risk includes adversarial/criminal spikes, not just model
tails; (b) some X cheap-YES "wins" may be tampering profits — unmodelable ex ante;
(c) EGLC London = same airport-METAR attack-surface class; (d) W5 must track per-city
resolution-source change history; (e) build a tamper-spike detector in the observations
feed (jump vs neighbor stations, evening window) — risk filter first, maybe edge later.

## 2. Build order (next sessions)
1. NOAA timeseries parser + HKO latest-reader → observations feed (conditions W4a).
2. Rolling calibration module (per city·lead, refreshed daily).
3. W4a daily re-scan with clean info sets → candidate log; hand-verify first 10 flags.
4. W4b term-structure backtest (sealed, 6 months, 14 cities + US °F cities if slugs found).
5. W5 station microstructure census → city leaderboard by gap-proneness & crowd error.
6. W1b sealed test with heat-wave exclusion.
Nothing trades until a candidate passes its sealed backtest + the welded gate.
