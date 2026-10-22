# POLYMARKET SECRETS — Dyutam investigation (section index)

> Source article: [Polymarket's 5-Minute Bitcoin Bets Are Doing $60M a Day — And Bots Are Eating Retail Alive](https://dyutam.com/news/polymarket-5-minute-bitcoin-bets-60m-bots-retail/)
> Captured: 2026-09-25 · all 15 "On this page" sections saved as separate files, including widget/table content.
>
> **⚠️ READ FIRST: `AUDIT - 2026-09-26 - claim verification.md`** — full cross-reference of every claim against current Polymarket docs and live-measured data. Verdict: the article's *model* is correct, several *parameters* are stale (fees 1.56%→1.75%, rebate 100%→20% pUSD, $60M→~$13.5M/day, hourly markets deleted). Stale sections carry an AUDIT stamp at the top.

| # | file | section |
|---|---|---|
| 01 | 01 - KEY FACTS AT A GLANCE.md | key facts at a glance |
| 02 | 02 - What Actually Happens When You Place a 5-Minute Bitcoin Bet.md | the full lifecycle of a bet, incl. retail-vs-bot step tables |
| 03 | 03 - The Numbers Behind the Frenzy.md | volume data + time-horizon compression timeline |
| 04 | 04 - The Speed Bump That Disappeared.md | the silent Feb-2026 removal and its fallout |
| 05 | 05 - BEFORE AND AFTER THE SPEED BUMP REMOVAL.md | before/after comparison panel |
| 06 | 06 - The Fee Machine — How Polymarket Monetizes Speed.md | fee math, rebate loop, extraction estimates, fee table |
| 07 | 07 - The Binary Options Comparison Nobody Wants to Make.md | ESMA/FCA bans, regulatory fragmentation |
| 08 | 08 - Same product, different label.md | EU binary option vs PM 5-min bet comparison matrix |
| 09 | 09 - The 0DTE Mirror — Wall Street's Parallel Addiction.md | 0DTE stats, gambling distribution, regulatory gap |
| 10 | 10 - The Integrity Gap.md | sports surveillance vs crypto integrity vacuum |
| 11 | 11 - INTEGRITY INFRASTRUCTURE COMPARISON.md | sports vs 5-min crypto integrity stacks |
| 12 | 12 - The $20 Billion Question.md | valuations, media distribution, pending legislation |
| 13 | 13 - What This Means for You.md | the six practical points |
| 14 | 14 - KEY TAKEAWAYS.md | key takeaways |
| 15 | 15 - Sources.md | all cited sources with links |

## Why this folder matters for our stack
- Companion forensics: `../ui_lab/DEVTOOLS-DEEP-INSPECTION.md` — full DevTools
  inspection of the live site (cookies, storage, hidden endpoints, JS bundles):
  no per-user price manipulation found; the engagement/ad machinery and the
  rule layer are where the asymmetry lives. Also discovered `/api/past-results`.
- Mobile-app forensics: `../app_lab/MOBILE-APP-DEEP-ANALYSIS.md` — full
  top-down analysis of the decompiled Android app v2.8.5: it's the US exchange
  venue (polymarket.us / polymarketexchange.com), a separate ConnectRPC/protobuf
  stack — 275-RPC gateway, device attestation, Binance-candle crypto resolution,
  staging/preprod infra shipped in prod. No 5m updown rounds in the mobile app.
  (full-precision round history, undocumented).
- Confirms the fee-machine facts coded into our system: taker max 1.56% at 50¢,
  makers zero + 100% of taker fees rebated daily in USDC.
- Confirms the speed-bump (taker delay) removal — our regime watcher tracks its
  live field (`seconds_delay`, currently 0) and will alert on any change.
- "Use limit orders, not market orders" (§13) is exactly the thesis behind the
  promoted maker family (S3/S6/S10) in STRATEGY-STACK-RERANKED.md.
- §02's "you are the inefficiency" is the risk model for any taker edge we run:
  assume the venue and the bots see us coming; stay small, stay aligned.
